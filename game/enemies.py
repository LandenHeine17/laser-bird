"""Enemy base class and the common enemies that appear in several worlds.

World-specific enemies live in their world module. Register spawnable enemies with
`@register_enemy("key")` so level definitions can name them.
"""
import math
import random

import pygame

from .lasers import Beam, Bolt, PlayerShot
from .registry import register_enemy
from .settings import FLOOR_Y, W
from .sprites import draw_text
from .util import aim


class Enemy:
    hp = 1
    score = 20
    w, h = 10, 8
    rammable = True
    shards = 1
    colors = [(255, 140, 40)]

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.t = 0.0
        self.alive = True
        self.flash = 0.0

    @classmethod
    def spawn(cls, game, y):
        game.enemies.append(cls(W + 12, y, game))

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def take(self, dmg, game, shot=None):
        if shot is not None and self.deflect(shot, game):
            return "reflect"
        self.hp -= dmg / game.hp_mult  # later levels have tougher mobs
        self.flash = 0.08
        if self.hp <= 0:
            self.alive = False
            return "kill"
        return "hit"

    def deflect(self, shot, game):
        return False

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)

    def offscreen(self):
        return self.x < -30 or self.y < -40 or self.y > 220

    def blit(self, surf, game, img):
        if self.flash > 0:
            img = game.art.white(img)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - img.get_height() / 2)))

    def draw(self, surf, game):
        pass

    def can_shoot(self, game, margin=24):
        p = game.player
        return p.alive and 0 < self.x < W - 6 and self.x > p.x + margin


@register_enemy("drone")
class Drone(Enemy):
    hp = 2
    score = 25
    colors = [(170, 170, 195), (220, 40, 60)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.base_y = y
        self.cool = random.uniform(0.8, 1.6)
        self.hover_x = random.uniform(190, 290)

    def update(self, dt, game):
        super().update(dt, game)
        if self.x > self.hover_x:
            self.x -= (game.scroll + 50) * dt
        else:
            self.x -= game.scroll * 0.35 * dt
        self.y = self.base_y + math.sin(self.t * 2.5) * 8
        self.cool -= dt
        p = game.player
        if self.cool <= 0:
            self.cool = random.uniform(1.4, 2.4) / (1 + 0.4 * game.diff)
            if self.can_shoot(game):
                spd = 85 + 25 * min(game.diff, 2)
                vx, vy = aim(self.x - 5, self.y, p.x, p.y, spd)
                game.bolts.append(Bolt(self.x - 5, self.y, vx, vy))
                game.audio.play("eshot", 0.6)

    def draw(self, surf, game):
        self.blit(surf, game, game.art.drone[int(self.t * 14) % 2])
        if 0 < self.cool < 0.25 and int(self.t * 30) % 2:
            surf.fill((255, 255, 255), (int(self.x) - 3, int(self.y), 2, 1))


@register_enemy("swooper")
class Swooper(Enemy):
    hp = 1
    score = 20
    w, h = 11, 6
    colors = [(220, 40, 60), (255, 140, 40)]

    def __init__(self, x, y, game, delay=0.0):
        super().__init__(x, y)
        self.speed = game.scroll + 85 + 20 * min(game.diff, 2)
        self.warn = 0.7 + delay

    @classmethod
    def spawn(cls, game, y):
        n = 1 if random.random() > 0.25 + 0.2 * game.diff else random.randint(2, 3)
        for i in range(n):
            yy = max(20, min(FLOOR_Y - 20, y + (i - n // 2) * 22))
            game.enemies.append(cls(W + 30, yy, game, delay=i * 0.25))

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
                draw_text(surf, "!", W - 6, int(self.y) - 2, (255, 60, 60))
            return
        self.blit(surf, game, game.art.swooper[int(self.t * 12) % 2])


@register_enemy("bat")
class MirrorBat(Enemy):
    """Its mirror bounces your lasers back at you. Hit it while the mirror is down,
    or ram it with a dash, or send a reflected bolt through it."""
    hp = 3
    score = 40
    w, h = 11, 7
    shards = 2
    colors = [(110, 40, 170), (200, 60, 255)]

    def __init__(self, x, y, game):
        super().__init__(x, y)
        self.base_y = y
        self.off = random.uniform(0, 2.7)
        self.amp = 16

    @property
    def mirror(self):
        return (self.t + self.off) % 2.7 < 1.6

    def deflect(self, shot, game):
        if isinstance(shot, PlayerShot) and self.mirror and shot.vx > 0:
            p = game.player
            vx, vy = aim(self.x - 8, shot.y, p.x, p.y, 150)
            game.bolts.append(Bolt(self.x - 8, shot.y, vx, vy, color=(255, 255, 255)))
            game.audio.play("reflect", 0.6)
            game.fx.burst(self.x - 8, shot.y, [(80, 230, 255), (255, 255, 255)], n=5, speed=50, life=0.25)
            return True
        return False

    def update(self, dt, game):
        super().update(dt, game)
        self.x -= (game.scroll * 0.5 + 18) * dt
        self.y = self.base_y + math.sin(self.t * 2) * self.amp

    def draw(self, surf, game):
        self.blit(surf, game, game.art.bat[int(self.t * 8) % 2])
        if self.mirror:
            mx = int(self.x) - 8
            for i, y in enumerate(range(int(self.y) - 6, int(self.y) + 7)):
                glint = (i + int(self.t * 20)) % 13 == 0
                surf.set_at((mx, y), (255, 255, 255) if glint else (80, 230, 255))
                surf.set_at((mx - 1, y), (40, 120, 160))


class Turret(Enemy):
    """Mounted on the left face of an obstacle (`anchor.x` is its left edge)."""
    hp = 4
    score = 50
    w, h = 9, 6
    rammable = False
    shards = 2
    colors = [(170, 170, 195), (200, 60, 255)]

    def __init__(self, anchor, y, game, ax=None):
        self.anchor = anchor
        self.ax = ax
        super().__init__(self._ax() - 4, y)
        self.cool = random.uniform(0.6, 1.4)
        self.aim_a = math.pi
        self.beam = None

    def _ax(self):
        return getattr(self.anchor, self.ax) if self.ax else self.anchor.x

    def muzzle(self):
        return self.x + math.cos(self.aim_a) * 7, self.y + math.sin(self.aim_a) * 7

    def update(self, dt, game):
        super().update(dt, game)
        self.x = self._ax() - 4
        p = game.player
        if self.beam is None or self.beam.dead:
            self.beam = None
            dx = min(p.x - self.x, -10)
            target = math.atan2(p.y - self.y, dx)
            self.aim_a += (target - self.aim_a) * min(1.0, dt * 4)
            self.cool -= dt
            if self.cool <= 0 and 30 < self.x < W - 8 and self.x > p.x + 30 and p.alive:
                self.cool = random.uniform(2.2, 3.2) / (1 + 0.3 * game.diff)
                self.beam = Beam(self.muzzle, self.aim_a, warn=0.75, fire=0.3, width=4,
                                 color=(255, 60, 60), owner=self)
                game.beams.append(self.beam)
                game.audio.play("charge", 0.7)

    def offscreen(self):
        return self.x < -20

    def draw(self, surf, game):
        mx, my = self.muzzle()
        pygame.draw.line(surf, (40, 40, 58), (int(self.x), int(self.y)), (int(mx), int(my)), 4)
        pygame.draw.line(surf, (170, 170, 195), (int(self.x), int(self.y)), (int(mx), int(my)), 2)
        self.blit(surf, game, game.art.turret)
