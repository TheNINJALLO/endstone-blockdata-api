from __future__ import annotations
from copy import deepcopy
from enum import Enum
from threading import RLock
from typing import Any
from .model import *

_MAX_CAPTURE_REGION_BLOCKS = 32768

class InMemoryAdapter:
    def __init__(self): self._blocks:dict[BlockLocation,BlockSnapshot]={}; self._lock=RLock()
    def capture(self,loc:BlockLocation)->BlockSnapshot:
        with self._lock:
            s=deepcopy(self._blocks.get(loc,BlockSnapshot(loc))); s.refresh_revision(); return s
    def apply(self,p:BlockPatch,policy:ConflictPolicy)->ApplyResult:
        with self._lock:
            if policy not in (ConflictPolicy.FAIL_IF_CHANGED,ConflictPolicy.FORCE):
                return ApplyResult(False,"unsupported","conflict policy is not implemented; use FailIfChanged or Force",0)
            s=deepcopy(self._blocks.get(p.location,BlockSnapshot(p.location))); s.refresh_revision()
            if p.expected_revision is not None and policy is not ConflictPolicy.FORCE and p.expected_revision!=s.revision:
                return ApplyResult(False,"conflict","revision changed",s.revision)
            if p.replacement_type is not None: s.type=p.replacement_type
            s.states.update(p.state_updates)
            for k in p.state_removals: s.states.pop(k,None)
            if p.nbt_updates or p.nbt_removals or p.inventory_updates or p.inventory_removals:
                s.block_entity=s.block_entity or BlockEntitySnapshot("generic", canonical_nbt=True)
                s.block_entity_status="captured"
                s.block_entity.nbt.update(deepcopy(p.nbt_updates))
                for k in p.nbt_removals: s.block_entity.nbt.pop(k,None)
                slots={x.slot:x for x in s.block_entity.inventory}
                for slot in p.inventory_removals: slots.pop(slot,None)
                for slot,item in p.inventory_updates.items(): slots[slot]=InventorySlotSnapshot(slot,deepcopy(item))
                s.block_entity.inventory=list(slots.values())
                if p.inventory_updates or p.inventory_removals:
                    s.block_entity.is_container=True
                    touched_slots=set(p.inventory_updates)|set(p.inventory_removals)
                    if touched_slots:
                        s.block_entity.container_size=max(
                            s.block_entity.container_size,max(touched_slots)+1
                        )
            s.refresh_revision(); self._blocks[p.location]=s
            return ApplyResult(True,"applied","applied",s.revision)

class BlockDataService:
    def __init__(self,adapter=None): self.adapter=InMemoryAdapter() if adapter is None else adapter
    def capture(self,dimension:str,position:tuple[int,int,int])->BlockSnapshot: return self.adapter.capture(BlockLocation(dimension,*position))
    def apply(self,patch:BlockPatch,policy:ConflictPolicy=ConflictPolicy.FAIL_IF_CHANGED)->ApplyResult: return self.adapter.apply(patch,policy)
    def capture_region(self,dimension:str,minimum:tuple[int,int,int],maximum:tuple[int,int,int])->list[BlockSnapshot]:
        ax,ay,az=minimum; bx,by,bz=maximum
        width=abs(bx-ax)+1; height=abs(by-ay)+1; depth=abs(bz-az)+1
        if (width>_MAX_CAPTURE_REGION_BLOCKS or height>_MAX_CAPTURE_REGION_BLOCKS or
                depth>_MAX_CAPTURE_REGION_BLOCKS or width*height*depth>_MAX_CAPTURE_REGION_BLOCKS):
            raise ValueError("capture region exceeds 32768 blocks")
        normalized_minimum=(min(ax,bx),min(ay,by),min(az,bz))
        normalized_maximum=(max(ax,bx),max(ay,by),max(az,bz))
        adapter_capture_region=getattr(self.adapter,"capture_region",None)
        if callable(adapter_capture_region):
            return adapter_capture_region(
                dimension,normalized_minimum,normalized_maximum
            )
        min_x,min_y,min_z=normalized_minimum
        max_x,max_y,max_z=normalized_maximum
        return [self.capture(dimension,(x,y,z)) for x in range(min_x,max_x+1) for y in range(min_y,max_y+1) for z in range(min_z,max_z+1)]
    @staticmethod
    def diff(before:BlockSnapshot,after:BlockSnapshot)->BlockEntityAuditDelta:
        if before.location != after.location: raise ValueError("snapshot locations differ")
        left={s.slot:s.item for s in (before.block_entity.inventory if before.block_entity else [])}
        right={s.slot:s.item for s in (after.block_entity.inventory if after.block_entity else [])}
        changes=[]
        for slot,item in left.items():
            if slot not in right: changes.append(InventoryChange(slot,InventoryChangeKind.REMOVED,deepcopy(item),None))
            elif item != right[slot]: changes.append(InventoryChange(slot,InventoryChangeKind.CHANGED,deepcopy(item),deepcopy(right[slot])))
        for slot,item in right.items():
            if slot not in left: changes.append(InventoryChange(slot,InventoryChangeKind.ADDED,None,deepcopy(item)))
        before_nbt=None if before.block_entity is None else before.block_entity.nbt
        after_nbt=None if after.block_entity is None else after.block_entity.nbt
        return BlockEntityAuditDelta(before.location,before.revision,after.revision,
            block_changed=(before.type,before.runtime_id,before.states)!=(after.type,after.runtime_id,after.states),
            actor_nbt_changed=before_nbt!=after_nbt,inventory_changes=changes)

