"""Menu screens: title, main menu, level select, shop, skins, how-to, pause and results.

Each screen has a key handler and a draw function, looked up by game state in
KEY_HANDLERS / SCREENS. Add a screen by writing both and registering them.
"""
import math

import pygame

from . import save
from .progression import LASERS, UPGRADES, bird_rank, buy_or_equip_laser, buy_upgrade, level_of, next_cost, preview
from .registry import BOSSES
from .settings import H, SKINS, W
from .sprites import draw_text, text_width
from .util import INK as K, WHITE, overlay, rainbow
from .world import Background
from .worlds import LEVELS, MAIN_LEVELS

GOLD = (255, 214, 64)
DIM = (170, 170, 200)
CYAN = (80, 230, 255)
GREEN = (90, 255, 120)
LEAF = (130, 230, 100)

UP = (pygame.K_UP, pygame.K_w)
DOWN = (pygame.K_DOWN, pygame.K_s)
LEFT = (pygame.K_LEFT, pygame.K_a)
RIGHT = (pygame.K_RIGHT, pygame.K_d)
OK = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j)
BACK = (pygame.K_ESCAPE, pygame.K_BACKSPACE)

MENU = [("ADVENTURE", "adventure"), ("ENDLESS", "endless"), ("SHOP", "shop"), ("SKINS", "skins"),
        ("HOW TO PLAY", "howto"), ("QUIT", "quit")]
SECRET = MAIN_LEVELS  # index of the hidden level (the first one after the main campaign)
SHOP_ROWS = 6        # visible rows in the scrolling shop list

HOWTO = [
    ("FLAP", "SPACE / W / UP / LEFT CLICK"),
    ("LASER", "HOLD J / F / X / RIGHT CLICK - WATCH YOUR HEAT BAR"),
    ("DASH", "K / SHIFT / S - INVINCIBLE FOR A MOMENT"),
    ("", ""),
    ("REFLECT", "DASH INTO ENEMY BOLTS TO FIRE THEM BACK"),
    ("PERFECT", "DASH JUST BEFORE A BOLT HITS FOR SLOW-MO"),
    ("PHASE", "DASH THROUGH A FIRING BEAM FOR BONUS POINTS"),
    ("RAM", "DASH INTO SMALL ENEMIES AND CRYSTAL TO SMASH"),
    ("", ""),
    ("COMBO", "KILLS, PASSES, CLOSE CALLS AND PICKUPS BUILD X8"),
    ("SAFE", "SWEEPING BOSS LASERS SKIP THE GREEN SAFE ZONE"),
    ("SHARDS", "TURN INTO TOKENS FOR THE SHOP + UNLOCK SKINS"),
    ("SHOP", "UPGRADE AFTER EVERY RUN - LATER WORLDS NEED IT!"),
]


# ====================================================================== shared helpers
def nav(game, k, attr, n, keys_prev=UP, keys_next=DOWN):
    """Move a cursor attribute with wraparound. Returns True if the key was a nav key."""
    if k in keys_prev or k in keys_next:
        setattr(game, attr, (getattr(game, attr) + (-1 if k in keys_prev else 1)) % n)
        game.audio.play("select", 0.6)
        return True
    return False


def n_cards(game):
    return len(LEVELS) if game.data["secret"] else MAIN_LEVELS


def level_open(game, i):
    if LEVELS[i].secret:
        return game.data["secret"]
    return i < game.data["unlocked"]


def back_target(game):
    return "levels" if game.mode == "adventure" else "menu"


def open_secret(game):
    first = not game.data["secret"]
    game.data["secret"] = True
    save.save(game.data)
    game.audio.play("perfect")
    game.level_sel = SECRET
    game.start_level(SECRET, "adventure")
    L = LEVELS[SECRET]
    game.show_banner("SECRET LEVEL", f"{L.name} - FIND YOUR ZEN" if first else L.name, 3.0)


def open_shop(game, back):
    game.shop_return = back
    game.shop_i = game.shop_scroll = 0
    if game.state in ("gameover", "complete"):
        game.to_menu(back)
    game.set_state("shop")
    game.audio.play("select")


def shop_rows(game):
    return UPGRADES if game.shop_tab == 0 else LASERS


