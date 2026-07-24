from __future__ import annotations
from copy import deepcopy
from threading import RLock
from .model import *

class InMemoryAdapter:
    def __init__(self): self._blocks:dict[BlockLocation,BlockSnapshot]={}; self._lock=RLock()
    def capture(self,loc:BlockLocation)->BlockSnapshot:
        with self._lock:
            s=deepcopy(self._blocks.get(loc,BlockSnapshot(loc))); s.refresh_revision(); return s
    def apply(self,p:BlockPatch,policy:ConflictPolicy)->ApplyResult:
        with self._lock:
            s=deepcopy(self._blocks.get(p.location,BlockSnapshot(p.location))); s.refresh_revision()
            if p.expected_revision is not None and policy is not ConflictPolicy.FORCE and p.expected_revision!=s.revision:
                return ApplyResult(False,"conflict","revision changed",s.revision)
            if p.replacement_type is not None: s.type=p.replacement_type
            s.states.update(p.state_updates)
            for k in p.state_removals: s.states.pop(k,None)
            if p.nbt_updates or p.nbt_removals or p.inventory_updates or p.inventory_removals:
                s.block_entity=s.block_entity or BlockEntitySnapshot("generic", canonical_nbt=True)
                s.block_entity.nbt.update(deepcopy(p.nbt_updates))
                for k in p.nbt_removals: s.block_entity.nbt.pop(k,None)
                slots={x.slot:x for x in s.block_entity.inventory}
                for slot in p.inventory_removals: slots.pop(slot,None)
                for slot,item in p.inventory_updates.items(): slots[slot]=InventorySlotSnapshot(slot,deepcopy(item))
                s.block_entity.inventory=list(slots.values())
            s.refresh_revision(); self._blocks[p.location]=s
            return ApplyResult(True,"applied","applied",s.revision)

class BlockDataService:
    def __init__(self,adapter=None): self.adapter=adapter or InMemoryAdapter()
    def capture(self,dimension:str,position:tuple[int,int,int])->BlockSnapshot: return self.adapter.capture(BlockLocation(dimension,*position))
    def apply(self,patch:BlockPatch,policy:ConflictPolicy=ConflictPolicy.FAIL_IF_CHANGED)->ApplyResult: return self.adapter.apply(patch,policy)
    def capture_region(self,dimension:str,minimum:tuple[int,int,int],maximum:tuple[int,int,int])->list[BlockSnapshot]:
        ax,ay,az=minimum; bx,by,bz=maximum
        return [self.capture(dimension,(x,y,z)) for x in range(min(ax,bx),max(ax,bx)+1) for y in range(min(ay,by),max(ay,by)+1) for z in range(min(az,bz),max(az,bz)+1)]
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
        self.snapshot=snapshot
    @property
    def nbt(self): return deepcopy(self.snapshot.block_entity.nbt)
    @property
    def raw_snbt(self): return self.snapshot.block_entity.raw_snbt
    def get_item(self,slot:int):
        return next((deepcopy(x.item) for x in self.snapshot.block_entity.inventory if x.slot==slot),None)
    def patch_item(self,slot:int,item:dict)->BlockPatch:
        return BlockPatch(self.snapshot.location,self.snapshot.revision,inventory_updates={slot:deepcopy(item)})
    def clear_item(self,slot:int)->BlockPatch:
        return BlockPatch(self.snapshot.location,self.snapshot.revision,inventory_removals={slot})
