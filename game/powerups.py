"""Collectible shards and power-up bubbles."""
import math
import random

import pygame

from .settings import FLOOR_Y, POWERS
from .sprites import draw_text


def random_power(hp, hp_cap):
    kinds = [k for k in POWERS if k != "heart" or hp < hp_cap]
    weights = [POWERS[k]["weight"] for k in kinds]
    return random.choices(kinds, weights)[0]


class Shard:
    def __init__(self, x, y, vx=0.0, vy=0.0, floating=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.floating = floating
        self.t = random.random()
        self.life = 14.0
        self.alive = True

    def update(self, dt, game):
        self.t += dt
        self.life -= dt
        p = game.player
        dx, dy = p.x - self.x, p.y - self.y
        d = math.hypot(dx, dy)
        reach = 90 if "magnet" in p.powers else p.magnet_r
        if p.alive and d < reach and d > 0.01:
            pull = 260 if "magnet" in p.powers else 120
            self.vx += dx / d * pull * dt * 4
            self.vy += dy / d * pull * dt * 4
            self.vx *= 0.9
            self.vy *= 0.9
        elif self.floating:
            self.vx, self.vy = -game.scroll, 0.0
        else:
            self.vx += (-game.scroll - self.vx) * min(1.0, dt * 2)
            self.vy = self.vy * 0.96 + 30 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > FLOOR_Y - 3:
            self.y = FLOOR_Y - 3
            self.vy = -abs(self.vy) * 0.5
        if self.x < -10 or self.life <= 0:
            self.alive = False

    def draw(self, surf, art):
        if self.life < 2 and int(self.life * 10) % 2:
            return
        bob = 1 if int(self.t * 6) % 2 else 0
        surf.blit(art.shard, (int(self.x) - 2, int(self.y) - 3 + bob))


class PowerItem:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.base_y, self.y = x, y, y
        self.t = random.random() * 6
        self.alive = True

    def update(self, dt, game):
        self.t += dt
        self.x -= game.scroll * dt
        self.y = self.base_y + math.sin(self.t * 3) * 4
        if self.x < -12:
            self.alive = False

    def draw(self, surf, art):
        info = POWERS[self.kind]
        x, y = int(self.x), int(self.y)
        col = info["color"]
        ring = (255, 255, 255) if int(self.t * 8) % 2 else col
        pygame.draw.circle(surf, (20, 16, 32), (x, y), 7)
        pygame.draw.circle(surf, ring, (x, y), 7, 1)
        if self.kind == "heart":
            surf.blit(art.heart, (x - 4, y - 4))
        else:
            draw_text(surf, info["letter"], x - 1, y - 2, col, shadow=None)
        if int(self.t * 4) % 3 == 0:
            a = self.t * 5
            surf.set_at((int(x + math.cos(a) * 9), int(y + math.sin(a) * 9)), (255, 255, 255))