def thumbs(game):
    if game.thumbs is None:
        game.thumbs = []
        s = pygame.Surface((W, H))
        for L in LEVELS:
            bg = Background(L.biome)
            bg.draw_back(s, 1.0)
            bg.draw_ground(s, 1.0)
            game.thumbs.append(pygame.transform.scale(s, (44, 26)))
    return game.thumbs


_scaled = {}


def scaled(img, k):
    """Integer-scaled copy of a sprite, cached."""
    key = (id(img), k)
    s = _scaled.get(key)
    if s is None:
        s = _scaled[key] = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
    return s


def dim(c, a=150):
    c.blit(overlay((W, H), (10, 6, 20), a), (0, 0))


# ====================================================================== key handlers
def key_title(game, k):
    if k in OK or k in UP:
        game.set_state("menu")
        game.audio.play("select")
    elif k in BACK:
        game.quit()


def key_menu(game, k):
    if nav(game, k, "menu_i", len(MENU) + 1):  # +1: the hidden button below QUIT
        return
    if k in BACK:
        game.set_state("title")
        return
    if k not in OK:
        return
    if game.menu_i == len(MENU):
        open_secret(game)
        return
    item = MENU[game.menu_i][1]
    game.audio.play("select")
    if item == "adventure":
        game.set_state("levels")
        game.set_level(game.level_sel)
    elif item == "endless":
        game.start_level(0, "endless")
    elif item == "shop":
        open_shop(game, "menu")
    elif item == "skins":
        game.skin_sel = game.skin
        game.set_state("skins")
    elif item == "howto":
        game.set_state("howto")
    else:
        game.quit()


def key_levels(game, k):
    if nav(game, k, "level_sel", n_cards(game), LEFT, RIGHT):
        game.set_level(game.level_sel)
    elif k in (pygame.K_TAB, pygame.K_e):
        open_shop(game, "levels")
    elif k in OK:
        if level_open(game, game.level_sel):
            game.start_level(game.level_sel, "adventure")
        else:
            game.audio.play("clank")
    elif k in BACK:
        game.set_level(0)
        game.set_state("menu")


def key_shop(game, k):
    if k in LEFT or k in RIGHT or k == pygame.K_TAB:
        game.shop_tab = 1 - game.shop_tab
        game.shop_i = game.shop_scroll = 0
        game.audio.play("select", 0.6)
    elif nav(game, k, "shop_i", len(shop_rows(game))):
        pass
    elif k in OK:
        row = shop_rows(game)[game.shop_i]
        buy = buy_upgrade if game.shop_tab == 0 else buy_or_equip_laser
        msg, sound = buy(game.data, row)
        game.shop_msg = (msg, game.time + 1.2)
        game.audio.play(sound)
        save.save(game.data)
        game.reset_run()  # re-apply upgrades to the player
    elif k in BACK:
        game.set_state(game.shop_return)


def key_skins(game, k):
    if nav(game, k, "skin_sel", len(SKINS), LEFT, RIGHT):
        return
    if k in OK:
        if game.skin_unlocked(game.skin_sel):
            game.skin = game.player.skin = game.data["skin"] = game.skin_sel
            save.save(game.data)
            game.audio.play("powerup")
        else:
            game.audio.play("clank")
    elif k in BACK:
        game.set_state("menu")


def key_howto(game, k):
    if k in OK or k in BACK:
        game.set_state("menu")


def key_pause(game, k):
    if k in (pygame.K_p, pygame.K_ESCAPE, pygame.K_SPACE):
        game.set_state("play")
    elif k == pygame.K_r:
        game.restart()
    elif k == pygame.K_q:
        game.to_menu(back_target(game))


def key_gameover(game, k):
    if game.state_t < 0.9:  # don't let a panicked flap skip the results
        return
    if k in OK or k in UP or k == pygame.K_r:
        game.restart()
    elif k == pygame.K_e:
        open_shop(game, back_target(game))
    elif k in BACK:
        game.to_menu(back_target(game))


def key_complete(game, k):
    if game.state_t < 1.2:
        return
    if k == pygame.K_e:
        open_shop(game, "levels")
    elif k in OK:
        nxt = game.level_idx + 1
        if nxt < MAIN_LEVELS:
            game.level_sel = nxt
            game.start_level(nxt, "adventure")
        else:
            game.to_menu("levels")
    elif k == pygame.K_r:
        game.restart()
    elif k in BACK:
        game.level_sel = game.level_idx
        game.to_menu("levels")


