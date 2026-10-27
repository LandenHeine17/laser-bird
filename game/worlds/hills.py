"""World 1: SUNSET HILLS - crystal pillars, laser gates, turrets. Boss: the Prism Owl."""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Drone, Turret
from ..lasers import Bolt
from ..levels import LevelDef
from ..obstacles import Pillar
from ..registry import register_boss
from ..settings import FLOOR_Y, H, PILLAR_SPACING, W
from ..util import INK as K, WHITE, clamp, rainbow, shade
from ..world import register_backdrop


class HillsDirector(Director):
    def obstacles(self, dt):
        g = self.g
        if self.travelled(dt, PILLAR_SPACING - 15 * min(g.diff, 1.5)):
            self.spawn()

    def spawn(self):
        g = self.g
        d = min(g.diff, 1.6)
        gap_h = max(48, 76 - 16 * d)
        c = clamp(self.last + random.uniform(-60, 60), 14 + gap_h / 2, FLOOR_Y - 14 - gap_h / 2)
        self.last = c
        kind = "metal" if random.random() < 0.25 + 0.15 * min(g.diff, 2) else "crystal"
        gate = self.late > 18 and random.random() < 0.12 + 0.2 * d
        pl = Pillar(W + 4, c - gap_h / 2, c + gap_h / 2, kind, g.biome, gate=gate)
        g.add_obstacle(pl)
        if self.late > 12 and random.random() < 0.18 + 0.25 * d:
            if pl.gap_top >= FLOOR_Y - pl.gap_bot and pl.gap_top > 14:
                g.enemies.append(Turret(pl, pl.gap_top - 8, g))
            elif FLOOR_Y - pl.gap_bot > 14:
                g.enemies.append(Turret(pl, pl.gap_bot + 8, g))
        self.maybe_pickup(pl.x + 60, c)

