"""Particles, floating text, screen shake, hit-stop, slow-mo and flashes."""
import math
import random

import pygame

from .sprites import draw_text
from .util import overlay

MAX_PARTICLES = 700


class FX:
    def __init__(self):
        self.parts = []
        self.rings = []
        self.texts = []
        self.shake = 0.0
        self.hitstop = 0.0
        self.slow = 0.0
        self.flash = 0.0
        self.flash_max = 1.0
        self.flash_col = (255, 255, 255)

    def clear(self):
        self.parts.clear()
        self.rings.clear()
        self.texts.clear()
        self.shake = self.hitstop = self.slow = self.flash = 0.0

    # ---------------------------------------------------------- spawners
    def burst(self, x, y, colors, n=10, speed=70, life=0.5, size=1, grav=60, angle=0.0, spread=math.tau):
        for _ in range(n):
            if len(self.parts) >= MAX_PARTICLES:
                break
            a = angle + random.uniform(-spread / 2, spread / 2)
            sp = random.uniform(0.25, 1.0) * speed
            lf = life * random.uniform(0.6, 1.25)
            sz = size if isinstance(size, int) else random.choice(size)
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp, lf, lf,
                               random.choice(colors), sz, grav])

    def explode(self, x, y, colors, big=False):
        self.burst(x, y, colors + [(255, 255, 255)], n=50 if big else 20, speed=150 if big else 90,
                   life=0.9 if big else 0.55, size=(1, 1, 2, 3) if big else (1, 1, 2), grav=40)
        self.burst(x, y, [(255, 220, 120), (255, 140, 40)], n=12 if big else 6, speed=40, life=0.4,
                   size=(2, 3), grav=-30)
        self.ring(x, y, 34 if big else 16, colors[0])

    def ring(self, x, y, maxr, color, life=0.3):
        self.rings.append([x, y, maxr, life, life, color])

    def text(self, x, y, s, color, scale=1, life=0.9):
        self.texts.append([x, y, s, color, scale, life, life])

    def add_shake(self, a):
        self.shake = min(9.0, max(self.shake, a))

    def stop(self, t):
        self.hitstop = max(self.hitstop, t)

    def slowmo(self, t):
        self.slow = max(self.slow, t)

    def do_flash(self, t, color=(255, 255, 255)):
        self.flash = self.flash_max = t
        self.flash_col = color

    # ---------------------------------------------------------- update
    def update(self, dt):
        keep = []
        for p in self.parts:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[2] *= 0.985
            keep.append(p)
        self.parts = keep
        for r in self.rings:
            r[3] -= dt
        self.rings = [r for r in self.rings if r[3] > 0]
        for t in self.texts:
            t[5] -= dt
            t[1] -= 18 * dt * (t[5] / t[6])
        self.texts = [t for t in self.texts if t[5] > 0]

    def tick_real(self, dt):
        self.shake = max(0.0, self.shake - 28 * dt)
        self.slow = max(0.0, self.slow - dt)
        self.flash = max(0.0, self.flash - dt)

    def offset(self):
        if self.shake < 0.5:
            return 0, 0
        s = int(self.shake + 0.5)
        return random.randint(-s, s), random.randint(-s, s)

    # ---------------------------------------------------------- draw
    def draw(self, surf):
        for p in self.parts:
            col = p[6]
            if p[4] < p[5] * 0.3:
                col = tuple(c // 2 for c in col)
            if p[7] <= 1:
                surf.set_at((int(p[0]), int(p[1])), col)
            else:
                s = p[7] if p[4] > p[5] * 0.5 else max(1, p[7] - 1)
                surf.fill(col, (int(p[0]) - s // 2, int(p[1]) - s // 2, s, s))
        for x, y, maxr, life, mx, col in self.rings:
            r = int(maxr * (1 - life / mx)) + 1
            pygame.draw.circle(surf, col, (int(x), int(y)), r, 1)

    def draw_texts(self, surf):
        for x, y, s, col, scale, life, mx in self.texts:
            if life < 0.25 and int(life * 30) % 2:
                continue
            draw_text(surf, s, x, y, col, scale, align="center")

    def draw_flash(self, surf):
        if self.flash > 0:
            alpha = int(200 * self.flash / self.flash_max) // 8 * 8  # quantized so overlays cache well
            surf.blit(overlay(surf.get_size(), self.flash_col, alpha), (0, 0))