KEY_HANDLERS = {
    "title": key_title, "menu": key_menu, "levels": key_levels, "shop": key_shop, "skins": key_skins,
    "howto": key_howto, "pause": key_pause, "gameover": key_gameover, "complete": key_complete,
}


def on_key(game, k):
    handler = KEY_HANDLERS.get(game.state)
    if handler:
        handler(game, k)


# ====================================================================== drawing: menu screens
def draw_logo(c, game, y=22, scale=4):
    t = game.time
    x0 = W // 2 - text_width("LASER BIRD", scale) // 2
    for i, ch in enumerate("LASER BIRD"):
        draw_text(c, ch, x0 + i * 4 * scale, y + int(math.sin(t * 4 + i * 0.5) * 2), rainbow(t * 0.5 + i * 0.07),
                  scale=scale)
    lw = int((math.sin(t * 2) * 0.5 + 0.5) * 150) + 10
    ly = y + 5 * scale + 4
    c.fill((255, 60, 60), (W // 2 - lw // 2, ly, lw, 2))
    c.fill(WHITE, (W // 2 - lw // 2, ly, lw, 1))


def draw_bird(c, game, x, y, scale=2, skin=None):
    up, down = game.art.bird[game.skin if skin is None else skin]
    img = scaled(up if int(game.time * 8) % 2 else down, scale)
    c.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))


def draw_title(c, game):
    t = game.time
    for sh in game.title_shots:
        sh.draw(c)
    draw_bird(c, game, 100, 112 + math.sin(t * 3) * 5)
    draw_logo(c, game)
    draw_text(c, "A FLAPPY LASER SHOOTER", W // 2, 56, GOLD, align="center")
    if int(t * 2) % 2:
        draw_text(c, "PRESS SPACE", 210, 108, WHITE, scale=2, align="center")
    draw_text(c, "F11: FULLSCREEN   M: MUTE", W // 2, 150, (230, 230, 255), align="center")


def draw_main_menu(c, game):
    t = game.time
    d = game.data
    dim(c, 90)
    draw_logo(c, game, y=12, scale=3)
    for i, (label, _) in enumerate(MENU):
        y = 46 + i * 17
        sel = i == game.menu_i
        draw_text(c, label, W // 2, y, rainbow(t + i * 0.1) if sel else DIM, scale=2, align="center")
        if sel:
            draw_bird(c, game, W // 2 - text_width(label, 2) // 2 - 14, y + 5, scale=1)
    key = MENU[game.menu_i][1] if game.menu_i < len(MENU) else ""
    sub = {"adventure": f"{sum(d['stars'])} STARS",
           "endless": f"BEST {d['high']}   BOSSES {d['best_tier']}",
           "shop": f"{d['tokens']} TOKENS TO SPEND",
           "skins": f"{d['shards']} LIFETIME SHARDS"}.get(key, "")
    draw_text(c, sub, W // 2, 152, GOLD, align="center")
    draw_text(c, f"TOKENS {d['tokens']}", W - 4, 4, CYAN, align="right")
    # the secret button: a tiny bamboo leaf in the bottom-left corner
    sel = game.menu_i == len(MENU)
    bx, by = 7, H - 7
    col = LEAF if sel or int(t * 1.5) % 4 == 0 else (70, 110, 60)
    for i in range(-3, 4):
        c.set_at((bx + i, by - i // 2), col)
        if abs(i) < 2:
            c.set_at((bx + i, by - i // 2 - 1), col)
    if sel:
        pygame.draw.circle(c, LEAF, (bx, by), 6, 1)
        draw_text(c, "???", bx + 9, by - 2, LEAF)


def draw_howto(c, game):
    dim(c, 190)
    draw_text(c, "HOW TO PLAY", W // 2, 8, GOLD, scale=2, align="center")
    for i, (a, b) in enumerate(HOWTO):
        y = 28 + i * 10
        draw_text(c, a, 70, y, CYAN, align="right")
        draw_text(c, b, 78, y, WHITE)
    draw_text(c, "ESC: BACK", W // 2, 158, DIM, align="center")


def draw_levels(c, game):
    t = game.time
    d = game.data
    dim(c, 120)
    draw_text(c, "SELECT LEVEL", W // 2, 8, GOLD, scale=2, align="center")
    th = thumbs(game)
    n = n_cards(game)
    cw, gap = (58, 4) if n <= 5 else (50, 3)
    x0 = (W - (cw * n + gap * (n - 1))) // 2
    for i in range(n):
        L = LEVELS[i]
        sel = i == game.level_sel
        x = x0 + i * (cw + gap)
        y = 30 - (3 if sel else 0)
        r = pygame.Rect(x, y, cw, 92)
        c.fill(K, r.inflate(2, 2))
        c.fill((30, 60, 35) if L.secret else ((60, 40, 90) if sel else (40, 30, 60)), r)
        if sel:
            pygame.draw.rect(c, rainbow(t), r.inflate(2, 2), 1)
        c.blit(th[i], (x + (cw - th[i].get_width()) // 2, y + 3))
        draw_text(c, "*" if L.secret else str(i + 1), x + 5, y + 5, LEAF if L.secret else WHITE)
        locked = not level_open(game, i)
        for j, part in enumerate(L.name.split(" ")):
            draw_text(c, part, x + cw // 2, y + 33 + j * 7, DIM if locked else WHITE, align="center")
        if locked:
            c.blit(overlay((cw, 92), (0, 0, 0), 130), (x, y))
            c.blit(scaled(game.art.lock, 2), (x + cw // 2 - 7, y + 8))
            continue
        for st in range(3):
            c.blit(game.art.star if st < d["stars"][i] else game.art.star_empty, (x + cw // 2 - 19 + st * 14, y + 52))
        draw_text(c, "BEST", x + cw // 2, y + 63, DIM, align="center")
        draw_text(c, str(d["best"][i]), x + cw // 2, y + 70, GOLD, align="center")
        boss = BOSSES[L.boss].name.replace("THE ", "")
        draw_text(c, boss.split(" ")[-1], x + cw // 2, y + 80, (255, 120, 180), align="center")
    L = LEVELS[game.level_sel]
    if level_open(game, game.level_sel):
        for j, line in enumerate(L.blurb):
            draw_text(c, line, W // 2, 132 + j * 8, WHITE, align="center")
        draw_text(c, f"BOSS: {BOSSES[L.boss].name}", W // 2, 151, (255, 120, 180), align="center")
    else:
        draw_text(c, "BEAT THE PREVIOUS LEVEL TO UNLOCK", W // 2, 136, DIM, align="center")
    draw_text(c, f"TOKENS {d['tokens']}", W - 4, 4, CYAN, align="right")
    draw_text(c, "< > CHOOSE   ENTER: PLAY   E: SHOP   ESC: BACK", W // 2, 170, GOLD, align="center")


def draw_shop(c, game):
    t = game.time
    d = game.data
    dim(c, 200)
    draw_text(c, "SHOP", W // 2, 6, GOLD, scale=2, align="center")
    draw_text(c, f"TOKENS: {d['tokens']}", W - 6, 6, CYAN, align="right")
    draw_text(c, f"BIRD RANK {bird_rank(d)}", 6, 6, GREEN)
    for i, tab in enumerate(("UPGRADES", "LASERS")):
        x = W // 2 - 50 + i * 100
        if i == game.shop_tab:
            c.fill((70, 40, 110), (x - 34, 22, 68, 10))
        draw_text(c, tab, x, 24, WHITE if i == game.shop_tab else DIM, align="center")
    rows = shop_rows(game)
    # keep the selected row inside the visible window
    game.shop_scroll = max(min(game.shop_scroll, game.shop_i), game.shop_i - SHOP_ROWS + 1)
    game.shop_scroll = max(0, min(game.shop_scroll, len(rows) - SHOP_ROWS))
    for vi, row in enumerate(rows[game.shop_scroll:game.shop_scroll + SHOP_ROWS]):
        i = game.shop_scroll + vi
        y = 40 + vi * 18
        sel = i == game.shop_i
        if sel:
            c.fill((50, 30, 80), (14, y - 3, W - 28, 17))
            pygame.draw.rect(c, rainbow(t), (14, y - 3, W - 28, 17), 1)
        draw_text(c, row["name"], 20, y, WHITE if sel else (210, 210, 235))
        draw_text(c, row["desc"], 20, y + 7, DIM)
        if game.shop_tab == 0:
            draw_text(c, preview(d, row), 82, y, CYAN if sel else (120, 170, 200))
            lvl, n = level_of(d, row["key"]), len(row["costs"])
            for k in range(n):
                c.fill(GOLD if k < lvl else (60, 50, 80), (216 + k * 5, y + 1, 4, 4))
            cost = next_cost(d, row)
            label = "MAX" if cost is None else str(cost)
            col = GREEN if cost is None else (GOLD if d["tokens"] >= cost else (255, 90, 90))
        else:
            if d["laser"] == row["key"]:
                label, col = "EQUIPPED", GREEN
            elif row["key"] in d["lasers"]:
                label, col = "OWNED", WHITE
            else:
                label, col = str(row["cost"]), GOLD if d["tokens"] >= row["cost"] else (255, 90, 90)
            c.fill(row["color"], (178, y + 1, 10, 3))
        draw_text(c, label, W - 20, y + 3, col, align="right")
    if game.shop_scroll > 0:
        pygame.draw.polygon(c, GOLD, [(W - 10, 38), (W - 7, 34), (W - 4, 38)])
    if game.shop_scroll + SHOP_ROWS < len(rows):
        pygame.draw.polygon(c, GOLD, [(W - 10, 144), (W - 7, 148), (W - 4, 144)])
    msg, until = game.shop_msg
    if msg and until > game.time:
        draw_text(c, msg, W // 2, 152, rainbow(t * 2), align="center")
    draw_text(c, "UP/DOWN: PICK  ENTER: BUY  < >: TAB  ESC: BACK", W // 2, 166, GOLD, align="center")


def draw_skins(c, game):
    t = game.time
    dim(c, 140)
    draw_text(c, "BIRD SKINS", W // 2, 10, GOLD, scale=2, align="center")
    draw_text(c, f"YOU HAVE {game.data['shards']} SHARDS", W // 2, 28, CYAN, align="center")
    for i, sk in enumerate(SKINS):
        x, y = 40 + i * 60, 72
        sel = i == game.skin_sel
        unlocked = game.skin_unlocked(i)
        if sel:
            pygame.draw.rect(c, rainbow(t), (x - 26, y - 26, 52, 70), 1)
        if unlocked:
            draw_bird(c, game, x, y + (math.sin(t * 4) * 3 if sel else 0), 3 if sel else 2, skin=i)
        else:
            img = scaled(game.art.tint(game.art.bird[i][1], (60, 60, 80)), 2)
            c.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
            c.blit(game.art.lock, (x - 3, y - 4))
        draw_text(c, sk["name"], x, y + 22, sk["body"] if unlocked else DIM, align="center")
        if i == game.skin:
            draw_text(c, "EQUIPPED", x, y + 31, GREEN, align="center")
        elif not unlocked:
            draw_text(c, str(sk["cost"]), x, y + 31, DIM, align="center")
    draw_text(c, "< > CHOOSE   ENTER: EQUIP   ESC: BACK", W // 2, 160, GOLD, align="center")


SCREENS = {"title": draw_title, "menu": draw_main_menu, "levels": draw_levels, "shop": draw_shop,
           "skins": draw_skins, "howto": draw_howto}


def draw_menu_state(c, game):
    game.bg.draw_back(c, game.time)
    game.bg.draw_ground(c, game.time)
    SCREENS[game.state](c, game)


# ====================================================================== drawing: in-play overlays
def draw_ready(c, game):
    if int(game.time * 2.5) % 2:
        draw_text(c, "PRESS SPACE TO FLAP", W // 2, 112, WHITE, align="center")
    draw_text(c, "J: LASER   K: DASH   (DASH INTO BOLTS TO REFLECT!)", W // 2, 124, GOLD, align="center")


def draw_banner(c, game):
    if not game.banner:
        return
    title, sub, left = game.banner
    if title == "WARNING!":
        if int(left * 6) % 2:
            c.fill((150, 0, 30), (0, 50, W, 26))
            draw_text(c, title, W // 2, 54, WHITE, scale=3, align="center")
        draw_text(c, sub, W // 2, 80, (255, 120, 120), align="center")
        return
    draw_text(c, title, W // 2, 52, WHITE, scale=3, align="center")
    if sub:
        draw_text(c, sub, W // 2, 72, GOLD, align="center")


def draw_pause(c, game):
    dim(c)
    draw_text(c, "PAUSED", W // 2, 56, WHITE, scale=3, align="center")
    draw_text(c, "P: RESUME   R: RESTART   Q: QUIT   M: MUTE", W // 2, 86, GOLD, align="center")


def draw_stats(c, game, y0):
    rows = [("KILLS", game.kills), ("REFLECTS", game.reflects), ("BEST COMBO", f"X{game.best_mult}"),
            ("CLOSE CALLS", game.near_misses), ("SHARDS", game.shard_count)]
    for i, (k, v) in enumerate(rows):
        draw_text(c, k, W // 2 - 4, y0 + i * 8, (180, 180, 210), align="right")
        draw_text(c, str(v), W // 2 + 4, y0 + i * 8, WHITE)


def draw_unlocks(c, game, y):
    for name in game.unlocks:
        draw_text(c, f"NEW SKIN UNLOCKED: {name}!", W // 2, y, rainbow(game.time * 2), align="center")
        y += 8
    return y


def draw_gameover(c, game):
    t = game.time
    d = game.data
    dim(c, min(170, int(game.state_t * 300)))
    draw_text(c, "GAME OVER", W // 2, 14, (255, 80, 80), scale=3, align="center")
    draw_text(c, game.death_msg, W // 2, 34, (255, 160, 120), align="center")
    draw_text(c, str(game.score), W // 2, 46, WHITE, scale=2, align="center")
    best = d["high"] if game.mode == "endless" else d["best"][game.level_idx]
    if game.new_best and int(t * 4) % 2:
        draw_text(c, "NEW BEST!", W // 2, 62, GOLD, align="center")
    else:
        draw_text(c, f"BEST {best}", W // 2, 62, (200, 200, 220), align="center")
    if game.mode == "adventure":
        draw_text(c, f"{game.level.name} - {int(game.progress * 100)}%", W // 2, 72, DIM, align="center")
    else:
        draw_text(c, f"BOSSES BEATEN: {game.bosses}", W // 2, 72, DIM, align="center")
    draw_stats(c, game, 84)
    y = draw_unlocks(c, game, 128)
    draw_text(c, f"+{game.tokens_earned} TOKENS  (YOU HAVE {d['tokens']})", W // 2, y + 2, CYAN, align="center")
    if game.state_t > 0.9 and int(t * 2.5) % 2:
        draw_text(c, "SPACE: RETRY   E: SHOP   ESC: MENU", W // 2, 160, GOLD, align="center")


def draw_complete(c, game):
    t = game.time
    st = game.state_t
    dim(c, min(170, int(st * 300)))
    last = game.level_idx >= MAIN_LEVELS - 1
    draw_text(c, "LEVEL CLEAR!", W // 2, 10, rainbow(t), scale=3, align="center")
    for s in range(3):  # stars pop in one at a time
        appear = st > 0.4 + s * 0.3
        img = game.art.star if appear and s < game.result.get("stars", 1) else game.art.star_empty
        img = scaled(img, 3 if appear else 2)
        c.blit(img, (W // 2 - 32 + s * 24 - img.get_width() // 2 + 8, 34 - img.get_height() // 2 + 8))
    draw_text(c, str(game.score), W // 2, 56, WHITE, scale=2, align="center")
    sub = "NEW BEST!" if game.new_best else f"BEST {game.data['best'][game.level_idx]}"
    draw_text(c, sub, W // 2, 72, GOLD, align="center")
    if game.result.get("flawless"):
        draw_text(c, "FLAWLESS - NO HITS TAKEN!", W // 2, 80, GREEN, align="center")
    draw_stats(c, game, 90)
    first = "  (FIRST CLEAR BONUS!)" if game.result.get("first") else ""
    draw_text(c, f"+{game.tokens_earned} TOKENS{first}", W // 2, 131, CYAN, align="center")
    y = draw_unlocks(c, game, 139)
    if game.result.get("unlocked"):
        draw_text(c, f"UNLOCKED: {game.result['unlocked']}", W // 2, y, CYAN, align="center")
    if last:
        msg = ("THE GROVE IS AT PEACE. THE PANDAS BOW TO YOU" if game.level.secret
               else "YOU CONQUERED THE COSMOS! TRY ENDLESS MODE")
        draw_text(c, msg, W // 2, 151, rainbow(t * 2), align="center")
    if st > 1.2 and int(t * 2.5) % 2:
        msg = "ENTER: LEVELS  R: RETRY  E: SHOP" if last else "ENTER: NEXT  R: RETRY  E: SHOP  ESC: LEVELS"
        draw_text(c, msg, W // 2, 162, GOLD, align="center")
