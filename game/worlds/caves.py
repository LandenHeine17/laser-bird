"""World 3: CRYSTAL CAVES - a twisting tunnel, stalactites, crystal clusters. Boss: the Geode Golem."""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Enemy
from ..lasers import Bolt
from ..levels import LevelDef
from ..obstacles import INF, Meteor, Obstacle, Part, block_style, register_block
from ..registry import register_boss
from ..settings import FLOOR_Y, H, W
from ..util import INK as K, WHITE, rainbow, shade
from ..world import register_backdrop


CHUNK = 8

register_block("cave", lambda b: (shade(b["near"], 1.2), shade(b["crystal"], 0.9), shade(b["near"], 0.6)))

class TunnelChunk(Obstacle):
    def __init__(self, x, top, bot, biome):
        super().__init__(x, CHUNK, biome)
        self.top, self.bot = int(top), int(bot)
        if self.top > 0:
            self.parts.append(Part(x, 0, CHUNK, self.top, INF, "cave"))
        if self.bot < FLOOR_Y:
            self.parts.append(Part(x, self.bot, CHUNK, FLOOR_Y - self.bot, INF, "cave"))
        self.specks = [(random.randrange(CHUNK), random.randrange(H)) for _ in range(3)]

    def draw(self, surf, game):
        col, light, dark = block_style("cave", self.biome)
        x = int(self.x)
        if self.top > 0:
            surf.fill(col, (x, 0, CHUNK, self.top))
            surf.fill(light, (x, self.top - 2, CHUNK, 2))
            surf.fill(dark, (x, self.top - 4, CHUNK, 2))
        if self.bot < FLOOR_Y:
            surf.fill(col, (x, self.bot, CHUNK, FLOOR_Y - self.bot))
            surf.fill(light, (x, self.bot, CHUNK, 2))
            surf.fill(dark, (x, self.bot + 2, CHUNK, 2))
        for sx, sy in self.specks:
            if sy < self.top - 5 or sy > self.bot + 5:
                surf.set_at((x + sx, sy), dark)

class Stalactite(Obstacle):
    """Hangs from the cave ceiling, shakes when you approach, then drops."""

    def __init__(self, x, top, biome):
        super().__init__(x, 8, biome)
        self.len = random.randint(14, 24)
        self.parts.append(Part(x + 1, top - 2, 6, self.len, 2, "crystal"))
        self.state = "hang"
        self.vy = 0.0
        self.shake = 0.0

    def update(self, dt, game):
        super().update(dt, game)
        p = self.parts[0]
        if not p.alive:
            self.dead = True
            return
        if self.state == "hang" and 0 < self.x - game.player.x < 70:
            self.state = "shake"
            self.shake = 0.4
            game.audio.play("clank", 0.4)
        elif self.state == "shake":
            self.shake -= dt
            if self.shake <= 0:
                self.state = "fall"
        elif self.state == "fall":
            self.vy += 450 * dt
            self.move(0, self.vy * dt)
            ob, _ = game.solid_at(p.x + 3, p.y + p.h, exclude=self)
            if ob is not None or p.y + p.h >= FLOOR_Y:
                game.break_part(self, p, quiet=True)

    def draw(self, surf, game):
        p = self.parts[0]
        jx = random.randint(-1, 1) if self.state == "shake" else 0
        x, y = int(self.x) + jx, int(p.y)
        col, light, dark = block_style("crystal", self.biome)
        pts = [(x, y), (x + 8, y), (x + 4, y + self.len)]
        pygame.draw.polygon(surf, WHITE if p.flash > 0 else col, pts)
        pygame.draw.polygon(surf, dark, pts, 1)
        pygame.draw.line(surf, light, (x + 2, y + 1), (x + 4, y + self.len - 3))

class CrystalCluster(Obstacle):
    """Breakable crystal spikes growing into the tunnel."""

    def __init__(self, x, base_y, up, biome):
        super().__init__(x, 12, biome)
        n = random.randint(2, 4)
        for i in range(n):
            ox = random.randint(0, 4)
            y = base_y - (i + 1) * 8 if up else base_y + i * 8
            self.parts.append(Part(x + ox, y, 8, 8, 2, "crystal"))

    def draw(self, surf, game):
        col, light, dark = block_style("crystal", self.biome)
        for p in self.parts:
            if not p.alive:
                continue
            x, y = int(p.x), int(p.y)
            pts = [(x + 4, y), (x + 8, y + 3), (x + 7, y + 8), (x + 1, y + 8), (x, y + 3)]
            pygame.draw.polygon(surf, WHITE if p.flash > 0 else col, pts)
            pygame.draw.polygon(surf, dark, pts, 1)
            surf.set_at((x + 3, y + 3), light)

