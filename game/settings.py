"""Tuning constants, palettes and content tables."""

W, H = 320, 180
SCALE = 4
FPS = 60

GROUND_H = 14
FLOOR_Y = H - GROUND_H
CEIL_Y = 5
PLAYER_X = 72.0

# Bird physics
GRAVITY = 560.0
FLAP_V = -172.0
MAX_FALL = 280.0

# World
BASE_SCROLL = 60.0
PILLAR_W = 18
PILLAR_SPACING = 140
BLOCK_H = 10
CRYSTAL_HP = 3

# Lasers
FIRE_COOLDOWN = 0.2
HEAT_PER_SHOT = 0.15
HEAT_COOL_RATE = 0.42
OVERHEAT_LOCK = 1.4
SHOT_SPEED = 320.0

# Reflect-dash
DASH_TIME = 0.22
DASH_COOLDOWN = 2.2
DASH_DIST = 44
REFLECT_RADIUS = 13
PERFECT_RADIUS = 28

# Health
MAX_HP = 3
HP_CAP = 5
INVULN_TIME = 1.3

# Combo
COMBO_TIMEOUT = 3.0
COMBO_PER_MULT = 4
MAX_MULT = 8

# Bosses
FIRST_BOSS = 1200
BOSS_STEP = 2200

PAL = {
    "K": (20, 16, 32),
    "W": (255, 255, 255),
    "Y": (255, 214, 64),
    "y": (200, 150, 30),
    "O": (255, 140, 40),
    "R": (220, 40, 60),
    "r": (130, 20, 40),
    "P": (255, 120, 180),
    "B": (60, 120, 255),
    "C": (80, 230, 255),
    "G": (80, 220, 100),
    "g": (30, 130, 60),
    "D": (70, 70, 95),
    "L": (170, 170, 195),
    "M": (200, 60, 255),
    "V": (110, 40, 170),
    "b": (140, 80, 40),
}

POWERS = {
    "spread": dict(dur=10.0, color=(255, 140, 40), letter="S", label="SPREAD SHOT", weight=3),
    "mega": dict(dur=5.0, color=(255, 60, 200), letter="M", label="MEGA BEAM", weight=1.5),
    "chill": dict(dur=9.0, color=(80, 230, 255), letter="C", label="CHILL: NO HEAT", weight=2),
    "magnet": dict(dur=12.0, color=(80, 220, 100), letter="G", label="SHARD MAGNET", weight=2),
    "tiny": dict(dur=10.0, color=(255, 214, 64), letter="T", label="TINY BIRD", weight=1.5),
    "shield": dict(dur=0, color=(140, 200, 255), letter="O", label="SHIELD BUBBLE", weight=2),
    "heart": dict(dur=0, color=(220, 40, 60), letter="+", label="EXTRA HEART", weight=1),
}

# Bird skins, unlocked by lifetime shards collected
SKINS = [
    dict(name="CLASSIC", cost=0, body=(255, 214, 64), dark=(200, 150, 30)),
    dict(name="RUBY", cost=300, body=(255, 90, 110), dark=(170, 30, 60)),
    dict(name="MINT", cost=1000, body=(110, 240, 170), dark=(40, 150, 100)),
    dict(name="VOID", cost=2500, body=(150, 110, 255), dark=(80, 50, 170)),
    dict(name="GOLDEN", cost=5000, body=(255, 245, 170), dark=(235, 175, 40)),
]
