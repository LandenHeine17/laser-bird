"""Player shots, enemy bolts (reflectable) and telegraphed beams."""
import math
import random

import pygame

from .settings import FLOOR_Y, H, W
from .sprites import draw_text
from .util import angle_diff, seg_dist, shade

SAFE_COL = (90, 255, 120)








class PlayerShot:
    def __init__(self, x, y, vx, vy, dmg=1, color=(255, 255, 120), kind="standard", pierce=0,
                 homing=False, life=None, r=1, splash=0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg = dmg
        self.color = color
        self.kind = kind
        self.pierce = pierce
        self.homing = homing
        self.life = life
        self.r = r
        self.splash = splash
        self.hit = set()
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.life is not None:
            self.life -= dt
            if self.life <= 0:
                self.alive = False
        if self.x > W + 10 or self.x < -10 or self.y < -10 or self.y > H + 10:
            self.alive = False

    def steer(self, tx, ty, dt, rate=6.0):
        a = math.atan2(self.vy, self.vx)
        want = math.atan2(ty - self.y, tx - self.x)
        a += max(-rate * dt, min(rate * dt, angle_diff(want, a)))
        spd = math.hypot(self.vx, self.vy)
        self.vx, self.vy = math.cos(a) * spd, math.sin(a) * spd

    def draw(self, surf):
        head = (int(self.x), int(self.y))
        if self.kind == "plasma":
            pygame.draw.circle(surf, shade(self.color, 0.6), head, self.r + 1)
            pygame.draw.circle(surf, self.color, head, self.r)
            pygame.draw.circle(surf, (255, 255, 255), head, max(1, self.r - 2))
            return
        tail = (int(self.x - self.vx * 0.02), int(self.y - self.vy * 0.02))
        pygame.draw.line(surf, shade(self.color, 0.6), tail, head, 3)
        pygame.draw.line(surf, (255, 255, 255), tail, head, 1)


class Bolt:
    """Enemy projectile. Dash into it to reflect it back as a friendly shot."""

    def __init__(self, x, y, vx, vy, color=(255, 70, 200), r=2, grav=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color = color
        self.r = r
        self.grav = grav
        self.hostile = True
        self.alive = True
        self.close = False
        self.awarded = False
        self.last_d = 999.0
        self.t = 0.0

    def reflect(self, target=None):
        self.hostile = False
        self.grav = 0.0
        self.color = (80, 230, 255)
        spd = 270.0
        a = math.atan2(target[1] - self.y, target[0] - self.x) if target is not None else 0.0
        self.vx, self.vy = math.cos(a) * spd, math.sin(a) * spd

    def update(self, dt):
        self.t += dt
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -12 or self.x > W + 24 or self.y < -60 or self.y > H + 12:
            self.alive = False
        elif self.grav and self.y > FLOOR_Y:
            self.alive = False

    def draw(self, surf):
        c = (int(self.x), int(self.y))
        tail = (int(self.x - self.vx * 0.03), int(self.y - self.vy * 0.03))
        pygame.draw.line(surf, shade(self.color, 0.5), tail, c, 2)
        pulse = 1 if int(self.t * 16) % 2 else 0
        pygame.draw.circle(surf, self.color, c, self.r + 1 + pulse)
        pygame.draw.circle(surf, (255, 255, 255), c, max(1, self.r - 1))


class Beam:
    """A laser that telegraphs (warn) then fires. Optionally sweeps.

    Sweeping beams get a `safe` window (center angle, half-width): while the beam
    is inside it, it switches off. The window is drawn in green during the warning.
    """

    def __init__(self, origin, angle, warn=0.7, fire=0.4, width=5, color=(255, 60, 60),
                 sweep=0.0, owner=None, length=460, safe=None):
        self.origin = origin
        self.angle = angle
        self.warn = warn
        self.fire = fire
        self.width = width
        self.color = color
        self.sweep = sweep
        self.owner = owner
        self.length = length
        self.safe = safe
        self.t = 0.0
        self.state = "warn"
        self.dead = False
        self.just_fired = False
        self.phased = False

    def pos(self):
        return self.origin() if callable(self.origin) else self.origin

    def endpoints(self, angle=None):
        a = self.angle if angle is None else angle
        x0, y0 = self.pos()
        return (x0, y0), (x0 + math.cos(a) * self.length, y0 + math.sin(a) * self.length)

    @property
    def in_safe(self):
        return self.safe is not None and abs(angle_diff(self.angle, self.safe[0])) < self.safe[1]

    @property
    def active(self):
        return self.state == "fire" and not self.in_safe

    def update(self, dt):
        self.t += dt
        self.just_fired = False
        if self.state == "warn" and self.t >= self.warn:
            self.state = "fire"
            self.t = 0.0
            self.just_fired = True
        elif self.state == "fire":
            self.angle += self.sweep * dt
            if self.t >= self.fire:
                self.dead = True
        if self.owner is not None and not getattr(self.owner, "alive", True):
            self.dead = True
        if self.owner is not None and getattr(self.owner, "dying", 0) > 0:
            self.dead = True

    def hits(self, px, py, r):
        if not self.active:
            return False
        (x0, y0), (x1, y1) = self.endpoints()
        return seg_dist(px, py, x0, y0, x1, y1) < self.width / 2 + r

    def _dotted(self, surf, a, color, step=4):
        (x0, y0), (x1, y1) = self.endpoints(a)
        n = int(self.length / step)
        for i in range(0, n, 2):
            f = i / n
            surf.set_at((int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f)), color)

    def draw_safe(self, surf, t):
        if self.safe is None:
            return
        c, h = self.safe
        if int(t * 8) % 2:
            self._dotted(surf, c - h, SAFE_COL)
            self._dotted(surf, c + h, SAFE_COL)
        # label the safe band where it reaches the left side of the screen
        x0, y0 = self.pos()
        ca = math.cos(c)
        if ca < -0.2:
            L = (14 - x0) / ca
            y = y0 + math.sin(c) * L
            if 8 < y < FLOOR_Y - 8:
                draw_text(surf, "SAFE", 4, int(y) - 2, SAFE_COL)

    def draw(self, surf, t):
        p0, p1 = self.endpoints()
        p0i = (int(p0[0]), int(p0[1]))
        p1i = (int(p1[0]), int(p1[1]))
        if self.state == "warn":
            k = self.t / self.warn
            if int(self.t * (14 + 20 * k)) % 2 == 0:
                pygame.draw.line(surf, self.color, p0i, p1i, 1 if k < 0.7 else 2)
            if self.sweep:
                _, e = self.endpoints(self.angle + self.sweep * self.fire)
                if int(self.t * 14) % 2:
                    pygame.draw.line(surf, shade(self.color, 0.5), p0i, (int(e[0]), int(e[1])), 1)
            self.draw_safe(surf, t)
            pygame.draw.circle(surf, (255, 255, 255), p0i, 1 + int(k * self.width * 0.6))
        elif self.in_safe:
            self._dotted(surf, self.angle, SAFE_COL, 6)
            pygame.draw.circle(surf, SAFE_COL, p0i, 3)
        else:
            w = self.width + (1 if int(t * 40) % 2 else 0)
            pygame.draw.line(surf, shade(self.color, 0.55), p0i, p1i, w + 4)
            pygame.draw.line(surf, self.color, p0i, p1i, w)
            pygame.draw.line(surf, (255, 255, 255), p0i, p1i, max(1, w // 3))
            pygame.draw.circle(surf, (255, 255, 255), p0i, w // 2 + 2)
            if self.safe is not None:
                self.draw_safe(surf, t)


def sweep_beams(owner, origin, n=1, color=(255, 60, 200), width=5, fire=1.7, warn=1.0, player_x=72.0):
    """Create sweeping beam(s) that always leave a safe band at the player's column."""
    gx, gy = origin()
    D = max(40.0, gx - player_x)
    safe_y = random.uniform(28, FLOOR_Y - 30)
    delta = math.atan2(gy - safe_y, D)  # angle above the horizontal-left direction
    safe_c = math.pi + delta
    span = max(0.85, abs(delta) + 0.35)
    half = 0.17
    dirs = [random.choice((-1, 1))] if n == 1 else [1, -1]
    beams = []
    for d in dirs:
        start = math.pi - span * d
        rate = 2 * span / fire * d
        beams.append(Beam(origin, start, warn=warn, fire=fire, width=width, color=color, sweep=rate,
                          owner=owner, safe=(safe_c, half)))
    return beams