class CrystalSpitter(Enemy):
    """Grows on the cave ceiling/floor and spits fans of crystal shards."""
    hp = 3
    score = 35
    w, h = 7, 5
    rammable = True
    shards = 2
    colors = [(80, 220, 100), (130, 255, 210)]

    def __init__(self, x, y, game, ceiling=False):
        super().__init__(x, y)
        self.ceiling = ceiling
        self.cool = random.uniform(0.8, 1.6)

    def update(self, dt, game):
        super().update(dt, game)
        self.x -= game.scroll * dt
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(2.0, 2.6) / (1 + 0.25 * game.diff)
            if self.can_shoot(game, 30):
                p = game.player
                base = math.atan2(p.y - self.y, p.x - self.x)
                for k in (-1, 0, 1):
                    a = base + k * 0.22
                    game.bolts.append(Bolt(self.x, self.y, math.cos(a) * 95, math.sin(a) * 95,
                                           color=(130, 255, 210)))
                game.audio.play("eshot", 0.5)

    def draw(self, surf, game):
        img = game.art.spitter_down if self.ceiling else game.art.spitter
        self.blit(surf, game, img)
        if 0 < self.cool < 0.3 and int(self.t * 30) % 2:
            surf.fill((255, 255, 255), (int(self.x) - 1, int(self.y) - 1, 2, 2))

