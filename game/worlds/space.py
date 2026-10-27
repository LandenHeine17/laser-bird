"""World 5: DEEP SPACE - low gravity, asteroids, black holes, satellite debris. Boss: the Mothership."""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Enemy
from ..lasers import Beam, Bolt
from ..levels import LevelDef
from ..obstacles import Obstacle, Part, block_style
from ..registry import register_boss, register_enemy
from ..settings import FLOOR_Y, W
from ..util import INK as K, WHITE, aim, rainbow, seg_dist, shade
from ..world import register_backdrop


class Asteroid(Obstacle):
    """Drifting rock. Big ones split into smaller ones when destroyed."""
    RADII = {1: 4, 2: 7, 3: 11}

    def __init__(self, cx, cy, size, biome, vx=0.0, vy=0.0):
        r = self.RADII[size]
        super().__init__(cx - r, 2 * r, biome)
        self.cx, self.cy, self.r, self.size = cx, cy, r, size
        self.vx, self.vy = vx, vy
        self.rot = random.uniform(0, 6.28)
        self.spin = random.uniform(-2, 2)
        side = int(r * 1.5)
        self.parts.append(Part(cx - side / 2, cy - side / 2, side, side, {1: 1, 2: 3, 3: 5}[size], "rock"))
        n = 7
        self.shape = [(math.cos(math.tau * i / n), math.sin(math.tau * i / n), random.uniform(0.75, 1.15))
                      for i in range(n)]

    def update(self, dt, game):
        self.tick(dt)
        if not self.parts[0].alive:
            self.dead = True
            return
        dx = (self.vx - game.scroll) * dt
        dy = self.vy * dt
        if not 10 < self.cy + dy < FLOOR_Y - 10:
            self.vy = -self.vy
            dy = 0
        self.move(dx, dy)
        self.cx += dx
        self.cy += dy
        self.rot += self.spin * dt

    def on_break(self, part, game):
        if self.size > 1:
            for s in (-1, 1):
                game.add_obstacle(Asteroid(self.cx, self.cy, self.size - 1, self.biome,
                                           self.vx + random.uniform(-10, 30), s * random.uniform(30, 60)))

    def draw(self, surf, game):
        p = self.parts[0]
        c, s = math.cos(self.rot), math.sin(self.rot)
        pts = [(self.cx + (x * c - y * s) * self.r * k, self.cy + (x * s + y * c) * self.r * k) for x, y, k in self.shape]
        col, light, dark = block_style("rock", self.biome)
        pygame.draw.polygon(surf, WHITE if p.flash > 0 else (125, 110, 120), pts)
        pygame.draw.polygon(surf, K, pts, 1)
        if self.r > 5:
            surf.fill(dark, (int(self.cx - 2), int(self.cy), 3, 2))
            surf.fill((160, 145, 155), (int(self.cx - self.r / 2), int(self.cy - self.r / 2), 2, 2))

class GravityWell(Obstacle):
    """A mini black hole: pulls you in and bends every laser nearby. The core hurts."""
    solid = False
    scores = True
    R = 95

    def __init__(self, cx, cy, biome):
        super().__init__(cx - 8, 16, biome)
        self.cy = cy

    @property
    def cx(self):
        return self.x + 8

    def special(self, dt, game):
        cx, cy, R = self.cx, self.cy, self.R
        p = game.player
        if p.alive:
            dx, dy = cx - p.x, cy - p.y
            d = math.hypot(dx, dy)
            if 1 < d < R:
                f = 340 * (1 - d / R)
                p.vy += dy / d * f * dt
                p.x += dx / d * f * 0.2 * dt
        for o in game.shots + game.bolts:
            dx, dy = cx - o.x, cy - o.y
            d = math.hypot(dx, dy)
            if 1 < d < R:
                f = 900 * (1 - d / R)
                o.vx += dx / d * f * dt
                o.vy += dy / d * f * dt
            if d < 6:
                o.alive = False

    def hazard_hits(self, px, py, r):
        return math.hypot(px - self.cx, py - self.cy) < 6 + r

    def draw(self, surf, game):
        t = game.time
        cx, cy = int(self.cx), int(self.cy)
        for i in range(0, 360, 30):
            a = math.radians(i) + t * 0.4
            surf.set_at((int(cx + math.cos(a) * self.R), int(cy + math.sin(a) * self.R)), (90, 60, 140))
        for i in range(22):
            k = ((t * 0.6 + i / 22) % 1.0)
            rr = 26 * (1 - k) + 6
            a = i * 2.4 + t * (3 + 4 * k)
            col = (255, 160, 60) if i % 3 == 0 else (200, 90, 255)
            surf.set_at((int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr * 0.6)), col)
        pygame.draw.circle(surf, (200, 90, 255) if int(t * 10) % 2 else WHITE, (cx, cy), 7, 1)
        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), 6)