class ContainerView:
    def __init__(self,snapshot:BlockSnapshot):
        if snapshot.block_entity is None: raise ValueError("block has no block entity")
        self.snapshot=deepcopy(snapshot)
    @property
    def nbt(self): return deepcopy(self.snapshot.block_entity.nbt)
    @property
    def raw_snbt(self): return self.snapshot.block_entity.raw_snbt
    @property
    def capacity(self): return self.snapshot.block_entity.container_size
    @property
    def occupied_slots(self): return len(self.snapshot.block_entity.inventory)
    def get_item(self,slot:int):
        return next((deepcopy(x.item) for x in self.snapshot.block_entity.inventory if x.slot==slot),None)
    def patch_item(self,slot:int,item:dict)->BlockPatch:
        return BlockPatch(self.snapshot.location,self.snapshot.revision,inventory_updates={slot:deepcopy(item)})
    def clear_item(self,slot:int)->BlockPatch:
        return BlockPatch(self.snapshot.location,self.snapshot.revision,inventory_removals={slot})

class ShelfKind(str,Enum):
    SHELF="shelf"
    CHISELED_BOOKSHELF="chiseled_bookshelf"

class ShelfView:
    """Fail-closed typed view over a complete live shelf capture."""
    _BOOK_IDS={
        "minecraft:book","minecraft:writable_book","minecraft:written_book",
        "minecraft:enchanted_book",
    }

    def __init__(self,snapshot:BlockSnapshot):
        self.snapshot=deepcopy(snapshot)
        actor=self.snapshot.block_entity
        if self.snapshot.block_entity_status!="captured" or actor is None or not actor.is_container:
            raise ValueError("shelf capture is incomplete or unavailable")
        if actor.type=="minecraft:shelf":
            self.kind=ShelfKind.SHELF
            expected=3
        elif actor.type=="minecraft:chiseled_bookshelf":
            self.kind=ShelfKind.CHISELED_BOOKSHELF
            expected=6
        else:
            raise ValueError("block actor is not a supported shelf")
        if actor.container_size!=expected:
            raise ValueError("shelf container capacity does not match the exact actor contract")
        occupied:set[int]=set()
        for entry in actor.inventory:
            if not 0<=entry.slot<expected:
                raise ValueError("shelf capture contains an out-of-range slot")
            if entry.slot in occupied:
                raise ValueError("shelf capture contains a duplicate slot")
            occupied.add(entry.slot)

    @property
    def capacity(self)->int:
        return 3 if self.kind is ShelfKind.SHELF else 6

    @property
    def slots(self)->list[dict[str,Any]|None]:
        output:list[dict[str,Any]|None]=[None]*self.capacity
        for entry in self.snapshot.block_entity.inventory:
            output[entry.slot]=deepcopy(entry.item)
        return output

    def _validate_slot(self,slot:int)->None:
        if not isinstance(slot,int) or isinstance(slot,bool) or not 0<=slot<self.capacity:
            raise IndexError("shelf slot is out of range")

    def _validate_item(self,item:dict[str,Any])->None:
        if not isinstance(item,dict):
            raise ValueError("shelf item must be an NBT compound")
        identifier=next((item[key] for key in ("Name","name","id") if key in item),None)
        if not isinstance(identifier,str) or not identifier:
            raise ValueError("shelf item has no item identifier")
        count=next((item[key] for key in ("Count","count") if key in item),1)
        if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=255:
            raise ValueError("shelf item count is out of range")
        if self.kind is ShelfKind.CHISELED_BOOKSHELF and (count!=1 or identifier not in self._BOOK_IDS):
            raise ValueError("chiseled bookshelf slots accept exactly one supported book")

    def get_item(self,slot:int)->dict[str,Any]|None:
        self._validate_slot(slot)
        return deepcopy(self.slots[slot])

    def patch_item(self,slot:int,item:dict[str,Any])->BlockPatch:
        self._validate_slot(slot)
        self._validate_item(item)
        return BlockPatch(
            self.snapshot.location,self.snapshot.revision,
            inventory_updates={slot:deepcopy(item)},
        )

    def clear_item(self,slot:int)->BlockPatch:
        return self.patch_items(removals={slot})

    def patch_items(
        self,
        updates:dict[int,dict[str,Any]]|None=None,
        removals:set[int]|None=None,
    )->BlockPatch:
        """Build one optimistic patch for any number of shelf slots."""
        updates={} if updates is None else updates
        removals=set() if removals is None else set(removals)
        for slot,item in updates.items():
            self._validate_slot(slot)
            self._validate_item(item)
            if slot in removals:
                raise ValueError(
                    "a shelf slot cannot be updated and removed in one patch"
                )
        for slot in removals:
            self._validate_slot(slot)
        return BlockPatch(
            self.snapshot.location,self.snapshot.revision,
            inventory_updates=deepcopy(updates),
            inventory_removals=removals,
        )

    def replace_items(self,items:list[dict[str,Any]|None])->BlockPatch:
        """Replace all shelf slots in one compare-and-swap operation."""
        if not isinstance(items,list) or len(items)!=self.capacity:
            raise ValueError(
                "replacement shelf contents must match the exact capacity"
            )
        updates={slot:item for slot,item in enumerate(items) if item is not None}
        removals={slot for slot,item in enumerate(items) if item is None}
        return self.patch_items(updates,removals)
