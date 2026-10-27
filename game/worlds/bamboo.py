"""SECRET WORLD: BAMBOO GROVE - a misty bamboo forest guarded by ninja pandas.

Bamboo bundles can be chopped apart with lasers, mossy stones can't. Bamboo spikes
burst from the ground after a rustle. Boss: the Grandmaster Panda, meditating on a
cloud with a bamboo staff.
"""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Enemy
from ..lasers import Bolt
from ..levels import LevelDef
from ..obstacles import Geyser, Pillar, register_block
from ..registry import register_boss, register_enemy
from ..settings import FLOOR_Y, W
from ..sprites import draw_text
from ..util import INK as K, WHITE, aim, shade
from ..world import register_backdrop


def _bamboo_decor(surf, r, part, light, dark, t):
    """A bundle of three stalks with node rings."""
    for sx in (r.x + 6, r.x + 12):
        pygame.draw.line(surf, dark, (sx, r.y), (sx, r.bottom - 1))
    surf.fill(dark, (r.x, r.bottom - 2, r.w, 1))
    surf.fill(light, (r.x + 1, r.bottom - 1, r.w - 2, 1))


def _moss_decor(surf, r, part, light, dark, t):
    surf.fill(light, (r.x + 1, r.y + 1, r.w - 2, 2))
    surf.fill(light, (r.x + 3, r.y + 3, 3, 1))
    surf.fill(dark, (r.x + 8, r.y + r.h // 2, 3, 2))


register_block("bamboo", ((95, 175, 65), (160, 225, 105), (40, 85, 35)), hp=2, decor=_bamboo_decor)
register_block("moss", ((110, 112, 104), (125, 195, 85), (52, 56, 52)), decor=_moss_decor)

LEAF = (130, 210, 90)
SILVER = (200, 205, 220)

class BambooSpike(Geyser):
    """A sharpened bamboo shoot that bursts out of the ground. Watch for the rustle."""

    def draw(self, surf, game):
        x, w = int(self.x), self.w
        if self.state == "warn":
            for i in range(3):
                jx = random.randint(-1, 1)
                surf.fill((90, 70, 50), (x + 2 + i * 3 + jx, FLOOR_Y - 2, 2, 2))
            if random.random() < 0.4:
                game.fx.burst(x + w / 2, FLOOR_Y - 1, [(110, 85, 60), LEAF], n=1, speed=40, life=0.4, grav=120,
                              angle=-math.pi / 2, spread=1.2)
        if self.h > 1:
            top = int(FLOOR_Y - self.h)
            body = pygame.Rect(x + 2, top + 6, w - 4, int(self.h) - 6)
            surf.fill((40, 85, 35), body.inflate(2, 0))
            surf.fill((95, 175, 65), body)
            surf.fill((160, 225, 105), (body.x + 1, body.y, 1, body.h))
            for y in range(body.y + 8, body.bottom, 12):
                surf.fill((40, 85, 35), (body.x, y, body.w, 1))
            pygame.draw.polygon(surf, (160, 225, 105), [(x + 1, top + 7), (x + w - 1, top + 7), (x + w // 2, top - 2)])
            pygame.draw.polygon(surf, (40, 85, 35), [(x + 1, top + 7), (x + w - 1, top + 7), (x + w // 2, top - 2)], 1)

@register_enemy("ninja")
class PandaNinja(Enemy):
    """Hovers on a little cloud and flings fans of spinning shuriken."""
    hp = 3
    score = 40
    w, h = 11, 11
    shards = 2
    colors = [WHITE, (40, 40, 50), (220, 40, 60)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.base_y = y
        self.cool = random.uniform(1.0, 1.8)
        self.hover_x = random.uniform(190, 285)

    def update(self, dt, game):
        super().update(dt, game)
        self.x -= ((game.scroll + 50) if self.x > self.hover_x else game.scroll * 0.3) * dt
        self.y = self.base_y + math.sin(self.t * 2) * 10
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(1.8, 2.6) / (1 + 0.3 * game.diff)
            if self.can_shoot(game):
                p = game.player
                base = math.atan2(p.y - self.y, p.x - self.x)
                for k in (-1, 0, 1):
                    a = base + k * 0.25
                    game.bolts.append(Bolt(self.x - 5, self.y, math.cos(a) * 95, math.sin(a) * 95, color=SILVER))
                game.audio.play("shard", 0.6)

    def draw(self, surf, game):
        x, y = int(self.x), int(self.y)
        for i, dx in enumerate((-6, -2, 2, 6)):
            pygame.draw.circle(surf, (235, 240, 245), (x + dx, y + 8 + (i % 2)), 3)
        self.blit(surf, game, game.art.ninja)
        for i in range(3):  # headband tails flutter behind
            surf.set_at((x + 6 + i, y - 3 + int(math.sin(self.t * 12 + i) * 1.5)), (220, 40, 60))
        if 0 < self.cool < 0.25 and int(self.t * 30) % 2:
            surf.fill(WHITE, (x - 7, y, 2, 2))

@register_enemy("redpanda")
class RedPanda(Enemy):
    """Scampers in fast after a '!' warning, homing on your height."""
    hp = 2
    score = 30
    w, h = 12, 6
    colors = [(255, 140, 40), (140, 80, 40), WHITE]

    def __init__(self, x, y, game, delay=0.0):
        super().__init__(x, y)
        self.warn = 0.75 + delay
        self.speed = game.scroll + 90 + 20 * min(game.diff, 2)

    @classmethod
    def spawn(cls, game, y):
        n = random.choice((1, 1, 2, 3))
        for i in range(n):
            game.enemies.append(cls(W + 30, max(22, min(FLOOR_Y - 22, y + (i - n // 2) * 22)), game, delay=i * 0.22))

    def update(self, dt, game):
        super().update(dt, game)
        p = game.player
        if self.warn > 0:
            self.warn -= dt
            self.y += (p.y - self.y) * min(1.0, dt * 1.2)
            return
        self.x -= self.speed * dt
        if self.x > p.x + 40:
            self.y += max(-70, min(70, (p.y - self.y) * 2.0)) * dt

    def draw(self, surf, game):
        if self.warn > 0:
            if int(self.t * 10) % 2:
                draw_text(surf, "!", W - 6, int(self.y) - 2, (255, 140, 40))
            return
        self.blit(surf, game, game.art.redpanda[int(self.t * 12) % 2])

@register_enemy("crane")
class Crane(Enemy):
    """Glides across in long waves, flicking feathers at you."""
    hp = 2
    score = 30
    w, h = 13, 5
    colors = [WHITE, (220, 40, 60), (40, 40, 50)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.base_y = y
        self.cool = random.uniform(1.0, 2.0)

    def update(self, dt, game):
        super().update(dt, game)
        self.x -= (game.scroll * 0.5 + 35) * dt
        self.y = self.base_y + math.sin(self.t * 1.6) * 24
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(1.8, 2.6) / (1 + 0.3 * game.diff)
            if self.can_shoot(game, 30):
                p = game.player
                vx, vy = aim(self.x - 6, self.y, p.x, p.y, 110)
                game.bolts.append(Bolt(self.x - 6, self.y, vx, vy, color=(240, 240, 250)))
                game.audio.play("eshot", 0.5)

    def draw(self, surf, game):
        self.blit(surf, game, game.art.crane[int(self.t * 6) % 2])

@register_boss("panda")
class GrandmasterPanda(Boss):
    """A giant panda master meditating on a cloud. The jade amulet on its chest is
    the weak point; the bamboo staff blocks shots."""
    name = "GRANDMASTER PANDA"
    base_hp, hp_tier, size = 120, 50, 22
    colors = [WHITE, (40, 40, 50), (110, 220, 140)]
    spiral_color = LEAF
    patterns = {
        1: ["shuriken", "spikes", "shuriken", "sweep"],
        2: ["shuriken", "sweep", "leaves", "spikes", "summon"],
        3: ["double", "shuriken", "leaves", "spikes", "summon", "sweep"],
    }

    def __init__(self, game, tier):
        super().__init__(game, tier)
        self.y = 88.0
        self.cast = 0.0

    def staff_tip(self):
        return self.x - 24, self.y - 30

    def amulet(self):
        return self.x, self.y + 4

    def spiral_origin(self):
        return self.amulet()

    def zones(self):
        x, y = self.x, self.y
        return [(pygame.Rect(int(x - 5), int(y), 10, 9), "crit"),
                (pygame.Rect(int(x - 26), int(y - 32), 6, 56), "block"),
                (pygame.Rect(int(x - 18), int(y - 28), 36, 50), "hit")]

    def behave(self, dt, game):
        self.cast = max(0.0, self.cast - dt)
        tx = 252.0
        ty = 88 + math.sin(self.t * (1.3 if self.phase == 3 else 0.7)) * 26
        if not self.entered:
            self.x += (tx - self.x) * min(1.0, dt * 1.2)
            self.entered = abs(self.x - tx) < 3
            return
        self.x = tx + math.sin(self.t * 0.5) * 8
        self.y += (ty - self.y) * min(1.0, dt * 2.5)
        self.tick_patterns(dt, game)

    def attack(self, pat, game):
        self.cast = 0.5
        if pat == "shuriken":
            self.fan(game, self.x - 14, self.y - 4, 7 if self.phase == 3 else 5, spread=0.15, color=SILVER)
        elif pat == "spikes":
            xs = sorted(random.sample(range(15, 225, 20), 6 + self.phase))
            for i, x in enumerate(xs):
                game.add_obstacle(BambooSpike(x, game.biome, hmax=random.randint(50, 100), once=True, delay=i * 0.12))
            game.fx.text(self.x - 30, self.y - 44, "BAMBOO STRIKE!", LEAF)
        elif pat == "leaves":
            self.start_spiral(1.3)
        elif pat == "summon":
            for dy in (-35, 35):
                game.enemies.append(PandaNinja(W + 10, max(20, min(150, self.y + dy)), game))
        elif pat == "sweep":
            self.sweep(game, self.staff_tip, color=(110, 220, 140))
        elif pat == "double":
            self.sweep(game, self.staff_tip, n=2, color=(110, 220, 140), width=5)

    def draw(self, surf, game):
        t = self.t
        x, y = int(self.x), int(self.y)
        fl = self.flash > 0
        rage = self.phase == 3
        white = WHITE if not fl else (255, 220, 220)
        black = (40, 40, 50) if not fl else WHITE
        # cloud
        for i, dx in enumerate((-22, -12, 0, 12, 22)):
            pygame.draw.circle(surf, (235, 240, 245), (x + dx, y + 26 + (i % 2) * 2), 9)
        for dx in (-16, 4, 18):
            pygame.draw.circle(surf, (205, 215, 225), (x + dx, y + 31), 5)
        # body + legs (crossed, meditating)
        pygame.draw.ellipse(surf, K, (x - 19, y - 11, 38, 36))
        pygame.draw.ellipse(surf, white, (x - 18, y - 10, 36, 34))
        pygame.draw.ellipse(surf, black, (x - 20, y + 14, 18, 10))
        pygame.draw.ellipse(surf, black, (x + 2, y + 14, 18, 10))
        # arms: left grips the staff
        pygame.draw.ellipse(surf, black, (x - 22, y - 8, 10, 18))
        pygame.draw.ellipse(surf, black, (x + 12, y - 6, 10, 18))
        # bamboo staff
        sx = x - 23
        surf.fill((40, 85, 35), (sx - 2, y - 32, 5, 58))
        surf.fill((110, 200, 80), (sx - 1, y - 32, 3, 58))
        for yy in range(y - 26, y + 24, 9):
            surf.fill((40, 85, 35), (sx - 2, yy, 5, 1))
        tipc = (160, 255, 190) if self.cast > 0 or int(t * 4) % 2 else (110, 220, 140)
        pygame.draw.circle(surf, tipc, (sx, y - 32), 3)
        # head
        hx, hy = x, y - 20
        for s in (-1, 1):
            pygame.draw.circle(surf, black, (hx + 11 * s, hy - 9), 5)
        pygame.draw.circle(surf, K, (hx, hy), 14)
        pygame.draw.circle(surf, white, (hx, hy), 13)
        pygame.draw.rect(surf, (220, 40, 60), (hx - 13, hy - 8, 26, 3))
        for i in range(3):
            surf.fill((220, 40, 60), (hx + 13 + i * 2, hy - 7 + int(math.sin(t * 10 + i) * 2), 2, 2))
        for s in (-1, 1):
            pygame.draw.ellipse(surf, black, (hx + (2 if s > 0 else -9), hy - 3, 7, 8))
            eye = (255, 60, 60) if rage else WHITE
            surf.fill(eye, (hx + (4 if s > 0 else -6), hy - 1, 2, 2))
            brow_y = hy - 5 + (1 if rage else 0)
            pygame.draw.line(surf, black, (hx + 2 * s, brow_y + (1 if rage else 0)), (hx + 8 * s, brow_y - 1))
        pygame.draw.ellipse(surf, black, (hx - 3, hy + 4, 6, 4))
        pygame.draw.line(surf, black, (hx - 3, hy + 9), (hx + 3, hy + 9))
        # jade amulet (weak point)
        ax, ay = self.amulet()
        pulse = 1 if int(t * 6) % 2 else 0
        pygame.draw.line(surf, (200, 160, 60), (x - 8, y - 6), (int(ax), int(ay)))
        pygame.draw.line(surf, (200, 160, 60), (x + 8, y - 6), (int(ax), int(ay)))
        pygame.draw.circle(surf, K, (int(ax), int(ay) + 2), 5 + pulse)
        pygame.draw.circle(surf, (110, 220, 140), (int(ax), int(ay) + 2), 4 + pulse)
        surf.fill(WHITE, (int(ax) - 2, int(ay), 2, 2))

class BambooDirector(Director):
    def __init__(self, game, level):
        super().__init__(game, level)
        self.spike_t = 9.0

    def obstacles(self, dt):
        g = self.g
        if self.travelled(dt, 128 - 12 * min(g.diff, 1.5)):
            self.spawn()
        self.spike_t -= dt
        if self.late > 8 and self.spike_t <= 0:
            self.spike_t = random.uniform(3.0, 5.0) / (1 + 0.3 * g.diff)
            g.add_obstacle(BambooSpike(random.uniform(120, W + 30), g.biome, hmax=random.uniform(45, 95),
                                       once=True, warn=1.0))

    def spawn(self):
        g = self.g
        d = min(g.diff, 1.6)
        gap_h = max(54, 80 - 16 * d)
        x = W + 4
        r = random.random()
        if r < 0.6:
            c = max(14 + gap_h / 2, min(FLOOR_Y - 14 - gap_h / 2, self.last + random.uniform(-55, 55)))
            self.last = c
            pl = Pillar(x, c - gap_h / 2, c + gap_h / 2, "bamboo", g.biome)
            mid = c
        elif r < 0.8:
            top = random.uniform(gap_h + 10, FLOOR_Y - 30)
            pl = Pillar(x, 0, top, "moss", g.biome, w=16)
            mid = top / 2
        else:
            bot = random.uniform(30, FLOOR_Y - gap_h - 10)
            pl = Pillar(x, bot, FLOOR_Y, "bamboo", g.biome)
            mid = (bot + FLOOR_Y) / 2
        g.add_obstacle(pl)
        self.maybe_pickup(pl.x + 60, mid)

    def free_y(self):
        return random.uniform(25, FLOOR_Y - 30)


@register_backdrop("bamboo")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    if idx == 0:
        # misty mountains + a distant pagoda + pale bamboo
        for k, (amp, base, col2) in enumerate(((40, 70, shade(col, 1.15)), (28, 100, col))):
            for x in range(LW):
                h = base - amp * (0.5 * math.sin(math.tau * (2 + k) * x / LW + k)
                                  + 0.5 * abs(math.sin(math.tau * (5 + k) * x / LW)))
                pygame.draw.line(surf, col2, (x, int(h)), (x, FLOOR_Y))
        px = rnd.randrange(LW)

        def pagoda(x):
            pc = shade(col, 0.8)
            for i in range(4):
                w = 22 - i * 4
                y = 92 - i * 9
                pygame.draw.polygon(surf, pc, [(x - w, y), (x + w, y), (x + w - 5, y - 4), (x - w + 5, y - 4)])
                pygame.draw.rect(surf, pc, (x - w + 7, y, 2 * w - 14, 6))
            pygame.draw.line(surf, pc, (x, 54), (x, 46))
        bg.wrap(pagoda, px)
        for _ in range(40):
            x = rnd.randrange(LW)
            pygame.draw.line(surf, shade(col, 1.25), (x, 0), (x, FLOOR_Y), 1)
    else:
        # dense foreground bamboo stalks with nodes and leaves
        stalk_cols = [col, shade(col, 0.85), shade(col, 1.15)]
        for _ in range(70):
            x = rnd.randrange(LW)
            w = rnd.choice((2, 3, 3, 4))
            c = rnd.choice(stalk_cols)

            def stalk(x, w=w, c=c, seed=rnd.random()):
                r2 = random.Random(seed)
                pygame.draw.rect(surf, c, (x, 0, w, FLOOR_Y))
                surf.fill(shade(c, 1.3), (x, 0, 1, FLOOR_Y))
                y = r2.randint(0, 14)
                while y < FLOOR_Y:
                    surf.fill(shade(c, 0.6), (x - 1, y, w + 2, 1))
                    if r2.random() < 0.3:
                        d = r2.choice((-1, 1))
                        for i in range(5):
                            surf.set_at((x + w // 2 + d * (2 + i), y - i // 2), shade(c, 1.2))
                            surf.set_at((x + w // 2 + d * (2 + i), y - i // 2 + 1), shade(c, 0.9))
                    y += r2.randint(12, 20)
            bg.wrap(stalk, x)
        from ..sprites import BABY_PANDA, from_grid
        panda = from_grid(BABY_PANDA)
        for _ in range(5):
            x = rnd.randrange(LW)

            def sit(x):
                surf.blit(panda, (x, FLOOR_Y - panda.get_height() + 1))
                pygame.draw.line(surf, (110, 190, 75), (x + 8, FLOOR_Y - 9), (x + 11, FLOOR_Y - 16))
            bg.wrap(sit, x)


BIOME = dict(name="BAMBOO GROVE", style="bamboo", stars=False, ambient="leaves", ground_style="moss",
    sky=((150, 215, 195), (250, 236, 195)), far=(125, 175, 150), near=(60, 125, 80),
    ground=(70, 55, 40), ground_top=(120, 195, 85), crystal=(110, 190, 75))

LEVEL = LevelDef(
    name="BAMBOO GROVE", biome=BIOME, director=BambooDirector, boss="panda",
    enemies=(("ninja", 3, 0), ("redpanda", 2, 6), ("crane", 2, 12)),
    length=80, star=4000, tokens=80, music="bamboo", base_diff=0.6, enemy_rate=1.1, hp_mult=3.0, boss_mult=2.4,
    secret=True,
    blurb=("A MISTY BAMBOO FOREST FULL OF", "NINJA PANDAS. FIND YOUR ZEN"), death="PANDA-MONIUM!",
)
