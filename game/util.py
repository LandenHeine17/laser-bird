"""Small shared helpers: colors, geometry and cached overlay surfaces."""
import colorsys
import math

import pygame

INK = (20, 16, 32)  # the outline / shadow color used everywhere
WHITE = (255, 255, 255)


# ------------------------------------------------------------------ colors
def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rainbow(t, s=0.6):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(t % 1.0, s, 1.0))


# ------------------------------------------------------------------ math
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_diff(a, b):
    """Signed smallest difference between two angles, in (-pi, pi]."""
    return (a - b + math.pi) % math.tau - math.pi


def seg_dist(px, py, x0, y0, x1, y1):
    """Distance from point (px, py) to the segment (x0, y0)-(x1, y1)."""
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def aim(x0, y0, x1, y1, speed):
    """Velocity of `speed` pointing from (x0, y0) toward (x1, y1)."""
    a = math.atan2(y1 - y0, x1 - x0)
    return math.cos(a) * speed, math.sin(a) * speed


def lob(x0, y0, x1, y1, t, grav):
    """Launch velocity for a projectile under `grav` to reach (x1, y1) after t seconds."""
    return (x1 - x0) / t, (y1 - y0) / t - 0.5 * grav * t


# ------------------------------------------------------------------ surfaces
_overlays = {}


def overlay(size, color, alpha):
    """A cached solid, semi-transparent surface (screen dims, flashes, card shades)."""
    key = (size, color, alpha)
    s = _overlays.get(key)
    if s is None:
        if len(_overlays) > 64:
            _overlays.clear()
        s = pygame.Surface(size)
        s.fill(color)
        s.set_alpha(alpha)
        _overlays[key] = s
    return s
