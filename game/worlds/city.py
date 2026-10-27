"""World 2: NEON CITY - skyscrapers, neon signs, hover-car traffic, searchlights. Boss: the Neon Serpent."""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Enemy, Turret
from ..lasers import Bolt
from ..levels import LevelDef
from ..obstacles import INF, Obstacle, Part, register_block
from ..registry import register_boss, register_enemy
from ..settings import FLOOR_Y, W
from ..sprites import draw_text
from ..util import INK as K, WHITE, aim, angle_diff, clamp, rainbow, shade
from ..world import register_backdrop


SIGN_WORDS = ["BAR", "24H", "EAT", "ZAP", "OPEN", "TAXI", "NOOD", "CAFE", "WOW"]
NEON = [(255, 90, 210), (80, 230, 255), (255, 214, 64), (120, 255, 140)]


register_block("glass", ((60, 20, 70), (255, 90, 210), (30, 10, 40)), hp=2)

class Tower(Obstacle):
    """A skyscraper, optionally with a neon sign hanging above it and a rooftop searchlight."""
    scores = True

    def __init__(self, x, top_y, biome, sign_bottom=None, light=False):
        w = random.choice((22, 26, 30))
        super().__init__(x - 3, w + 6, biome)
        self.bx = x
        self.bw = w
        self.top_y = int(top_y)
        self.parts.append(Part(x, top_y, w, FLOOR_Y - top_y, INF, "metal"))
        self.antenna = random.random() < 0.5
        if self.antenna:
            self.parts.append(Part(x + w // 2 - 1, top_y - 10, 2, 10, INF, "metal"))
        self.windows = [(dx, dy, random.choice(NEON) if random.random() < 0.15 else (255, 220, 120))
                        for dy in range(5, FLOOR_Y - int(top_y) - 3, 6)
                        for dx in range(3, w - 3, 5) if random.random() < 0.45]
        self.sign = []
        self.sign_col = random.choice(NEON)
        self.word = random.choice(SIGN_WORDS)
        if sign_bottom is not None:
            y = int(sign_bottom)
            top = max(14, y - random.choice((20, 30)))
            while y > top:
                self.sign.append(Part(x - 3, y - 10, w + 6, 10, 2, "glass"))
                y -= 10
            self.parts += self.sign
            self.sign_top = y
        self.light = light
        self.light_ph = random.uniform(0, 6)
        self.light_a = -2.3
        self.spot = 0.0
        self.alarmed = False

    def move(self, dx, dy=0.0):
        super().move(dx, dy)
        self.bx += dx

    def colors(self, part):
        if part.kind == "glass":
            return [self.sign_col, WHITE, (60, 20, 70)]
        return super().colors(part)

    def special(self, dt, game):
        if not self.light:
            return
        self.light_a = -math.pi * 0.75 + math.sin(self.t * 0.9 + self.light_ph) * 0.38
        ox, oy = self.bx + self.bw / 2, self.top_y
        p = game.player
        dx, dy = p.x - ox, p.y - oy
        inside = (p.alive and math.hypot(dx, dy) < 175
                  and abs(angle_diff(math.atan2(dy, dx), self.light_a)) < 0.15)
        self.spot = self.spot + dt if inside else max(0.0, self.spot - dt)
        if self.spot > 0.35 and not self.alarmed:
            self.alarmed = True
            p = game.player
            game.fx.text(p.x, p.y - 16, "SPOTTED!", (255, 60, 60), scale=2)
            game.audio.play("warn", 0.7)
            for dy in (-24, 24):
                game.enemies.append(HoverCop(W + 14, clamp(p.y + dy, 20, FLOOR_Y - 20), game))

    def draw(self, surf, game):
        t = game.time
        x, w, top = int(self.bx), self.bw, self.top_y
        body = shade(self.biome["near"], 1.6)
        surf.fill(K, (x - 1, top - 1, w + 2, FLOOR_Y - top + 1))
        surf.fill(body, (x, top, w, FLOOR_Y - top))
        surf.fill(shade(body, 1.4), (x, top, 2, FLOOR_Y - top))
        for dx, dy, c in self.windows:
            surf.fill(c, (x + dx, top + dy, 2, 3))
        surf.fill(shade(body, 1.8), (x - 1, top, w + 2, 2))
        if self.antenna:
            surf.fill((140, 140, 160), (x + w // 2 - 1, top - 10, 2, 10))
            if int(t * 2) % 2:
                surf.fill((255, 50, 50), (x + w // 2 - 1, top - 12, 2, 2))
        if self.light:
            ox, oy = x + w // 2, top
            a = self.light_a
            pts = [(ox, oy)] + [(ox + math.cos(a + s) * 175, oy + math.sin(a + s) * 175) for s in (-0.15, 0.15)]
            col = (70, 16, 16) if self.alarmed else (50, 47, 30)
            pygame.draw.polygon(game.light, col, pts)
            surf.fill((255, 240, 160), (ox - 2, oy - 3, 5, 3))
        if self.sign:
            alive = [p for p in self.sign if p.alive]
            if alive:
                cx = int(self.bx + self.bw / 2)
                pygame.draw.line(surf, (90, 90, 110), (cx, 0), (cx, int(min(p.y for p in alive))))
            on = int(t * 7 + self.light_ph) % 13 != 0
            for p in alive:
                r = p.rect
                surf.fill(K, r)
                surf.fill(WHITE if p.flash > 0 else (40, 14, 50), r.inflate(-2, -2))
                pygame.draw.rect(surf, self.sign_col if on else shade(self.sign_col, 0.4), r.inflate(-2, -2), 1)
            if alive and on:
                mid = alive[len(alive) // 2]
                draw_text(surf, self.word[: max(1, (self.bw + 2) // 4)], mid.x + (self.bw + 6) / 2,
                          mid.y + 3, self.sign_col, shadow=None, align="center")

CAR_COLS = [(255, 90, 110), (80, 230, 255), (255, 214, 64), (200, 120, 255)]

class HoverCar(Obstacle):
    """Oncoming flying traffic. Telegraphed by flashing chevrons; shootable."""
    shard_chance = 1.0

    def __init__(self, y, biome, speed):
        super().__init__(W + 30, 20, biome)
        self.y = y
        self.speed = speed
        self.warn = 0.8
        self.col = random.choice(CAR_COLS)
        self.parts.append(Part(self.x, y - 4, 20, 8, 3, "car"))

    def update(self, dt, game):
        self.tick(dt)
        if not self.parts[0].alive:
            self.dead = True
        if self.warn > 0:
            self.warn -= dt
            if self.warn <= 0:
                game.audio.play("dash", 0.5)
            return
        self.move(-(game.scroll + self.speed) * dt)

    def colors(self, part):
        return [self.col, (255, 140, 40), WHITE]

    def on_break(self, part, game):
        game.fx.explode(part.x + 10, part.y + 4, [self.col, (255, 140, 40)])
        game.add_score(30, part.x + 10, part.y - 6)
        game.kills += 1
        game.bump_combo()
        game.audio.play("explode")

    def draw(self, surf, game):
        t = game.time
        if self.warn > 0:
            if int(t * 10) % 2:
                draw_text(surf, "<<", W - 10, int(self.y) - 2, (255, 214, 64))
            return
        p = self.parts[0]
        if not p.alive:
            return
        x, y = int(p.x), int(p.y)
        cone = [(x, y + 4), (x - 40, y - 2), (x - 40, y + 12)]
        pygame.draw.polygon(game.light, (45, 44, 35), cone)
        body = WHITE if p.flash > 0 else self.col
        surf.fill(K, (x - 1, y + 1, 22, 7))
        surf.fill(body, (x, y + 2, 20, 5))
        surf.fill(K, (x + 4, y - 1, 11, 4))
        surf.fill((80, 230, 255), (x + 5, y, 9, 2))
        surf.fill((255, 255, 200), (x, y + 3, 2, 2))
        flame = (255, 140, 40) if int(t * 20) % 2 else (255, 230, 120)
        surf.fill(flame, (x + 20, y + 3, 3, 3))
        surf.fill(shade(body, 0.6), (x + 2, y + 6, 16, 1))

@register_enemy("cop")
class HoverCop(Enemy):
    """Sirens blaring, tracks your height and fires 3-round bursts."""
    hp = 3
    score = 35
    w, h = 12, 6
    shards = 2
    colors = [(170, 170, 195), (60, 120, 255), (220, 40, 60)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.hover_x = random.uniform(220, 290)
        self.cool = random.uniform(1.0, 1.8)
        self.burst = 0
        self.burst_cd = 0.0

    def update(self, dt, game):
        super().update(dt, game)
        p = game.player
        if self.x > self.hover_x:
            self.x -= (game.scroll + 60) * dt
        else:
            self.x -= game.scroll * 0.2 * dt
        self.y += (p.y - self.y) * min(1.0, dt * 0.8)
        self.y = max(18, min(FLOOR_Y - 18, self.y))
        if self.burst > 0:
            self.burst_cd -= dt
            if self.burst_cd <= 0:
                self.burst -= 1
                self.burst_cd = 0.13
                if self.can_shoot(game):
                    vx, vy = aim(self.x - 6, self.y, p.x, p.y, 120)
                    game.bolts.append(Bolt(self.x - 6, self.y, vx, vy, color=(60, 140, 255)))
                    game.audio.play("eshot", 0.5)
            return
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(2.0, 2.8) / (1 + 0.3 * game.diff)
            self.burst = 3

    def draw(self, surf, game):
        self.blit(surf, game, game.art.cop[int(self.t * 8) % 2])

@register_boss("serpent")
class NeonSerpent(Boss):
    """A long robotic dragon weaving across the skyline. Its armored body blocks
    lasers; hit the head (the eye is the weak point)."""
    name = "NEON SERPENT"
    base_hp, hp_tier, size = 90, 50, 14
    colors = [(255, 90, 210), (80, 230, 255), (255, 214, 64)]
    patterns = {
        1: ["volley", "ring", "beam"],
        2: ["volley", "sweep", "ring", "beam"],
        3: ["volley", "ring", "sweep", "beam", "volley"],
    }
    spiral_color = (255, 90, 210)

    def __init__(self, game, tier):
        super().__init__(game, tier)
        self.nseg = 9 + 2 * tier
        self.pts = []
        self.volley = -1
        self.volley_cd = 0.0
        self.mouth = 0.0

    def segments(self):
        out = []
        for i in range(self.nseg):
            j = len(self.pts) - 1 - (i + 1) * 4
            if j < 0:
                break
            out.append(self.pts[j])
        return out

    def head(self):
        return self.x - 7, self.y

    def zones(self):
        z = [(pygame.Rect(int(self.x - 10), int(self.y - 3), 5, 5), "crit"),
             (pygame.Rect(int(self.x - 9), int(self.y - 6), 18, 12), "hit")]
        z += [(pygame.Rect(int(sx - 5), int(sy - 5), 10, 10), "block") for sx, sy in self.segments()]
        return z

    def behave(self, dt, game):
        sp = {1: 1.0, 2: 1.2, 3: 1.45}[self.phase]
        tx = 205 + 70 * math.sin(self.t * 0.7 * sp)
        ty = 85 + 52 * math.sin(self.t * 1.3 * sp)
        k = min(1.0, dt * (1.2 if not self.entered else 4))
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k
        if not self.entered and self.t > 2.5:
            self.entered = True
        if not self.pts or math.hypot(self.x - self.pts[-1][0], self.y - self.pts[-1][1]) >= 2:
            self.pts.append((self.x, self.y))
            del self.pts[: max(0, len(self.pts) - (self.nseg * 4 + 8))]
        self.mouth = max(0.0, self.mouth - dt)
        if self.volley >= 0:
            self.volley_cd -= dt
            if self.volley_cd <= 0:
                segs = self.segments()
                if self.volley < len(segs):
                    sx, sy = segs[self.volley]
                    p = game.player
                    a = math.atan2(p.y - sy, p.x - sx)
                    game.bolts.append(Bolt(sx, sy, math.cos(a) * 85, math.sin(a) * 85, color=(80, 230, 255)))
                    game.audio.play("eshot", 0.3)
                    self.volley += 2 if self.phase == 1 else 1
                    self.volley_cd = 0.09
                else:
                    self.volley = -1
            return
        if self.entered:
            self.tick_patterns(dt, game)

    def attack(self, pat, game):
        self.mouth = 0.4
        if pat == "volley":
            self.volley = 0
        elif pat == "ring":
            n = 12 + 2 * self.phase
            for i in range(n):
                a = math.tau * i / n + self.t
                game.bolts.append(Bolt(self.x, self.y, math.cos(a) * 75, math.sin(a) * 75, color=(255, 90, 210)))
            game.audio.play("eshot")
        elif pat == "beam":
            self.aimed_beam(game, self.head, width=6, color=(255, 90, 210))
        elif pat == "sweep":
            self.sweep(game, self.head, color=(80, 230, 255))

    def draw(self, surf, game):
        t = self.t
        fl = self.flash > 0
        segs = self.segments()
        for i in range(len(segs) - 1, -1, -1):
            sx, sy = int(segs[i][0]), int(segs[i][1])
            c = (255, 90, 210) if i % 2 else (80, 230, 255)
            r = max(3, 6 - i // 5)
            pygame.draw.circle(surf, K, (sx, sy), r + 1)
            pygame.draw.circle(surf, (40, 30, 70), (sx, sy), r)
            pygame.draw.circle(surf, c, (sx, sy), r, 1)
            if (i + int(t * 10)) % self.nseg == 0:
                pygame.draw.circle(surf, WHITE, (sx, sy), 2)
            surf.set_at((sx, sy - r - 1), c)
        x, y = int(self.x), int(self.y)
        body = WHITE if fl else (40, 30, 70)
        neon = rainbow(t) if self.phase == 3 else (255, 90, 210)
        jaw = 3 if self.mouth > 0 else 1
        head = [(x - 10, y - 2), (x - 3, y - 7), (x + 8, y - 6), (x + 9, y + 4), (x - 3, y + 6), (x - 10, y + jaw)]
        pygame.draw.polygon(surf, body, head)
        pygame.draw.polygon(surf, neon, head, 1)
        for s in (-1, 1):
            pygame.draw.line(surf, neon, (x + 3, y - 6), (x + 10, y - 11 + s), 1)
        pygame.draw.circle(surf, (255, 214, 64), (x - 6, y - 1), 2)
        surf.set_at((x - 7, y - 1), K)
        if self.mouth > 0:
            pygame.draw.circle(surf, WHITE, (x - 10, y + 1), 2)

class CityDirector(Director):
    def __init__(self, game, level):
        super().__init__(game, level)
        self.next = 60
        self.car_t = 4.0

    def obstacles(self, dt):
        g = self.g
        if self.travelled(dt, self.next):
            self.next = random.uniform(115, 150) - 12 * min(g.diff, 1.5)
            self.spawn_tower()
        self.car_t -= dt
        if self.late > 6 and self.car_t <= 0:
            self.car_t = random.uniform(2.6, 4.6) / (1 + 0.3 * g.diff)
            lanes = random.sample([26, 46, 66, 86], 2 if random.random() < 0.3 + 0.2 * g.diff else 1)
            for y in lanes:
                g.add_obstacle(HoverCar(y, g.biome, random.uniform(40, 80) + 20 * min(g.diff, 2)))

    def spawn_tower(self):
        g = self.g
        d = min(g.diff, 1.6)
        gap_h = max(66, 92 - 16 * d)
        # keep towers low so there's always plenty of open sky to dodge in
        top_y = random.uniform(96, FLOOR_Y - 26)
        sign_bottom = None
        if random.random() < 0.6 and top_y - gap_h > 26:
            sign_bottom = top_y - gap_h - random.uniform(0, 12)
        light = self.late > 10 and random.random() < 0.35
        t = Tower(W + 6, top_y, g.biome, sign_bottom, light)
        g.add_obstacle(t)
        if self.late > 15 and random.random() < 0.2 + 0.2 * d and FLOOR_Y - top_y > 34:
            g.enemies.append(Turret(t, top_y + 12, g, ax="bx"))
        self.maybe_pickup(t.x + 60, top_y - gap_h / 2)

    def free_y(self):
        return random.uniform(20, 88)


@register_backdrop("city")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    x = 0
    win_cols = [(255, 220, 120), (255, 80, 200), (80, 230, 255)]
    while x < LW:
        bw = rnd.randint(14, 32)
        bh = rnd.randint(30, 80) if idx == 0 else rnd.randint(14, 42)
        top = FLOOR_Y - bh
        pygame.draw.rect(surf, col, (x, top, bw, bh))
        pygame.draw.line(surf, light, (x, top), (x + bw - 1, top))
        if rnd.random() < 0.3:
            pygame.draw.line(surf, col, (x + bw // 2, top), (x + bw // 2, top - 8))
            surf.set_at((x + bw // 2, top - 9), (255, 60, 60))
        for wy in range(top + 4, FLOOR_Y - 4, 5):
            for wx in range(x + 3, x + bw - 3, 4):
                if rnd.random() < 0.3:
                    wc = rnd.choice(win_cols)
                    surf.fill(shade(wc, 0.55 if idx == 0 else 0.9), (wx, wy, 2, 2))
        x += bw + rnd.randint(0, 4)


BIOME = dict(name="NEON CITY", style="city", stars=True, ground_style="street",
    sky=((15, 8, 35), (95, 20, 115)), far=(55, 30, 95), near=(30, 15, 60),
    ground=(25, 15, 45), ground_top=(255, 60, 200), crystal=(255, 90, 210))

LEVEL = LevelDef(
    name="NEON CITY", biome=BIOME, director=CityDirector, boss="serpent",
    enemies=(("drone", 2, 0), ("cop", 2, 4), ("swooper", 2, 12)),
    length=75, star=3000, tokens=25, music="city", base_diff=0.25, enemy_rate=1.1, hp_mult=1.5, boss_mult=1.3,
    blurb=("DODGE TRAFFIC, SMASH NEON SIGNS", "AND STAY OUT OF THE SEARCHLIGHTS"), death="ROADKILL!",
)
