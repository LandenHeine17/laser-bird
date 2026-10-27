"""Laser firing patterns. Each laser type (see progression.LASERS) maps to a function
that returns the shots for one trigger pull. Add a new laser by writing a pattern
and adding a row to LASERS."""
import math
import random

from .lasers import PlayerShot
from .settings import SHOT_SPEED

PATTERNS = {}


def pattern(key):
    def deco(fn):
        PATTERNS[key] = fn
        return fn
    return deco


def _shot(x, y, a, speed=SHOT_SPEED, **kw):
    return PlayerShot(x, y, math.cos(a) * speed, math.sin(a) * speed, **kw)


@pattern("standard")
def standard(x, y, a, dmg, col):
    return [_shot(x, y, a, dmg=dmg, color=col, kind="standard")]


@pattern("twin")
def twin(x, y, a, dmg, col):
    return [_shot(x, y + dy, a, dmg=dmg * 0.75, color=col, kind="twin") for dy in (-3, 3)]


@pattern("pierce")
def pierce(x, y, a, dmg, col):
    return [_shot(x, y, a, dmg=dmg, color=col, kind="pierce", pierce=3)]


@pattern("homing")
def homing(x, y, a, dmg, col):
    return [_shot(x, y, a, dmg=dmg, color=col, kind="homing", homing=True)]


@pattern("scatter")
def scatter(x, y, a, dmg, col):
    return [_shot(x, y, a + (i - 2) * 0.16 + random.uniform(-0.04, 0.04), dmg=dmg * 0.7, color=col,
                  kind="scatter", life=0.38) for i in range(5)]


@pattern("plasma")
def plasma(x, y, a, dmg, col):
    return [_shot(x, y, a, speed=200, dmg=dmg * 3, color=col, kind="plasma", r=3, splash=20)]


def fire(laser, x, y, dmg, spread=False):
    """All shots for one trigger pull; the Spread power-up fans any laser into three."""
    fn = PATTERNS[laser["key"]]
    shots = []
    for a in ((-0.2, 0.0, 0.2) if spread else (0.0,)):
        shots += fn(x, y, a, dmg, laser["color"])
    return shots
