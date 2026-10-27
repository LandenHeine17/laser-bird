"""Base class for level directors: the per-world spawners that build each level."""
import math
import random

from .powerups import PowerItem, Shard, random_power
from .registry import ENEMIES
from .settings import FLOOR_Y, H, PILLAR_SPACING


class Director:
    """Owned by the Game for one stage. Subclasses override `obstacles` (called every
    frame while no boss is around) and optionally `prefill`, `free_y` and `update`."""

    def __init__(self, game, level):
        self.g = game
        self.L = level
        self.enemy_t = 3.0
        self.dist = PILLAR_SPACING * 0.4
        self.last = H * 0.45

    def prefill(self):
        """Populate the screen before the first frame (e.g. the cave tunnel)."""

    def update(self, dt):
        g = self.g
        if g.boss_state is None and g.player.alive:
            self.obstacles(dt)
            self.enemy_t -= dt
            if self.enemy_t <= 0:
                self.enemy_t = random.uniform(2.2, 3.8) / (1 + 0.45 * g.diff) / self.L.enemy_rate
                self.spawn_enemy()

    def obstacles(self, dt):
        pass

    def travelled(self, dt, spacing):
        """Accumulate scrolled distance; True (and reset) once it reaches `spacing` px."""
        self.dist += self.g.scroll * dt
        if self.dist >= spacing:
            self.dist = 0.0
            return True
        return False

    def free_y(self):
        """A y position where it's reasonable to spawn a flying enemy."""
        return random.uniform(25, FLOOR_Y - 25)

    @property
    def late(self):
        """Seconds into the stage; in Endless loops everything is unlocked."""
        return self.g.stage_time + (999 if self.g.tier else 0)

    def spawn_enemy(self):
        opts = [(key, w) for key, w, after in self.L.enemies if self.late >= after]
        key = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        ENEMIES[key].spawn(self.g, self.free_y())

    def maybe_pickup(self, x, y, item=0.13, shards=0.27):
        g = self.g
        roll = random.random()
        if roll < item:
            g.items.append(PowerItem(random_power(g.player.hp, g.hp_cap), x, y))
        elif roll < item + shards:
            for i in range(4):
                g.shards.append(Shard(x + i * 12, y + math.sin(i) * 6, floating=True))
