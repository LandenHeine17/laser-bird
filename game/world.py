"""Parallax backgrounds and animated ground strips.

A biome dict describes colors and styles. Each world registers a painter for its
`style` with `@register_backdrop("style")`; the painter draws the far (idx 0) and
near (idx 1) parallax layers once. Built layers are cached per biome, so switching
levels or browsing level select doesn't rebuild them.
"""
import math
import random

import pygame

from .settings import FLOOR_Y, GROUND_H, H, W
from .util import lerp_color, shade

BACKDROPS = {}
_LAYER_CACHE = {}


def register_backdrop(style):
    def deco(fn):
        BACKDROPS[style] = fn
        return fn
    return deco


class _Layers:
    """The expensive, static part of a background (built once per biome)."""
    LW = W * 2  # layers are two screens wide and wrap seamlessly

    def __init__(self, biome):
        self.biome = biome
        self.sky = self._sky()
        self.far = self._layer(0)
        self.near = self._layer(1)
        self.ground = self._ground()
        rnd = random.Random(len(biome["name"]))
        self.stars = []
        if biome["stars"]:
            self.stars = [(rnd.randrange(W), rnd.randrange(FLOOR_Y - 20), rnd.random() * 6.28,
                           rnd.choice((1, 1, 1, 2))) for _ in range(55)]
        ambient = biome.get("ambient")
        count = {"embers": 40, "leaves": 30}.get(ambient, 0)
        self.ambient = [(rnd.randrange(W), rnd.randrange(H), rnd.uniform(10, 30), rnd.random() * 6.28)
                        for _ in range(count)]

    def wrap(self, fn, x):
        """Call fn at x and one layer-width either side, so shapes tile seamlessly."""
        for off in (-self.LW, 0, self.LW):
            fn(x + off)

    def _sky(self):
        s = pygame.Surface((W, H))
        top, bot = self.biome["sky"]
        bands = 10
        for y in range(H):
            tb = y / (H - 1) * bands
            base = int(tb)
            c0 = lerp_color(top, bot, base / bands)
            pygame.draw.line(s, c0, (0, y), (W, y))
            if tb - base > 0.5:  # retro checkerboard dither between bands
                c1 = lerp_color(top, bot, min(1.0, (base + 1) / bands))
                for x in range(y % 2, W, 2):
                    s.set_at((x, y), c1)
        return s

    def _layer(self, idx):
        b = self.biome
        surf = pygame.Surface((self.LW, H), pygame.SRCALPHA)
        col = b["far"] if idx == 0 else b["near"]
        rnd = random.Random(idx * 97 + len(b["name"]))
        BACKDROPS[b["style"]](self, surf, idx, col, shade(col, 1.25), rnd)
        return surf

    def _ground(self):
        b = self.biome
        LW = self.LW
        g = pygame.Surface((LW, GROUND_H))
        g.fill(b["ground"])
        style = b["ground_style"]
        if style == "planet":
            for y in range(GROUND_H):
                pygame.draw.line(g, lerp_color(b["ground_top"], b["ground"], y / GROUND_H), (0, y), (LW, y))
            return g
        g.fill(b["ground_top"], (0, 0, LW, 2))
        g.fill(shade(b["ground_top"], 0.6), (0, 2, LW, 1))
        dark = shade(b["ground"], 0.7)
        if style == "street":
            for x in range(0, LW, 16):
                g.fill((255, 214, 64), (x, 8, 8, 1))
        elif style == "moss":
            rnd = random.Random(9)
            for _ in range(60):
                g.fill((95, 90, 85), (rnd.randrange(LW), rnd.randrange(5, GROUND_H), 3, 2))
            for x in range(0, LW, 3):
                if rnd.random() < 0.5:
                    g.fill(b["ground_top"], (x, 0, 1, rnd.randint(2, 4)))
        elif style == "rock":
            rnd = random.Random(5)
            for _ in range(80):
                g.fill(dark, (rnd.randrange(LW), rnd.randrange(4, GROUND_H), 3, 2))
        else:
            for x in range(0, LW, 8):
                pygame.draw.line(g, dark, (x, 4), (x + 6, GROUND_H))
        return g


def layers_for(biome):
    L = _LAYER_CACHE.get(biome["name"])
    if L is None:
        L = _LAYER_CACHE[biome["name"]] = _Layers(biome)
    return L


class Background:
    LW = _Layers.LW

    def __init__(self, biome):
        self.biome = biome
        self.L = layers_for(biome)
        self.ox = [0.0, 0.0, 0.0]

    def update(self, dt, speed):
        for i, f in enumerate((0.15, 0.45, 1.0)):
            self.ox[i] = (self.ox[i] + speed * f * dt) % self.LW

    def draw_back(self, surf, t):
        L = self.L
        surf.blit(L.sky, (0, 0))
        for x, y, ph, s in L.stars:
            if math.sin(t * 3 + ph) > -0.3:
                c = 255 if math.sin(t * 5 + ph) > 0.6 else 170
                surf.fill((c, c, c), (x, y, s, s))
        for layer, ox in ((L.far, self.ox[0]), (L.near, self.ox[1])):
            surf.blit(layer, (-int(ox), 0))
            surf.blit(layer, (-int(ox) + self.LW, 0))
        ambient = self.biome.get("ambient")
        if ambient == "leaves":
            for x, y, sp, ph in L.ambient:
                ly = (y + t * sp) % H
                lx = (x + math.sin(t * 1.5 + ph) * 8 - t * sp * 0.8) % W
                c = (140, 210, 90) if math.sin(t * 3 + ph) > 0 else (90, 160, 60)
                surf.fill(c, (int(lx), int(ly), 2, 1))
        elif ambient == "embers":
            for x, y, sp, ph in L.ambient:
                ey = (y - t * sp) % H
                ex = (x + math.sin(t + ph) * 6 - self.ox[1] * 0.5) % W
                surf.set_at((int(ex), int(ey)), (255, 160, 60) if math.sin(t * 4 + ph) > 0 else (255, 90, 30))

    def draw_ground(self, surf, t=0.0):
        b = self.biome
        if b["ground_style"] == "lava":
            surf.fill(b["ground"], (0, FLOOR_Y, W, GROUND_H))
            for x in range(0, W, 2):
                wy = FLOOR_Y + int(math.sin(x * 0.08 + t * 3) * 1.5 + math.sin(x * 0.03 - t * 2))
                surf.fill(b["ground_top"], (x, wy, 2, 2))
                if (x + int(t * 20)) % 23 == 0:
                    surf.fill((255, 240, 160), (x, FLOOR_Y + 5 + (x // 2) % 6, 2, 1))
            surf.fill((150, 30, 10), (0, H - 3, W, 3))
            return
        ox = int(self.ox[2])
        surf.blit(self.L.ground, (-ox, FLOOR_Y))
        surf.blit(self.L.ground, (-ox + self.LW, FLOOR_Y))
