from endstone_blockdata import *
service=BlockDataService()
block=service.capture("overworld",(100,64,200))
patch=BlockPatch(block.location,block.revision,"minecraft:chest",
    nbt_updates={"CustomName":"Kingdom Vault"},
    inventory_updates={0:{"Name":"minecraft:diamond","Count":16}})
print(service.apply(patch))
print(ContainerView(service.capture("overworld",(100,64,200))).get_item(0))