@register_boss("golem")
class GeodeGolem(Boss):
    """A walking mountain of rock. Orbiting crystal shields block shots (and can
    be broken). Its glowing core takes critical damage."""
    name = "GEODE GOLEM"
    base_hp, hp_tier, size = 110, 55, 24
    colors = [(130, 255, 210), (120, 110, 130), (255, 255, 255)]
    patterns = {
        1: ["shards", "slam", "shards", "sweep"],
        2: ["shards", "slam", "burst", "sweep"],
        3: ["sweep", "slam", "burst", "shards", "slam"],
    }
    spiral_color = (130, 255, 210)

    def __init__(self, game, tier):
        super().__init__(game, tier)
        self.shields = []
        self.shield_phase = 0
        self.slam_t = 0.0
        self.y = H * 0.5

    def core(self):
        return self.x - 2, self.y + 2

    def eye(self):
        return self.x - 6, self.y - 24

    def spiral_origin(self):
        return self.core()

    def shield_pos(self):
        cx, cy = self.core()
        n = len(self.shields)
        out = []
        for i, s in enumerate(self.shields):
            a = self.t * 1.4 + i * math.tau / max(1, n)
            out.append((s, cx + math.cos(a) * 25, cy + math.sin(a) * 25))
        return out

    def zones(self):
        z = [(pygame.Rect(int(sx - 4), int(sy - 4), 8, 8), "block") for s, sx, sy in self.shield_pos() if s[0] > 0]
        cx, cy = self.core()
        z.append((pygame.Rect(int(cx - 5), int(cy - 5), 10, 10), "crit"))
        z.append((pygame.Rect(int(self.x - 12), int(self.y - 32), 20, 14), "hit"))
        z.append((pygame.Rect(int(self.x - 18), int(self.y - 18), 36, 48), "block"))
        return z

    def take(self, dmg, game, point=None):
        if point is not None and self.entered and self.dying <= 0:
            for s, sx, sy in self.shield_pos():
                if s[0] > 0 and abs(point[0] - sx) <= 4 and abs(point[1] - sy) <= 4:
                    s[0] -= dmg / game.boss_mult
                    s[1] = 0.06
                    if s[0] <= 0:
                        game.fx.burst(sx, sy, [(130, 255, 210), WHITE], n=14, speed=80, life=0.5, grav=100)
                        game.audio.play("crystal")
                        game.fx.text(sx, sy - 8, "SHIELD BROKEN", (130, 255, 210))
                    return "block"
        return super().take(dmg, game, point)

    def behave(self, dt, game):
        if self.shield_phase != self.phase:
            self.shield_phase = self.phase
            self.shields = [[6 + 2 * self.tier, 0.0] for _ in range(2 + self.phase)]
        for s in self.shields:
            s[1] = max(0.0, s[1] - dt)
        self.shields = [s for s in self.shields if s[0] > 0]
        tx = 262.0
        ty = H * 0.5 + math.sin(self.t * 0.6) * 14
        if not self.entered:
            self.x += (tx - self.x) * min(1.0, dt * 1.0)
            self.entered = abs(self.x - tx) < 3
            if int(self.t * 3) != int((self.t - dt) * 3):
                game.fx.add_shake(2)
                game.audio.play("hit", 0.6)
            return
        self.y += (ty - self.y) * min(1.0, dt * 2)
        if self.slam_t > 0:
            self.slam_t -= dt
            if self.slam_t <= 0:
                game.fx.add_shake(7)
                game.audio.play("big_explode", 0.6)
                n = 5 + self.phase
                xs = random.sample(range(20, 230, 18), n)
                for i, x in enumerate(xs):
                    game.add_obstacle(Meteor(x, game.biome, vx=0, vy=150, warn=0.8 + i * 0.05, size=8, kind="crystal"))
            return
        self.tick_patterns(dt, game)

    def attack(self, pat, game):
        if pat == "shards":
            self.fan(game, *self.eye(), 5 + self.phase, spread=0.16, color=(130, 255, 210))
        elif pat == "slam":
            self.slam_t = 0.6
            game.fx.text(self.x - 20, self.y - 40, "!!", (255, 80, 80))
        elif pat == "sweep":
            self.sweep(game, self.eye, n=2 if self.phase == 3 else 1, color=(130, 255, 210))
        elif pat == "burst":
            self.start_spiral(1.1)

    def draw(self, surf, game):
        t = self.t
        x, y = int(self.x), int(self.y)
        fl = self.flash > 0
        rock = WHITE if fl else (110, 100, 120)
        dark = (60, 52, 70)
        cc = (130, 255, 210)
        # legs
        for lx in (x - 12, x + 6):
            surf.fill(K, (lx - 1, y + 20, 10, FLOOR_Y - y - 20))
            surf.fill(dark, (lx, y + 20, 8, FLOOR_Y - y - 20))
        # body
        body = [(x - 18, y - 16), (x + 16, y - 18), (x + 20, y + 10), (x + 10, y + 24), (x - 14, y + 24), (x - 20, y + 4)]
        pygame.draw.polygon(surf, rock, body)
        pygame.draw.polygon(surf, K, body, 1)
        # arms (the left one raises for a slam)
        raise_k = 1.0 if self.slam_t > 0 else 0.0
        for s in (-1, 1):
            ax = x + 21 * s
            ay = y - 12 - (18 if s < 0 else 0) * raise_k
            arm = pygame.Rect(ax - 5, int(ay), 10, 24)
            surf.fill(K, arm.inflate(2, 2))
            surf.fill(rock, arm)
        # shoulder crystals
        for s in (-1, 1):
            sx = x + 12 * s
            pygame.draw.polygon(surf, cc, [(sx - 3, y - 16), (sx, y - 26), (sx + 3, y - 16)])
        # head
        surf.fill(K, (x - 13, y - 33, 22, 16))
        surf.fill(rock, (x - 12, y - 32, 20, 14))
        eye_c = (255, 60, 60) if self.phase == 3 else cc
        surf.fill(eye_c, (x - 9, y - 26, 4, 2))
        surf.fill(eye_c, (x - 1, y - 26, 4, 2))
        # core
        cx, cy = self.core()
        pulse = 1 + int(t * 6) % 2
        pygame.draw.circle(surf, K, (int(cx), int(cy)), 6 + pulse)
        pygame.draw.circle(surf, rainbow(t * 0.5, 0.4) if self.phase == 3 else cc, (int(cx), int(cy)), 5 + pulse)
        surf.fill(WHITE, (int(cx) - 2, int(cy) - 2, 2, 2))
        # orbiting shields
        for s, sx, sy in self.shield_pos():
            pts = [(sx, sy - 5), (sx + 4, sy), (sx, sy + 5), (sx - 4, sy)]
            pygame.draw.polygon(surf, WHITE if s[1] > 0 else cc, pts)
            pygame.draw.polygon(surf, K, pts, 1)

