"""Core flow for an anti-grief recorder.

The live Endstone binding supplies `block_data`. The portable reference API shown
here has the same snapshots and diff shape.
"""
from endstone_blockdata import BlockDataService

service = BlockDataService()
location = (100, 64, 200)
before = service.capture("overworld", location)

# Capture again after a container transaction/event.
after = service.capture("overworld", location)
delta = service.diff(before, after)

for change in delta.inventory_changes:
    print(change.kind.value, "slot", change.slot, "before=", change.before, "after=", change.after)
