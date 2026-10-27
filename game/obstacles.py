"""Obstacle building blocks shared by every world.

An Obstacle is made of solid `Part`s (rects that block shots and hurt on contact,
optionally breakable) and/or non-solid hazards (via `hazard_hits`). Block looks
are data: worlds add their own materials with `register_block`.
"""
import math
import random
from dataclasses import dataclass

import pygame

from .settings import BLOCK_H, CRYSTAL_HP, FLOOR_Y, PILLAR_W, W
from .util import WHITE, shade

INF = 10 ** 9


# ====================================================================== block materials
@dataclass
class BlockKind:
    colors: object          # (main, light, dark) or fn(biome) -> (main, light, dark)
    hp: float = INF         # INF = unbreakable
    decor: object = None    # fn(surf, rect, part, light, dark, t) for extra detail


BLOCK_KINDS = {}


def register_block(name, colors, hp=INF, decor=None):
    BLOCK_KINDS[name] = BlockKind(colors, hp, decor)


def block_style(kind, biome):
    """(main, light, dark) colors for a block kind."""
    c = BLOCK_KINDS.get(kind, BLOCK_KINDS["metal"]).colors
    return c(biome) if callable(c) else c


def _metal_decor(surf, r, part, light, dark, t):
    if r.h > 4:
        for rx in (r.x + 3, r.right - 4):
            surf.set_at((rx, r.y + 2), light)
            surf.set_at((rx, r.bottom - 3), light)
    pygame.draw.line(surf, dark, (r.x, r.bottom - 1), (r.right - 1, r.bottom - 1))


def _crystal_decor(surf, r, part, light, dark, t):
    if r.h > 4:
        pygame.draw.line(surf, light, (r.x + 6, r.bottom - 2), (r.right - 3, r.y + 1))


def _rock_decor(surf, r, part, light, dark, t):
    surf.fill(dark, (r.x + 5, r.y + 3, 2, 2))
    surf.fill(dark, (r.right - 6, r.bottom - 4, 2, 2))


def _crystal_colors(biome):
    c = biome["crystal"]
    return c, shade(c, 1.35), shade(c, 0.45)


register_block("metal", ((105, 105, 130), (170, 170, 195), (40, 40, 58)), decor=_metal_decor)
register_block("crystal", _crystal_colors, hp=CRYSTAL_HP, decor=_crystal_decor)
register_block("rock", ((120, 85, 70), (165, 125, 100), (55, 35, 30)), hp=2, decor=_rock_decor)
register_block("emitter", ((255, 60, 60), (170, 170, 195), (40, 40, 58)), hp=2)