class SpaceDebris(Obstacle):
    """A tumbling broken satellite. Its spinning solar panel is a hazard."""
    solid = False
    scores = True
    L = 22

    def __init__(self, cx, cy, biome):
        super().__init__(cx - self.L, self.L * 2, biome)
        self.cy = cy
        self.a = random.uniform(0, 3.14)
        self.spin = random.choice((-1, 1)) * random.uniform(0.8, 1.4)

    def update(self, dt, game):
        super().update(dt, game)
        self.a += self.spin * dt

    def ends(self):
        cx = self.x + self.L
        dx, dy = math.cos(self.a) * self.L, math.sin(self.a) * self.L
        return (cx - dx, self.cy - dy), (cx + dx, self.cy + dy)

    def hazard_hits(self, px, py, r):
        (x0, y0), (x1, y1) = self.ends()
        return seg_dist(px, py, x0, y0, x1, y1) < 3 + r

    def draw(self, surf, game):
        (x0, y0), (x1, y1) = self.ends()
        pygame.draw.line(surf, K, (x0, y0), (x1, y1), 6)
        pygame.draw.line(surf, (60, 100, 220), (x0, y0), (x1, y1), 4)
        for i in range(1, 8):
            f = i / 8
            surf.set_at((int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f)), (160, 200, 255))
        cx = int(self.x + self.L)
        surf.fill(K, (cx - 4, int(self.cy) - 4, 8, 8))
        surf.fill((190, 190, 210), (cx - 3, int(self.cy) - 3, 6, 6))
        if int(game.time * 3) % 2:
            surf.set_at((cx, int(self.cy) - 4), (255, 60, 60))

@register_enemy("ufo")
class UFO(Enemy):
    """Hovers up high and drops a tractor beam that drags you upward."""
    hp = 4
    score = 45
    w, h = 11, 6
    shards = 2
    colors = [(170, 170, 195), (80, 220, 100), (80, 230, 255)]

    def __init__(self, x, y, game):
        super().__init__(x, random.uniform(22, 55))
        self.cycle = random.uniform(0, 4)
        self.cool = random.uniform(1.5, 2.5)

    @property
    def beam_state(self):
        ph = (self.t + self.cycle) % 4.0
        return "warn" if 1.5 < ph < 2.0 else ("on" if ph >= 2.0 and ph < 3.6 else "off")

    def update(self, dt, game):
        super().update(dt, game)
        p = game.player
        target_x = p.x + 30
        self.x += max(-50, min(20, (target_x - self.x) * 0.8)) * dt - game.scroll * 0.15 * dt
        self.y += math.sin(self.t * 2) * 6 * dt
        if self.beam_state == "on" and p.alive and p.y > self.y:
            spread = 6 + (p.y - self.y) * 0.3
            if abs(p.x - self.x) < spread:
                p.vy -= 900 * dt
                p.vy = max(p.vy, -120)
                if random.random() < 0.3:
                    game.fx.burst(p.x, p.y, [(80, 220, 100)], n=1, speed=30, life=0.3, grav=-60)
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(2.2, 3.2)
            if p.alive and abs(self.x - p.x) > 20 and 0 < self.x < W:
                vx, vy = aim(self.x, self.y, p.x, p.y, 90)
                game.bolts.append(Bolt(self.x, self.y + 3, vx, vy, color=(80, 220, 100)))

    def offscreen(self):
        return self.x < -30 or self.t > 25

    def draw(self, surf, game):
        st = self.beam_state
        if st == "on" or (st == "warn" and int(self.t * 12) % 2):
            top = int(self.y + 4)
            col = (40, 150, 70) if st == "on" else (15, 60, 25)
            shift = int(self.t * 40) % 4
            for yy in range(top + shift, FLOOR_Y, 4):
                half = 4 + (yy - top) * 0.3
                pygame.draw.line(game.light, col, (int(self.x - half), yy), (int(self.x + half), yy))
        img = game.art.ufo
        self.blit(surf, game, img)
        if int(self.t * 6) % 2:
            surf.set_at((int(self.x) - 3 + int(self.t * 6) % 3 * 3, int(self.y)), (255, 214, 64))

