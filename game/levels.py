"""The LevelDef record. Each world module in `game/worlds/` defines one `LEVEL`."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LevelDef:
    name: str
    biome: dict                 # colors + background style, see world.Background
    director: type              # Director subclass that builds the world
    boss: str                   # key in registry.BOSSES
    enemies: tuple              # (enemy key, spawn weight, seconds into the level before it appears)
    length: float = 75.0        # seconds of travel before the boss
    star: int = 3000            # score for 2 stars (x1.8 for 3)
    tokens: int = 10            # base token reward for clearing it
    music: str = "main"         # track name in audio.TRACKS
    base_diff: float = 0.0      # starting difficulty
    enemy_rate: float = 1.0     # spawn-rate multiplier
    hp_mult: float = 1.0        # enemy toughness (damage taken is divided by this)
    boss_mult: float = 1.0      # boss toughness
    gravity: float = 1.0        # multiplier on the bird's gravity
    flap: float = 1.0           # multiplier on the bird's flap strength
    secret: bool = False        # hidden until unlocked; never part of Endless
    blurb: tuple = ("", "")     # two lines shown on the level select screen
    death: str = "SPLAT!"       # message when you hit the floor
