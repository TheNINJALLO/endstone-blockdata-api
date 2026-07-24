"""Use inside an Endstone Python plugin on the primary server thread."""
from _endstone_blockdata_live import capture, capabilities


def inspect_container(plugin, dimension: str, x: int, y: int, z: int) -> dict | None:
    caps = capabilities(plugin.server)
    if not caps["block_entity_nbt"] or not caps["inventory"]:
        raise RuntimeError("The exact BlockData NBT adapter is not active")
    snapshot = capture(plugin.server, dimension, x, y, z)
    if snapshot is None or snapshot["block_entity"] is None:
        return None
    return snapshot


# Save the returned dict before a player action, capture it again afterwards,
# and compare block_entity["inventory"] and block_entity["nbt"]. The nested
# item `tag` contains enchantments, lore and custom item data.