class CaveDirector(Director):
    def __init__(self, game, level):
        super().__init__(game, level)
        self.edge = 0.0
        self.ph = random.uniform(0, 1000)
        self.a, self.b = random.uniform(0, 6), random.uniform(0, 6)
        self.gap = 140.0
        self.c = FLOOR_Y / 2
        self.decor = True

    def target_gap(self):
        g = self.g
        if g.boss_state is not None:
            return FLOOR_Y - 14
        prog = min(1.0, g.stage_time / g.level.length)
        return max(66, 115 - 34 * prog - 10 * min(g.tier, 2))

    def gen_chunk(self, x):
        g = self.g
        self.ph += CHUNK
        self.gap += (self.target_gap() - self.gap) * 0.03
        mid = FLOOR_Y / 2
        amp = max(0.0, (FLOOR_Y - self.gap) / 2 - 6)
        self.c = mid + amp * (0.65 * math.sin(self.ph * 0.009 + self.a) + 0.35 * math.sin(self.ph * 0.023 + self.b))
        top = max(3, self.c - self.gap / 2)
        bot = min(FLOOR_Y - 3, self.c + self.gap / 2)
        g.add_obstacle(TunnelChunk(x, top, bot, g.biome))
        if not self.decor or g.boss_state is not None or not g.player.alive:
            return
        r = random.random()
        if r < 0.03 and g.stage_time > 2:
            g.add_obstacle(Stalactite(x, top, g.biome))
        elif r < 0.055:
            up = random.random() < 0.5
            g.add_obstacle(CrystalCluster(x, bot if up else top, up, g.biome))
        elif r < 0.072 and self.late > 6:
            ceiling = random.random() < 0.5
            g.enemies.append(CrystalSpitter(x + 4, top + 3 if ceiling else bot - 3, g, ceiling=ceiling))
        elif r < 0.082:
            self.maybe_pickup(x, self.c, item=0.35, shards=0.65)

    def prefill(self):
        self.decor = False
        self.edge = -CHUNK
        while self.edge < W + CHUNK:
            self.gen_chunk(self.edge)
            self.edge += CHUNK
        self.decor = True

    def update(self, dt):
        self.edge -= self.g.scroll * dt
        while self.edge < W + CHUNK:
            self.gen_chunk(self.edge)
            self.edge += CHUNK
        super().update(dt)

    def free_y(self):
        return self.c + random.uniform(-0.25, 0.25) * self.gap


@register_backdrop("crystals")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    for _ in range(22 if idx == 0 else 14):
        cx = rnd.randrange(LW)
        w = rnd.randint(8, 20) * (1 if idx == 0 else 1.5)
        h = rnd.randint(25, 70) if idx == 0 else rnd.randint(15, 40)
        fromtop = rnd.random() < 0.45

        def crystal(x, w=w, h=h, fromtop=fromtop):
            if fromtop:
                pts = [(x - w / 2, 0), (x, h), (x + w / 2, 0)]
            else:
                pts = [(x - w / 2, FLOOR_Y), (x, FLOOR_Y - h), (x + w / 2, FLOOR_Y)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.line(surf, light, pts[0], pts[1])
        bg.wrap(crystal, cx)


BIOME = dict(name="CRYSTAL CAVES", style="crystals", stars=False, ground_style="rock",
    sky=((8, 25, 45), (30, 85, 115)), far=(40, 95, 135), near=(20, 60, 90),
    ground=(15, 35, 55), ground_top=(80, 230, 255), crystal=(130, 255, 210))

LEVEL = LevelDef(
    name="CRYSTAL CAVES", biome=BIOME, director=CaveDirector, boss="golem",
    enemies=(("bat", 3, 0), ("drone", 1, 10), ("swooper", 1, 20)),
    length=75, star=3200, tokens=40, music="caves", base_diff=0.45, enemy_rate=1.15, hp_mult=2.5, boss_mult=1.9,
    blurb=("A TWISTING TUNNEL - WATCH OUT", "FOR FALLING STALACTITES!"), death="CRUSHED!",
)
