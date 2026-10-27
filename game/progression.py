"""Shop upgrades, laser types and how they turn into player stats.

The game is meant to be grindy: the bird starts weak, every run pays tokens, and
upgrades go up to 10 levels with costs that grow ~45% per level. Each upgrade has
an `effect(level)` that returns the stat it controls, used both to apply it and to
preview "now -> next" in the shop.
"""
from .settings import DASH_COOLDOWN, FIRE_COOLDOWN, MAX_HP, REFLECT_RADIUS


def _costs(base, n, growth=1.45):
    return [int(round(base * growth ** i / 5) * 5) for i in range(n)]


def _pct(v):
    return f"{int(round(v * 100))}%"


UPGRADES = [
    dict(key="damage", name="DAMAGE", desc="HIT HARDER WITH EVERY LASER", costs=_costs(25, 10),
         effect=lambda lv: 1.0 + 0.3 * lv, show=lambda v: f"{v:.1f}X DMG"),
    dict(key="rate", name="FIRE RATE", desc="SHORTER TIME BETWEEN SHOTS", costs=_costs(20, 10),
         effect=lambda lv: 1.0 - 0.05 * lv, show=lambda v: f"{FIRE_COOLDOWN * v:.2f}S"),
    dict(key="cooling", name="COOLING", desc="LESS HEAT PER SHOT, FASTER COOLDOWN", costs=_costs(20, 10),
         effect=lambda lv: 1.0 - 0.065 * lv, show=lambda v: f"{_pct(v)} HEAT"),
    dict(key="dash", name="DASH CORE", desc="SHORTER DASH COOLDOWN, WIDER REFLECT", costs=_costs(20, 10),
         effect=lambda lv: 1.0 - 0.06 * lv, show=lambda v: f"{DASH_COOLDOWN * v:.1f}S"),
    dict(key="hearts", name="EXTRA HEART", desc="+1 MAX HEART", costs=[90, 260, 600],
         effect=lambda lv: MAX_HP + lv, show=lambda v: f"{v} HEARTS"),
    dict(key="tokens", name="TOKEN BOOST", desc="EARN MORE TOKENS FROM EVERY RUN", costs=_costs(40, 8, 1.55),
         effect=lambda lv: 1.0 + 0.12 * lv, show=lambda v: f"{v:.2f}X TOKENS"),
    dict(key="magnet", name="SHARD MAGNET", desc="PULL SHARDS IN FROM FARTHER AWAY", costs=_costs(15, 5),
         effect=lambda lv: 18 + 12 * lv, show=lambda v: f"{v}PX REACH"),
    dict(key="luck", name="LUCKY DROPS", desc="ENEMIES DROP POWER-UPS MORE OFTEN", costs=_costs(30, 5),
         effect=lambda lv: 0.08 + 0.03 * lv, show=lambda v: f"{_pct(v)} DROP"),
    dict(key="power", name="POWER TIME", desc="POWER-UPS LAST LONGER", costs=_costs(30, 5),
         effect=lambda lv: 1.0 + 0.15 * lv, show=lambda v: f"{v:.2f}X TIME"),
    dict(key="combo", name="COMBO KEEPER", desc="MORE TIME BEFORE YOUR COMBO DROPS", costs=_costs(25, 4),
         effect=lambda lv: 3.0 + 0.6 * lv, show=lambda v: f"{v:.1f}S"),
    dict(key="shield", name="START SHIELD", desc="BEGIN EVERY LEVEL WITH A SHIELD", costs=[350],
         effect=lambda lv: lv > 0, show=lambda v: "ON" if v else "OFF"),
    dict(key="revive", name="SECOND WIND", desc="SURVIVE ONE KNOCKOUT PER RUN", costs=[900],
         effect=lambda lv: lv, show=lambda v: f"{v} REVIVE"),
]
UPGRADE_BY_KEY = {u["key"]: u for u in UPGRADES}