@register_enemy("mine")
class SpaceMine(Enemy):
    """Arms when you get close, then bursts into a ring of bolts. Shoot it first."""
    hp = 2
    score = 20
    w, h = 7, 7
    colors = [(220, 40, 60), (170, 170, 195)]

    def __init__(self, x, y, game, vx=None):
        super().__init__(x, y)
        self.vx = vx if vx is not None else -game.scroll * 0.6
        self.vy = random.uniform(-8, 8)
        self.arm = -1.0

    def update(self, dt, game):
        super().update(dt, game)
        self.x += self.vx * dt
        self.y += self.vy * dt
        p = game.player
        if self.arm < 0 and p.alive and math.hypot(p.x - self.x, p.y - self.y) < 48:
            self.arm = 0.8
            game.audio.play("charge", 0.5)
        if self.arm > 0:
            self.arm -= dt
            if self.arm <= 0:
                self.alive = False
                for i in range(10):
                    a = math.tau * i / 10
                    game.bolts.append(Bolt(self.x, self.y, math.cos(a) * 85, math.sin(a) * 85,
                                           color=(255, 80, 80)))
                game.fx.explode(self.x, self.y, [(255, 80, 80), (255, 140, 40)])
                game.audio.play("explode", 0.7)

    def draw(self, surf, game):
        blink = self.arm > 0 and int(self.t * (20 if self.arm < 0.4 else 10)) % 2
        img = game.art.white(game.art.mine) if blink else game.art.mine
        surf.blit(img, (int(self.x) - 4, int(self.y) - 4))
        if self.arm > 0:
            pygame.draw.circle(surf, (255, 80, 80), (int(self.x), int(self.y)), int(6 + (0.8 - self.arm) * 10), 1)

