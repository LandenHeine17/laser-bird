"""All worlds, in play order. Importing this registers every enemy, boss, block
material and background painter the levels use.

To add a world: create a module here that defines BIOME, its director, enemies,
boss and a `LEVEL = LevelDef(...)`, then append it below. Secret worlds go last.
"""
from . import bamboo, caves, city, hills, magma, space

LEVELS = [hills.LEVEL, city.LEVEL, caves.LEVEL, magma.LEVEL, space.LEVEL, bamboo.LEVEL]
MAIN_LEVELS = sum(not L.secret for L in LEVELS)
assert all(L.secret for L in LEVELS[MAIN_LEVELS:]), "secret levels must come after the main ones"