LASERS = [
    dict(key="standard", name="STANDARD", desc="RELIABLE SINGLE BEAM", cost=0, heat=1.0, cd=1.0,
         color=(255, 255, 120)),
    dict(key="twin", name="TWIN", desc="TWO PARALLEL BEAMS", cost=150, heat=1.2, cd=1.0, color=(120, 255, 160)),
    dict(key="pierce", name="PIERCER", desc="PASSES THROUGH UP TO 3 ENEMIES", cost=320, heat=1.3, cd=1.1,
         color=(80, 230, 255)),
    dict(key="homing", name="SEEKER", desc="CURVES TOWARD THE NEAREST TARGET", cost=500, heat=1.2, cd=1.1,
         color=(255, 120, 255)),
    dict(key="scatter", name="SCATTER", desc="5 SHORT-RANGE PELLETS, BIG BURST", cost=750, heat=1.6, cd=1.7,
         color=(255, 170, 60)),
    dict(key="plasma", name="PLASMA", desc="SLOW ORB WITH HUGE SPLASH DAMAGE", cost=1100, heat=2.2, cd=2.3,
         color=(200, 120, 255)),
]
LASER_BY_KEY = {L["key"]: L for L in LASERS}


def level_of(data, key):
    lvl = data.get("upgrades", {}).get(key, 0)
    return min(lvl, len(UPGRADE_BY_KEY[key]["costs"]))


def next_cost(data, up):
    lvl = level_of(data, up["key"])
    return up["costs"][lvl] if lvl < len(up["costs"]) else None


def stat(data, key, lvl=None):
    up = UPGRADE_BY_KEY[key]
    return up["effect"](level_of(data, key) if lvl is None else lvl)


def preview(data, up):
    """'NOW -> NEXT' text for the shop."""
    lvl = level_of(data, up["key"])
    now = up["show"](up["effect"](lvl))
    if lvl >= len(up["costs"]):
        return now
    return f"{now} > {up['show'](up['effect'](lvl + 1))}"


def bird_rank(data):
    """Total upgrade levels bought: a simple measure of progression."""
    return sum(level_of(data, u["key"]) for u in UPGRADES)


def apply_stats(player, data):
    """Copy upgrade levels onto a freshly made Bird."""
    st = lambda k: stat(data, k)
    cool = st("cooling")
    player.heat_mult = cool
    player.cool_mult = 1.0 + (1.0 - cool) * 1.2
    player.rate_mult = st("rate")
    player.dmg = st("damage")
    player.dash_cd_max = DASH_COOLDOWN * st("dash")
    player.reflect_r = REFLECT_RADIUS + level_of(data, "dash")
    player.max_hp = st("hearts")
    player.hp = player.max_hp
    player.magnet_r = st("magnet")
    player.token_mult = st("tokens")
    player.luck = st("luck")
    player.power_mult = st("power")
    player.combo_time = st("combo")
    player.shield = st("shield")
    player.revives = st("revive")
    player.laser = LASER_BY_KEY.get(data.get("laser", "standard"), LASERS[0])


# ------------------------------------------------------------------ purchases
def buy_upgrade(data, up):
    """Try to buy the next level of an upgrade. Returns (message, sound)."""
    cost = next_cost(data, up)
    if cost is None:
        return "MAXED OUT!", "clank"
    if data["tokens"] < cost:
        return "NOT ENOUGH TOKENS", "clank"
    data["tokens"] -= cost
    data["upgrades"][up["key"]] = level_of(data, up["key"]) + 1
    return f"{up['name']} UPGRADED!", "powerup"


def buy_or_equip_laser(data, laser):
    """Equip an owned laser, or buy and equip it. Returns (message, sound)."""
    owned = data["lasers"]
    if laser["key"] in owned:
        data["laser"] = laser["key"]
        return f"{laser['name']} EQUIPPED", "select"
    if data["tokens"] < laser["cost"]:
        return "NOT ENOUGH TOKENS", "clank"
    data["tokens"] -= laser["cost"]
    owned.append(laser["key"])
    data["laser"] = laser["key"]
    return f"{laser['name']} BOUGHT + EQUIPPED!", "powerup"