def draw_block(surf, part, biome, t=0.0):
    r = part.rect
    col, light, dark = block_style(part.kind, biome)
    surf.fill(dark, r)
    if r.h <= 2 or r.w <= 2:
        return
    surf.fill(WHITE if part.flash > 0 else col, r.inflate(-2, -2))
    surf.fill(light, (r.x + 2, r.y + 1, 2, r.h - 2))
    decor = BLOCK_KINDS.get(part.kind, BLOCK_KINDS["metal"]).decor
    if decor:
        decor(surf, r, part, light, dark, t)
    if part.breakable and part.hp < part.max_hp:
        pygame.draw.lines(surf, dark, False, [(r.x + 4, r.y + 1), (r.x + 8, r.y + r.h // 2), (r.x + 6, r.bottom - 1)])
        if part.hp <= 1:
            pygame.draw.line(surf, dark, (r.right - 5, r.y + 1), (r.right - 7, r.bottom - 1))


# ====================================================================== core types
class Part:
    __slots__ = ("x", "y", "w", "h", "hp", "max_hp", "alive", "flash", "kind")

    def __init__(self, x, y, w, h, hp=INF, kind="metal"):
        self.x, self.y, self.w, self.h = float(x), float(y), int(w), int(h)
        self.hp = self.max_hp = hp
        self.alive = True
        self.flash = 0.0
        self.kind = kind

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def breakable(self):
        return self.hp < INF


class Obstacle:
    solid = True       # parts block shots/bolts
    scores = False     # award points for flying past
    shard_chance = 0.45

    def __init__(self, x, w, biome):
        self.x = float(x)  # left edge; all parts lie within [x, x + w]
        self.w = w
        self.biome = biome
        self.parts = []
        self.passed = False
        self.dead = False
        self.t = 0.0

    def move(self, dx, dy=0.0):
        self.x += dx
        for p in self.parts:
            p.x += dx
            p.y += dy

    def tick(self, dt):
        self.t += dt
        for p in self.parts:
            if p.flash > 0:
                p.flash -= dt

    def update(self, dt, game):
        self.tick(dt)
        self.move(-game.scroll * dt)

    def special(self, dt, game):
        pass

    def offscreen(self):
        return self.dead or self.x + self.w < -14

    def hazard_hits(self, px, py, r):
        return False

    def colors(self, part):
        col, light, dark = block_style(part.kind, self.biome)
        return [col, light, WHITE]

    def on_break(self, part, game):
        pass

    def draw(self, surf, game):
        for p in self.parts:
            if p.alive:
                draw_block(surf, p, self.biome, game.time)


def rect_hit(rect, px, py, r):
    return rect.inflate(int(r * 2), int(r * 2)).collidepoint(px, py)


# ====================================================================== shared obstacles
class Pillar(Obstacle):
    """Column(s) of blocks with a gap. Either side may be absent (one-sided spire)."""
    scores = True
    GATE_ON, GATE_OFF, GATE_WARN = 1.0, 1.3, 0.45

    def __init__(self, x, gap_top, gap_bot, kind, biome, gate=False, w=PILLAR_W):
        super().__init__(x, w, biome)
        self.kind = kind
        self.gap_top, self.gap_bot = int(gap_top), int(gap_bot)
        hp = BLOCK_KINDS[kind].hp
        y = self.gap_top
        while y > 0:
            y0 = max(0, y - BLOCK_H)
            self.parts.append(Part(x, y0, w, y - y0, hp, kind))
            y = y0
        y = self.gap_bot
        while y < FLOOR_Y:
            y1 = min(FLOOR_Y, y + BLOCK_H)
            self.parts.append(Part(x, y, w, y1 - y, hp, kind))
            y = y1
        self.emitters = []
        if gate and self.gap_top > 0 and self.gap_bot < FLOOR_Y:
            self.gate_ph = random.uniform(0, 3)
            self.emitters = [Part(x + w / 2 - 5, self.gap_top, 10, 4, 2, "emitter"),
                             Part(x + w / 2 - 5, self.gap_bot - 4, 10, 4, 2, "emitter")]
            self.parts += self.emitters

    @property
    def gate_alive(self):
        return bool(self.emitters) and all(e.alive for e in self.emitters)

    @property
    def gate_state(self):
        if not self.gate_alive:
            return "off"
        ph = (self.t + self.gate_ph) % (self.GATE_ON + self.GATE_OFF)
        if ph < self.GATE_ON:
            return "on"
        if ph > self.GATE_ON + self.GATE_OFF - self.GATE_WARN:
            return "warn"
        return "off"

    def gate_rect(self):
        cx = int(self.x + self.w / 2)
        return pygame.Rect(cx - 2, self.gap_top + 4, 4, self.gap_bot - self.gap_top - 8)

    def hazard_hits(self, px, py, r):
        return self.gate_state == "on" and rect_hit(self.gate_rect(), px, py, r * 0.5)

    def colors(self, part):
        if part.kind == "emitter":
            return [(255, 60, 60), (170, 170, 195), WHITE]
        return super().colors(part)

    def on_break(self, part, game):
        if part.kind == "emitter":
            for e in self.emitters:
                if e.alive:
                    e.alive = False
                game.fx.explode(e.x + 5, e.y + 2, [(255, 60, 60), (170, 170, 195)])
            game.fx.text(self.x + self.w / 2, (self.gap_top + self.gap_bot) / 2, "GATE DOWN", (255, 120, 120))
            game.add_score(30)
            game.bump_combo()

    def draw(self, surf, game):
        t = game.time
        col, light, dark = block_style(self.kind, self.biome)
        for p in self.parts:
            if p.alive and p.kind != "emitter":
                draw_block(surf, p, self.biome, t)
        for p in self.parts:
            if not p.alive or p.kind == "emitter":
                continue
            if int(p.y + p.h) == self.gap_top:
                self._lip(surf, self.gap_top - 4, col, light, dark)
            elif int(p.y) == self.gap_bot:
                self._lip(surf, self.gap_bot, col, light, dark)
        if self.emitters and self.gate_alive:
            st = self.gate_state
            for e in self.emitters:
                surf.fill((40, 40, 58), e.rect)
                c = WHITE if e.flash > 0 else ((255, 60, 60) if st != "off" else (120, 40, 50))
                surf.fill(c, e.rect.inflate(-4, -2))
            br = self.gate_rect()
            if st == "on":
                w = 4 if int(t * 30) % 2 else 3
                surf.fill((150, 20, 40), (br.centerx - w // 2 - 1, br.y, w + 2, br.h))
                surf.fill((255, 60, 60), (br.centerx - w // 2, br.y, w, br.h))
                surf.fill(WHITE, (br.centerx, br.y, 1, br.h))
            elif st == "warn" and int(t * 20) % 2:
                for y in range(br.y, br.bottom, 3):
                    surf.set_at((br.centerx, y), (255, 80, 80))

    def _lip(self, surf, y, c, light, dark):
        r = pygame.Rect(int(self.x) - 2, y, self.w + 4, 4)
        surf.fill(dark, r)
        surf.fill(c, r.inflate(-2, -2))
        surf.fill(light, (r.x + 1, r.y + 1, r.w - 2, 1))
        if self.kind == "metal":
            for x in range(r.x + 1, r.right - 1, 4):
                surf.fill((255, 200, 40), (x, r.y + 1, 2, 2))


class Geyser(Obstacle):
    """Lava column that bubbles (warning), then erupts. Non-solid hazard."""
    solid = False

    def __init__(self, x, biome, hmax=90, w=12, warn=0.9, erupt=1.1, rest=1.8, once=False, delay=0.0):
        super().__init__(x, w, biome)
        self.hmax, self.warn, self.erupt, self.rest = hmax, warn, erupt, rest
        self.once = once
        self.delay = delay
        self.ph = 0.0 if once else random.uniform(0, warn + erupt + rest)
        self.h = 0.0
        self.state = "idle"

    def update(self, dt, game):
        super().update(dt, game)
        if self.once:
            tt = self.t - self.delay
            if tt < 0:
                self.state, te = "idle", 0
            elif tt < self.warn:
                self.state, te = "warn", 0
            elif tt < self.warn + self.erupt:
                self.state, te = "erupt", tt - self.warn
            else:
                self.state, te = "idle", 0
                self.dead = tt > self.warn + self.erupt + 0.4
        else:
            cyc = (self.t + self.ph) % (self.warn + self.erupt + self.rest)
            if cyc < self.rest:
                self.state, te = "idle", 0
            elif cyc < self.rest + self.warn:
                self.state, te = "warn", 0
            else:
                self.state, te = "erupt", cyc - self.rest - self.warn
        prev = self.h
        if self.state == "erupt":
            self.h = self.hmax * min(1.0, te / 0.15) * (1 + 0.05 * math.sin(self.t * 30))
            if prev < 1 and -20 < self.x < W:
                game.audio.play("beam", 0.4)
        else:
            self.h = max(0.0, self.h - 400 * dt)

    def hazard_hits(self, px, py, r):
        return self.h > 4 and rect_hit(pygame.Rect(int(self.x), int(FLOOR_Y - self.h), self.w, int(self.h)), px, py, r)

    def draw(self, surf, game):
        t = game.time
        x, w = int(self.x), self.w
        if self.state == "warn":
            k = 1 + int(t * 12) % 2
            pygame.draw.ellipse(surf, (255, 200, 60), (x - k, FLOOR_Y - 3 - k, w + 2 * k, 5 + k))
            if random.random() < 0.5:
                game.fx.burst(x + w / 2, FLOOR_Y - 2, [(255, 160, 40), (255, 230, 120)], n=1, speed=50,
                              life=0.4, grav=80, angle=-math.pi / 2, spread=0.8)
        if self.h > 1:
            top = int(FLOOR_Y - self.h)
            surf.fill((150, 30, 10), (x - 1, top, w + 2, int(self.h)))
            surf.fill((255, 110, 20), (x, top, w, int(self.h)))
            surf.fill((255, 220, 90), (x + w // 2 - 2, top + 2, 4, int(self.h) - 2))
            pygame.draw.circle(surf, (255, 160, 40), (x + w // 2, top), w // 2 + 2)
            pygame.draw.circle(surf, (255, 240, 160), (x + w // 2, top), w // 4 + 1)


class Meteor(Obstacle):
    """Telegraphed falling rock. Shootable."""

    def __init__(self, x, biome, vx=-35.0, vy=170.0, warn=0.9, size=8, kind="rock"):
        super().__init__(x, size, biome)
        self.vx, self.vy, self.warn, self.size = vx, vy, warn, size
        self.parts.append(Part(x, -size - 4, size, size, 2, kind))

    def update(self, dt, game):
        super().update(dt, game)
        p = self.parts[0]
        if not p.alive:
            self.dead = True
            return
        if self.warn > 0:
            self.warn -= dt
            return
        self.move(self.vx * dt, self.vy * dt)
        if random.random() < 0.7:
            c = (255, 140, 40) if p.kind == "rock" else self.biome["crystal"]
            game.fx.burst(p.x + self.size / 2, p.y, [c, (255, 230, 120)], n=1, speed=20, life=0.3, grav=-20)
        if p.y + p.h >= FLOOR_Y:
            game.fx.burst(p.x + 4, FLOOR_Y, [(255, 160, 40), (255, 230, 120)], n=10, speed=70, life=0.5,
                          grav=200, angle=-math.pi / 2, spread=2.0)
            game.audio.play("hit", 0.5)
            self.dead = True

    def draw(self, surf, game):
        p = self.parts[0]
        if self.warn > 0:
            if int(game.time * 10) % 2:
                x = int(p.x + self.size / 2)
                pygame.draw.polygon(surf, (255, 60, 60), [(x - 4, 2), (x + 4, 2), (x, 8)])
                for i in range(1, 12):
                    k = i * 0.06
                    surf.set_at((int(x + self.vx * k), int(10 + self.vy * k)), (255, 120, 120))
            return
        x, y = int(p.x + self.size / 2), int(p.y + self.size / 2)
        col, light, dark = block_style(p.kind, self.biome)
        pygame.draw.circle(surf, dark, (x, y), self.size // 2 + 1)
        pygame.draw.circle(surf, WHITE if p.flash > 0 else col, (x, y), self.size // 2)
        surf.set_at((x - 1, y - 1), light)