@register_boss("owl")
class PrismOwl(Boss):
    name = "THE PRISM OWL"
    base_hp, hp_tier, size = 80, 45, 16
    patterns = {
        1: ["fan", "beam", "fan", "rain"],
        2: ["fan", "sweep", "spiral", "beam", "rain"],
        3: ["double_sweep", "spiral", "summon", "fan", "beam", "rain"],
    }

    def gem(self):
        return self.x, self.y + 6

    def spiral_origin(self):
        return self.gem()

    def zones(self):
        return [(pygame.Rect(int(self.x - 6), int(self.y), 12, 12), "crit"),
                (pygame.Rect(int(self.x - 14), int(self.y - 15), 28, 30), "hit")]

    def behave(self, dt, game):
        speed = 1.6 if self.phase == 3 else 1.0
        bob_y = H * 0.42 + math.sin(self.t * 0.9 * speed) * 38
        tx = 250.0
        if not self.entered:
            self.x += (tx - self.x) * min(1.0, dt * 1.4)
            self.y += (bob_y - self.y) * min(1.0, dt * 2)
            self.entered = abs(self.x - tx) < 3
            return
        self.x = tx + math.sin(self.t * 0.5) * 12
        self.y += (bob_y - self.y) * min(1.0, dt * 3)
        self.tick_patterns(dt, game)

    def attack(self, pat, game):
        if pat == "fan":
            self.fan(game, self.x - 2, self.y, 7 if self.phase == 3 else 5)
        elif pat == "beam":
            self.aimed_beam(game, self.gem)
        elif pat == "sweep":
            self.sweep(game, self.gem)
        elif pat == "double_sweep":
            self.sweep(game, self.gem, n=2, width=5)
        elif pat == "spiral":
            self.start_spiral()
        elif pat == "rain":
            for i in range(6 + self.tier):
                game.bolts.append(Bolt(random.uniform(15, 225), -6 - i * 10, random.uniform(-10, 10),
                                       70 + 8 * self.tier, color=(80, 230, 255)))
            game.audio.play("warn", 0.4)
        elif pat == "summon":
            for dy in (-35, 35):
                game.enemies.append(Drone(W + 10, max(20, min(150, self.y + dy)), game))

    def draw(self, surf, game):
        t = self.t
        x, y = int(self.x), int(self.y)
        fl = self.flash > 0
        rage = self.phase == 3
        body = WHITE if fl else ((150, 30, 90) if rage else (110, 40, 170))
        belly = WHITE if fl else ((230, 90, 140) if rage else (200, 120, 230))
        wing = WHITE if fl else ((110, 20, 60) if rage else (80, 30, 130))
        a = int(math.sin(t * 7) * 5)
        for s in (-1, 1):
            pts = [(x + 8 * s, y - 6), (x + 26 * s, y - 4 + a), (x + 22 * s, y + 12 + a), (x + 7 * s, y + 9)]
            pygame.draw.polygon(surf, wing, pts)
            pygame.draw.polygon(surf, K, pts, 1)
            ear = [(x + 7 * s, y - 12), (x + 14 * s, y - 22), (x + 3 * s, y - 14)]
            pygame.draw.polygon(surf, body, ear)
            pygame.draw.polygon(surf, K, ear, 1)
        r = pygame.Rect(x - 14, y - 15, 28, 31)
        pygame.draw.ellipse(surf, body, r)
        pygame.draw.ellipse(surf, K, r, 1)
        pygame.draw.ellipse(surf, belly, (x - 9, y - 3, 18, 17))
        p = game.player
        look = -1 if p.x < self.x else 1
        lpy = max(-1, min(1, int((p.y - y) / 30)))
        eye_c = (255, 60, 60) if rage else (255, 214, 64)
        for ex in (x - 6, x + 6):
            pygame.draw.circle(surf, K, (ex, y - 7), 6)
            pygame.draw.circle(surf, WHITE if fl else eye_c, (ex, y - 7), 5)
            pygame.draw.circle(surf, K, (ex + look * 2, y - 7 + lpy), 2)
        pygame.draw.polygon(surf, (255, 140, 40), [(x - 2, y - 3), (x + 2, y - 3), (x, y + 1)])
        gc = rainbow(t * 0.6)
        pulse = 1 if int(t * 6) % 2 else 0
        gx, gy = x, y + 6
        gem = [(gx, gy - 5 - pulse), (gx + 5 + pulse, gy), (gx, gy + 5 + pulse), (gx - 5 - pulse, gy)]
        pygame.draw.polygon(surf, gc, gem)
        pygame.draw.polygon(surf, K, gem, 1)
        surf.fill(WHITE, (gx - 2, gy - 2, 2, 2))


@register_backdrop("hills")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    base = FLOOR_Y - (42 if idx == 0 else 16)
    amp = 22 if idx == 0 else 12
    k1, k2 = (2, 5) if idx == 0 else (3, 8)
    heights = []
    for x in range(LW):
        h = base - amp * (0.6 * math.sin(math.tau * k1 * x / LW)
                          + 0.4 * math.sin(math.tau * k2 * x / LW + 1.3))
        heights.append(int(h))
        pygame.draw.line(surf, col, (x, int(h)), (x, FLOOR_Y))
        surf.set_at((x, int(h)), light)
    if idx == 1:
        for _ in range(26):
            tx = rnd.randrange(LW)
            ty = heights[tx]
            th = rnd.randint(7, 13)

            def tree(x, ty=ty, th=th):
                pygame.draw.polygon(surf, shade(col, 0.8), [(x - 4, ty + 2), (x, ty - th), (x + 4, ty + 2)])
            bg.wrap(tree, tx)


BIOME = dict(name="SUNSET HILLS", style="hills", stars=False, ground_style="dirt",
    sky=((255, 110, 90), (255, 200, 130)), far=(190, 80, 110), near=(115, 45, 90),
    ground=(70, 35, 60), ground_top=(250, 150, 90), crystal=(110, 200, 255))

LEVEL = LevelDef(
    name="SUNSET HILLS", biome=BIOME, director=HillsDirector, boss="owl",
    enemies=(("drone", 3, 0), ("swooper", 2, 8), ("bat", 1.5, 30)),
    length=60, star=1800, tokens=10, music="main", enemy_rate=0.75, hp_mult=0.8,
    blurb=("CRYSTAL PILLARS - SHOOT THEM APART", "OR SLIP THROUGH THE GAPS"), death="SPLAT!",
)
