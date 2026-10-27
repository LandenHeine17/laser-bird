"""Heads-up display."""
import pygame

from .settings import H, POWERS, W
from .sprites import draw_text
from .util import INK as K, rainbow


def bar(surf, x, y, w, h, frac, col, back=(50, 40, 70)):
    surf.fill(K, (x - 1, y - 1, w + 2, h + 2))
    surf.fill(back, (x, y, w, h))
    surf.fill(col, (x, y, int(w * max(0.0, min(1.0, frac))), h))


def draw(surf, g):
    p = g.player
    t = g.time
    art = g.art
    # hearts
    slots = max(p.max_hp, p.hp)
    for i in range(slots):
        surf.blit(art.heart if i < p.hp else art.heart_empty, (3 + i * 9, 3))
    if p.shield:
        cx = 3 + slots * 9 + 5
        pygame.draw.circle(surf, (140, 200, 255), (cx, 7), 4, 1)

    # heat
    if p.overheat > 0:
        hc = (255, 255, 255) if int(t * 10) % 2 else (255, 40, 40)
    elif p.heat > 0.75:
        hc = (255, 60, 60)
    elif p.heat > 0.45:
        hc = (255, 200, 60)
    else:
        hc = (80, 220, 100)
    if "chill" in p.powers:
        hc = (80, 230, 255)
    bar(surf, 4, 14, 36, 3, p.heat, hc)
    draw_text(surf, "HOT!" if p.overheat > 0 else "HEAT", 44, 13, hc)

    # dash
    ready = p.dash_cd <= 0
    dc = (80, 230, 255) if ready else (60, 90, 120)
    bar(surf, 4, 21, 36, 2, 1 - p.dash_cd / p.dash_cd_max, dc)
    draw_text(surf, "DASH", 44, 20, dc if not ready or int(t * 3) % 3 else (255, 255, 255))

    # score + multiplier
    draw_text(surf, str(g.score), W // 2, 3, (255, 255, 255), scale=2, align="center")
    m = g.mult
    if m > 1:
        draw_text(surf, f"X{m}", W // 2, 16, rainbow(t * 2), align="center")
    if g.combo > 0:
        bar(surf, W // 2 - 12, 23, 24, 1, g.combo_t / p.combo_time, (255, 214, 64))

    # active powers
    x = W - 4
    for k, left in sorted(p.powers.items()):
        info = POWERS[k]
        x -= 11
        surf.fill(K, (x - 1, 3, 11, 11))
        surf.fill(info["color"], (x, 4, 9, 9))
        draw_text(surf, info["letter"], x + 3, 6, K, shadow=None)
        bar(surf, x, 15, 9, 1, left / (info["dur"] * p.power_mult), info["color"])

    # boss
    b = g.boss
    if b is not None and b.dying <= 0:
        frac = b.hp / b.max_hp
        bar(surf, 100, H - 8, W - 140, 3, frac, rainbow(t) if b.phase == 3 else (255, 60, 200))
        draw_text(surf, b.name, 95, H - 9, (255, 120, 180), align="right")

    # level progress toward the boss
    if g.boss_state is None and not g.ready:
        x0, x1, y = 70, W - 70, H - 8
        bar(surf, x0, y, x1 - x0, 2, g.progress, (255, 214, 64))
        icon = art.small(art.bird[g.skin][1], 0.6)
        surf.blit(icon, (x0 + int((x1 - x0) * g.progress) - icon.get_width() // 2, y - 4))
        draw_text(surf, "BOSS", x1 + 5, y - 2, (255, 120, 180))
        label = g.level.name if g.mode == "adventure" else f"STAGE {g.bosses + 1}"
        draw_text(surf, label, x0 - 5, y - 2, (230, 230, 255), align="right")