@register_boss("mothership")
class Mothership(Boss):
    """Huge saucer. Laser curtains with a single gap, a tractor beam, mines and
    escort UFOs. The hatch underneath opens up during big attacks."""
    name = "THE MOTHERSHIP"
    base_hp, hp_tier, size = 130, 60, 30
    colors = [(170, 170, 195), (80, 220, 100), (80, 230, 255)]
    patterns = {
        1: ["spiral", "curtain", "mines"],
        2: ["tractor", "curtain", "spiral", "mines"],
        3: ["curtain", "tractor", "spiral", "escort", "curtain"],
    }
    spiral_color = (80, 220, 100)

    def __init__(self, game, tier):
        super().__init__(game, tier)
        self.y = 42
        self.tractor = 0.0
        self.hatch = 0.0

    @property
    def hatch_open(self):
        return self.hatch > 0 or self.tractor > 0 or self.phase == 3

    def spiral_origin(self):
        return self.x, self.y + 6

    def zones(self):
        z = [(pygame.Rect(int(self.x - 10), int(self.y - 15), 20, 11), "hit")]
        if self.hatch_open:
            z.append((pygame.Rect(int(self.x - 6), int(self.y + 3), 12, 8), "crit"))
        z.append((pygame.Rect(int(self.x - 36), int(self.y - 5), 72, 12), "block"))
        return z

    def behave(self, dt, game):
        self.hatch = max(0.0, self.hatch - dt)
        amp = 30 if self.phase == 3 else 14
        ty = 46 + math.sin(self.t * 0.5) * amp
        tx = 240.0
        if not self.entered:
            self.x += (tx - self.x) * min(1.0, dt * 1.0)
            self.entered = abs(self.x - tx) < 3
            return
        self.x = tx + math.sin(self.t * 0.37) * 10
        self.y += (ty - self.y) * min(1.0, dt * 2)
        if self.tractor > 0:
            self.tractor -= dt
            p = game.player
            if p.alive:
                dx, dy = self.x - p.x, self.y - p.y
                d = max(1.0, math.hypot(dx, dy))
                p.x += dx / d * 40 * dt
                p.vy += dy / d * 380 * dt
            if random.random() < 0.3:
                self.fan(game, self.x, self.y + 6, 1, speed=90, color=(80, 220, 100))
            return
        self.tick_patterns(dt, game)

    def attack(self, pat, game):
        if pat == "curtain":
            self.hatch = 1.8
            safe_y = random.uniform(30, FLOOR_Y - 30)
            y = 16
            while y < FLOOR_Y - 6:
                if abs(y - safe_y) > 22:
                    game.beams.append(Beam((W + 10, y), math.pi, warn=1.1, fire=0.6, width=4,
                                           color=(80, 220, 100), length=W + 30, owner=self))
                y += 15
            game.safe_marks.append([safe_y, 1.7])
            game.audio.play("charge")
        elif pat == "tractor":
            self.tractor = 2.4
            game.fx.text(self.x, self.y + 20, "TRACTOR BEAM!", (80, 220, 100))
            game.audio.play("warn", 0.5)
        elif pat == "spiral":
            self.hatch = 1.4
            self.start_spiral(1.3)
        elif pat == "mines":
            for k in range(3 + self.phase // 2):
                game.enemies.append(SpaceMine(self.x - 10 * k, self.y + 10, game, vx=-60 - 15 * k))
            game.audio.play("eshot")
        elif pat == "escort":
            for dy in (-1, 1):
                game.enemies.append(UFO(W + 10, 0, game))

    def draw(self, surf, game):
        t = self.t
        x, y = int(self.x), int(self.y)
        fl = self.flash > 0
        if self.tractor > 0:
            p = game.player
            pygame.draw.polygon(game.light, (22, 70, 33),
                                [(x - 6, y + 6), (x + 6, y + 6), (int(p.x) + 12, int(p.y)), (int(p.x) - 12, int(p.y))])
        hull = WHITE if fl else (150, 150, 175)
        pygame.draw.ellipse(surf, K, (x - 37, y - 7, 74, 16))
        pygame.draw.ellipse(surf, hull, (x - 36, y - 6, 72, 14))
        pygame.draw.ellipse(surf, (90, 90, 115), (x - 30, y + 1, 60, 6))
        for i in range(10):
            lx = x - 30 + i * 6.6
            c = rainbow(t * 0.8 + i * 0.1) if (i + int(t * 8)) % 3 == 0 else (60, 60, 80)
            surf.fill(c, (int(lx), y - 1, 2, 2))
        dome = pygame.Rect(x - 11, y - 16, 22, 14)
        pygame.draw.ellipse(surf, K, dome.inflate(2, 2))
        pygame.draw.ellipse(surf, (60, 150, 190) if not fl else WHITE, dome)
        # the pilot
        surf.fill((80, 220, 100), (x - 3, y - 11, 6, 6))
        if int(t * 2) % 5:
            surf.fill(K, (x - 2, y - 9, 1, 2))
            surf.fill(K, (x + 1, y - 9, 1, 2))
        surf.fill((180, 230, 255), (x - 7, y - 14, 3, 2))
        if self.hatch_open:
            c = (255, 80, 80) if self.phase == 3 else (80, 255, 120)
            pygame.draw.ellipse(surf, c, (x - 6, y + 4, 12, 6))
            surf.fill(WHITE, (x - 2, y + 6, 4, 2))
        else:
            pygame.draw.ellipse(surf, (70, 70, 90), (x - 6, y + 4, 12, 6))

class SpaceDirector(Director):
    def __init__(self, game, level):
        super().__init__(game, level)
        self.ast_t = 1.0
        self.well_t = 7.0
        self.debris_t = 4.0
        self.item_t = 5.0

    def obstacles(self, dt):
        g = self.g
        self.ast_t -= dt
        if self.ast_t <= 0:
            self.ast_t = random.uniform(0.9, 1.8) / (1 + 0.35 * g.diff)
            size = random.choices([1, 2, 3], [3, 3, 2])[0]
            g.add_obstacle(Asteroid(W + 15, random.uniform(20, FLOOR_Y - 20), size, g.biome,
                                    vx=random.uniform(-25, 15), vy=random.uniform(-20, 20)))
        self.well_t -= dt
        if self.well_t <= 0:
            self.well_t = random.uniform(9, 14)
            g.add_obstacle(GravityWell(W + 40, random.uniform(45, 120), g.biome))
        self.debris_t -= dt
        if self.late > 4 and self.debris_t <= 0:
            self.debris_t = random.uniform(5, 8) / (1 + 0.2 * g.diff)
            g.add_obstacle(SpaceDebris(W + 30, random.uniform(30, FLOOR_Y - 30), g.biome))
        self.item_t -= dt
        if self.item_t <= 0:
            self.item_t = random.uniform(5, 8)
            self.maybe_pickup(W + 20, random.uniform(30, 140), item=0.4, shards=0.6)


@register_backdrop("space")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    if idx == 0:
        for _ in range(3):
            px, py = rnd.randrange(LW), rnd.randint(25, 100)
            pr = rnd.randint(8, 22)
            pc = shade(rnd.choice([(200, 90, 160), (90, 160, 220), (220, 170, 90)]), 0.7)

            def planet(x, py=py, pr=pr, pc=pc):
                pygame.draw.circle(surf, pc, (x, py), pr)
                pygame.draw.circle(surf, shade(pc, 1.3), (x - pr // 3, py - pr // 3), max(2, pr // 3))
                pygame.draw.ellipse(surf, shade(pc, 1.5), (x - pr * 1.7, py - 2, pr * 3.4, 5), 1)
            bg.wrap(planet, px)
    else:
        for _ in range(16):
            ax, ay = rnd.randrange(LW), rnd.randint(20, FLOOR_Y - 10)
            pts = []
            n = rnd.randint(5, 8)
            rr = rnd.randint(3, 8)
            for i in range(n):
                a = math.tau * i / n
                d = rr * rnd.uniform(0.6, 1.2)
                pts.append((math.cos(a) * d, math.sin(a) * d))

            def rock(x, ay=ay, pts=pts):
                pygame.draw.polygon(surf, col, [(x + px, ay + py) for px, py in pts])
            bg.wrap(rock, ax)


BIOME = dict(name="DEEP SPACE", style="space", stars=True, ground_style="planet",
    sky=((2, 2, 12), (25, 12, 45)), far=(70, 45, 110), near=(45, 35, 75),
    ground=(30, 60, 140), ground_top=(120, 220, 255), crystal=(200, 170, 255))

LEVEL = LevelDef(
    name="DEEP SPACE", biome=BIOME, director=SpaceDirector, boss="mothership",
    enemies=(("ufo", 2, 0), ("mine", 2, 4), ("drone", 1, 10)),
    length=85, star=4200, tokens=70, music="space", base_diff=0.75, enemy_rate=1.1, hp_mult=4.4, boss_mult=3.1,
    gravity=0.55, flap=0.72,
    blurb=("LOW GRAVITY! ASTEROIDS SPLIT AND", "BLACK HOLES BEND YOUR LASERS"), death="BURNED UP!",
)
