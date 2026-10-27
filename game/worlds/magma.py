"""World 4: MAGMA DEPTHS - lava floor, geysers, basalt spires, meteors. Boss: the Lava Leviathan."""
import math
import random

import pygame

from ..bosses import Boss
from ..director import Director
from ..enemies import Enemy
from ..lasers import Bolt
from ..levels import LevelDef
from ..obstacles import Geyser, Meteor, Obstacle, Pillar, rect_hit, register_block
from ..registry import register_boss, register_enemy
from ..settings import FLOOR_Y, W
from ..util import INK as K, WHITE
from ..world import register_backdrop


def _basalt_decor(surf, r, part, light, dark, t):
    glow = (255, 120, 30) if math.sin(t * 3 + r.x * 0.1) > -0.2 else (200, 70, 20)
    pygame.draw.lines(surf, glow, False, [(r.x + 4, r.y + 1), (r.x + 8, r.y + r.h // 2), (r.x + 6, r.bottom - 2)])


register_block("basalt", ((55, 38, 45), (90, 65, 70), (25, 15, 20)), decor=_basalt_decor)

class LavaWave(Obstacle):
    """A rolling wall of lava you have to hop over (Leviathan attack)."""
    solid = False

    def __init__(self, x, biome, hmax=55, speed=115):
        super().__init__(x, 26, biome)
        self.hmax, self.speed = hmax, speed

    def update(self, dt, game):
        self.tick(dt)
        self.move(-self.speed * dt)

    @property
    def h(self):
        return self.hmax * min(1.0, self.t / 0.7)

    def hazard_hits(self, px, py, r):
        return rect_hit(pygame.Rect(int(self.x) + 3, int(FLOOR_Y - self.h), self.w - 6, int(self.h)), px, py, r)

    def draw(self, surf, game):
        x, h = int(self.x), self.h
        top = FLOOR_Y - h
        pts = [(x, FLOOR_Y), (x + 2, top + 8), (x + 8, top), (x + 18, top + 2), (x + 26, FLOOR_Y)]
        pygame.draw.polygon(surf, (255, 110, 20), pts)
        pygame.draw.polygon(surf, (150, 30, 10), pts, 1)
        pygame.draw.line(surf, (255, 230, 120), (x + 4, top + 6), (x + 10, top + 1), 2)
        if random.random() < 0.4:
            game.fx.burst(x + 8, top, [(255, 160, 40), (255, 230, 120)], n=1, speed=40, life=0.5, grav=120)

@register_enemy("imp")
class FireImp(Enemy):
    """Flits around erratically and lobs arcing fireballs."""
    hp = 2
    score = 30
    w, h = 9, 7
    colors = [(220, 40, 60), (255, 140, 40), (255, 214, 64)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.base_y = y
        self.hover_x = random.uniform(180, 280)
        self.cool = random.uniform(1.0, 2.0)
        self.ph = random.uniform(0, 6)

    def update(self, dt, game):
        super().update(dt, game)
        if self.x > self.hover_x:
            self.x -= (game.scroll + 40) * dt
        else:
            self.x -= game.scroll * 0.3 * dt
        self.x += math.sin(self.t * 3 + self.ph) * 20 * dt
        self.y = self.base_y + math.sin(self.t * 2.2 + self.ph) * 14 + math.sin(self.t * 5.1) * 4
        self.cool -= dt
        if self.cool <= 0:
            self.cool = random.uniform(1.8, 2.6) / (1 + 0.3 * game.diff)
            if self.can_shoot(game, 40):
                p = game.player
                T, g = 1.1, 160.0
                vx = (p.x - self.x) / T
                vy = (p.y - self.y) / T - 0.5 * g * T
                game.bolts.append(Bolt(self.x, self.y, vx, vy, color=(255, 140, 40), r=3, grav=g))
                game.audio.play("eshot", 0.5)

    def draw(self, surf, game):
        self.blit(surf, game, game.art.imp[int(self.t * 10) % 2])

@register_enemy("fish")
class LavaFish(Enemy):
    """Bubbles warn where it is about to leap out of the lava."""
    hp = 1
    score = 25
    w, h = 9, 5
    colors = [(255, 140, 40), (255, 214, 64)]

    def __init__(self, x, game):
        super().__init__(x, FLOOR_Y + 8)
        self.warn = 0.8
        self.vy = -random.uniform(230, 290)
        self.vx = -random.uniform(10, 40)

    @classmethod
    def spawn(cls, game, y):
        game.enemies.append(cls(random.uniform(110, W - 30), game))

    def update(self, dt, game):
        super().update(dt, game)
        if self.warn > 0:
            self.warn -= dt
            self.x -= game.scroll * dt
            if random.random() < 0.5:
                game.fx.burst(self.x, FLOOR_Y, [(255, 230, 120), (255, 160, 40)], n=1, speed=30, life=0.3,
                              grav=60, angle=-math.pi / 2, spread=1.0)
            return
        self.vy += 400 * dt
        self.x += (self.vx - game.scroll * 0.5) * dt
        self.y += self.vy * dt
        if self.vy > 0 and self.y > FLOOR_Y + 10:
            self.alive = False
            game.fx.burst(self.x, FLOOR_Y, [(255, 160, 40)], n=6, speed=50, life=0.4, grav=150,
                          angle=-math.pi / 2, spread=1.5)

    def draw(self, surf, game):
        if self.warn > 0:
            if int(self.t * 12) % 2:
                pygame.draw.ellipse(surf, (255, 230, 120), (int(self.x) - 5, FLOOR_Y - 2, 10, 4), 1)
            return
        a = math.degrees(math.atan2(self.vy, self.vx))
        img = pygame.transform.rotate(game.art.fish, 180 - a)
        self.blit(surf, game, img)

@register_boss("leviathan")
class LavaLeviathan(Boss):
    """Rises out of the lava. Lobs fireballs, sends lava waves, and dives to
    lunge up from beneath you (watch the bubbles)."""
    name = "LAVA LEVIATHAN"
    base_hp, hp_tier, size = 110, 55, 18
    colors = [(255, 110, 20), (255, 214, 64), (150, 30, 10)]
    patterns = {
        1: ["lob", "wave", "lob", "geysers"],
        2: ["lob", "sweep", "wave", "dive", "geysers"],
        3: ["dive", "lob", "wave", "sweep", "geysers"],
    }

    def __init__(self, game, tier):
        super().__init__(game, tier)
        self.bx = 255.0
        self.x = self.bx
        self.y = FLOOR_Y + 40
        self.dive_t = 0.0
        self.mouth = 0.0

    def mouth_pos(self):
        return self.x - 12, self.y + 3

    def zones(self):
        if self.y > FLOOR_Y - 8:
            return []
        z = [(pygame.Rect(int(self.x - 8), int(self.y - 6), 5, 5), "crit"),
             (pygame.Rect(int(self.x - 14), int(self.y - 8), 24, 16), "hit")]
        for i in range(1, 6):
            nx, ny = self.neck(i / 6)
            z.append((pygame.Rect(int(nx - 6), int(ny - 6), 12, 12), "block"))
        return z

    def neck(self, f):
        x0, y0 = self.bx + 14, FLOOR_Y + 6
        x1, y1 = self.x + 6, self.y + 4
        cx = (x0 + x1) / 2 + 18 + math.sin(self.t * 2) * 6
        cy = (y0 + y1) / 2
        u = 1 - f
        return (u * u * x0 + 2 * u * f * cx + f * f * x1, u * u * y0 + 2 * u * f * cy + f * f * y1)

    def behave(self, dt, game):
        self.mouth = max(0.0, self.mouth - dt)
        hover_y = 62 + math.sin(self.t * 0.9 * (1.4 if self.phase == 3 else 1)) * 28
        if not self.entered:
            self.y += (hover_y - self.y) * min(1.0, dt * 1.2)
            if random.random() < 0.5:
                game.fx.burst(self.x, FLOOR_Y, [(255, 160, 40), (255, 230, 120)], n=2, speed=70, life=0.5, grav=200,
                              angle=-math.pi / 2, spread=1.4)
            self.entered = abs(self.y - hover_y) < 3
            return
        if self.dive_t > 0:
            self.dive_t -= dt
            target = FLOOR_Y + 45 if self.dive_t > 0.6 else hover_y
            self.y += (target - self.y) * min(1.0, dt * 4)
            return
        self.y += (hover_y - self.y) * min(1.0, dt * 3)
        self.x = self.bx + math.sin(self.t * 0.5) * 8
        self.tick_patterns(dt, game)

    def attack(self, pat, game):
        p = game.player
        self.mouth = 0.4
        if pat == "lob":
            mx, my = self.mouth_pos()
            for k in range(3 + (1 if self.phase == 3 else 0)):
                T = 1.0 + k * 0.18
                g = 170.0
                tx = p.x + random.uniform(-25, 25)
                vx = (tx - mx) / T
                vy = (p.y - my) / T - 0.5 * g * T
                game.bolts.append(Bolt(mx, my, vx, vy, color=(255, 140, 40), r=3, grav=g))
            game.audio.play("eshot")
        elif pat == "wave":
            game.add_obstacle(LavaWave(self.x - 30, game.biome, hmax=min(75, 50 + 8 * self.phase + 5 * self.tier)))
            game.audio.play("beam", 0.6)
        elif pat == "geysers":
            xs = sorted(random.sample(range(15, 225, 22), 6))
            for i, x in enumerate(xs):
                game.add_obstacle(Geyser(x, game.biome, hmax=random.randint(55, 105), once=True, delay=i * 0.12))
        elif pat == "sweep":
            self.sweep(game, self.mouth_pos, color=(255, 140, 40))
        elif pat == "dive":
            self.dive_t = 2.6
            game.add_obstacle(Geyser(p.x - 11, game.biome, hmax=FLOOR_Y - 15, w=22, warn=1.1, erupt=0.7, once=True,
                                     delay=0.6))
            game.fx.text(p.x, FLOOR_Y - 20, "BELOW!", (255, 120, 40))

    def draw(self, surf, game):
        if self.y > FLOOR_Y + 6:
            return
        t = self.t
        fl = self.flash > 0
        scale = WHITE if fl else (150, 35, 20)
        belly = WHITE if fl else (255, 140, 40)
        for i in range(8, 0, -1):
            nx, ny = self.neck(i / 9)
            r = 7 - i // 4
            pygame.draw.circle(surf, K, (int(nx), int(ny)), r + 1)
            pygame.draw.circle(surf, scale, (int(nx), int(ny)), r)
            surf.set_at((int(nx) - 2, int(ny)), belly)
        x, y = int(self.x), int(self.y)
        jaw = 5 if self.mouth > 0 else 1
        head = [(x - 16, y - 2), (x - 6, y - 9), (x + 8, y - 8), (x + 12, y + 2), (x + 4, y + 8), (x - 14, y + jaw + 2)]
        pygame.draw.polygon(surf, scale, head)
        pygame.draw.polygon(surf, K, head, 1)
        pygame.draw.line(surf, belly, (x - 14, y + jaw + 1), (x + 2, y + 6))
        for s in (0, 6):
            pygame.draw.polygon(surf, (90, 20, 15), [(x + s, y - 8), (x + s + 4, y - 15), (x + s + 5, y - 7)])
        eye_c = (255, 60, 60) if self.phase == 3 else (255, 230, 80)
        pygame.draw.circle(surf, eye_c, (x - 6, y - 4), 2)
        surf.set_at((x - 7, y - 4), K)
        if self.mouth > 0 or int(t * 4) % 3 == 0:
            game.fx.burst(x - 15, y + 3, [(255, 160, 40)], n=1, speed=20, life=0.4, grav=120)

class MagmaDirector(Director):
    def __init__(self, game, level):
        super().__init__(game, level)
        self.meteor_t = 6.0

    def obstacles(self, dt):
        g = self.g
        if self.travelled(dt, 125 - 12 * min(g.diff, 1.5)):
            self.spawn_column()
        self.meteor_t -= dt
        if self.late > 8 and self.meteor_t <= 0:
            self.meteor_t = random.uniform(2.5, 4.5) / (1 + 0.3 * g.diff)
            g.add_obstacle(Meteor(random.uniform(140, W + 60), g.biome))

    def spawn_column(self):
        g = self.g
        d = min(g.diff, 1.6)
        open_h = max(60, 86 - 16 * d)
        kind = "rock" if random.random() < 0.35 else "basalt"
        r = random.random()
        x = W + 4
        if r < 0.4:
            top = random.uniform(open_h + 10, FLOOR_Y - 30)
            pl = Pillar(x, 0, top, kind, g.biome, w=16)
            mid = top / 2
        elif r < 0.75:
            bot = random.uniform(30, FLOOR_Y - open_h - 10)
            pl = Pillar(x, bot, FLOOR_Y, kind, g.biome, w=16)
            mid = (bot + FLOOR_Y) / 2
        else:
            c = random.uniform(14 + open_h / 2, FLOOR_Y - 14 - open_h / 2)
            pl = Pillar(x, c - open_h / 2, c + open_h / 2, kind, g.biome, w=16)
            mid = c
        g.add_obstacle(pl)
        if random.random() < 0.5 + 0.2 * d:
            g.add_obstacle(Geyser(x + 62, g.biome, hmax=random.uniform(45, 95)))
        self.maybe_pickup(x + 40, mid)


@register_backdrop("volcano")
def paint_backdrop(bg, surf, idx, col, light, rnd):
    """Background layer {0: far, 1: near} for this world."""
    LW = bg.LW
    if idx == 0:
        for _ in range(4):
            vx = rnd.randrange(LW)
            vw, vh = rnd.randint(70, 120), rnd.randint(60, 100)

            def volcano(x, vw=vw, vh=vh):
                top = FLOOR_Y - vh
                pts = [(x - vw, FLOOR_Y), (x - 8, top), (x + 8, top), (x + vw, FLOOR_Y)]
                pygame.draw.polygon(surf, col, pts)
                pygame.draw.polygon(surf, (255, 110, 30), [(x - 8, top), (x + 8, top), (x + 4, top + 6),
                                                           (x - 3, top + 10)])
                pygame.draw.line(surf, (230, 80, 20), (x, top + 4), (x - 10, top + 40))
            bg.wrap(volcano, vx)
    else:
        x = 0
        while x < LW:
            sw = rnd.randint(8, 18)
            sh = rnd.randint(12, 45)
            pygame.draw.polygon(surf, col, [(x, FLOOR_Y), (x + sw // 2, FLOOR_Y - sh), (x + sw, FLOOR_Y)])
            surf.set_at((x + sw // 2, FLOOR_Y - sh), (255, 120, 40))
            x += sw + rnd.randint(2, 14)


BIOME = dict(name="MAGMA DEPTHS", style="volcano", stars=False, ambient="embers", ground_style="lava",
    sky=((35, 6, 12), (150, 40, 20)), far=(95, 25, 28), near=(48, 14, 20),
    ground=(210, 60, 10), ground_top=(255, 200, 60), crystal=(255, 130, 50))

LEVEL = LevelDef(
    name="MAGMA DEPTHS", biome=BIOME, director=MagmaDirector, boss="leviathan",
    enemies=(("imp", 3, 0), ("fish", 2, 5), ("drone", 1, 15)),
    length=80, star=3600, tokens=55, music="magma", base_diff=0.6, hp_mult=3.4, boss_mult=2.5,
    blurb=("THE FLOOR IS LAVA. GEYSERS", "AND METEORS INCOMING!"), death="MELTED!",
)
