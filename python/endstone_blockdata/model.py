from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
import hashlib
import json

class ConflictPolicy(Enum):
    FAIL_IF_CHANGED=auto(); MERGE_CHANGED_PATHS=auto(); MERGE_INVENTORY_SLOTS=auto(); REPLACE=auto(); FORCE=auto()

class InventoryChangeKind(Enum):
    ADDED="added"; REMOVED="removed"; CHANGED="changed"

@dataclass(frozen=True, slots=True)
class BlockLocation:
    dimension:str="overworld"; x:int=0; y:int=0; z:int=0

@dataclass(slots=True)
class InventorySlotSnapshot:
    slot:int; item:dict[str,Any]; revision:int=0

@dataclass(slots=True)
class BlockEntitySnapshot:
    type:str
    nbt:dict[str,Any]=field(default_factory=dict)
    raw_snbt:str=""
    canonical_nbt:bool=False
    inventory:list[InventorySlotSnapshot]=field(default_factory=list)

@dataclass(slots=True)
class BlockSnapshot:
    location:BlockLocation
    type:str="minecraft:air"
    runtime_id:int=0
    states:dict[str,bool|int|str]=field(default_factory=dict)
    block_entity:BlockEntitySnapshot|None=None
    revision:int=0
    def refresh_revision(self)->int:
        raw=json.dumps({"type":self.type,"runtime":self.runtime_id,"states":self.states,
          "entity":None if self.block_entity is None else {"type":self.block_entity.type,"nbt":self.block_entity.nbt,
          "inventory":[{"slot":s.slot,"item":s.item} for s in self.block_entity.inventory]}},sort_keys=True,separators=(",",":"),default=str)
        self.revision=int.from_bytes(hashlib.blake2b(raw.encode(),digest_size=8).digest(),"big")
        return self.revision

@dataclass(slots=True)
class BlockPatch:
    location:BlockLocation; expected_revision:int|None=None; replacement_type:str|None=None
    state_updates:dict[str,bool|int|str]=field(default_factory=dict); state_removals:set[str]=field(default_factory=set)
    nbt_updates:dict[str,Any]=field(default_factory=dict); nbt_removals:set[str]=field(default_factory=set)
    inventory_updates:dict[int,dict[str,Any]]=field(default_factory=dict); inventory_removals:set[int]=field(default_factory=set)

@dataclass(slots=True)
class ApplyResult:
    ok:bool; status:str; message:str; resulting_revision:int=0

@dataclass(slots=True)
class InventoryChange:
    slot:int
    kind:InventoryChangeKind
    before:dict[str,Any]|None=None
    after:dict[str,Any]|None=None

@dataclass(slots=True)
class BlockEntityAuditDelta:
    location:BlockLocation
    before_revision:int
    after_revision:int
    block_changed:bool=False
    actor_nbt_changed:bool=False
    inventory_changes:list[InventoryChange]=field(default_factory=list)
    @property
    def empty(self)->bool:
        return not self.block_changed and not self.actor_nbt_changed and not self.inventory_changes
