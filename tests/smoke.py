"""Headless smoke test: a bot plays through the menus, buys everything in the shop,
beats every level and boss (each with a different laser), the secret level, a stage
of Endless, then dies on purpose. Run:  python -m tests.smoke
"""
import random

import pygame

from tests import harness

from game import menus
from game.powerups import PowerItem
from game.progression import LASERS
from game.settings import POWERS
from game.worlds import LEVELS, MAIN_LEVELS


def run(game):
    """Drive the game with a bot: menus, shop, every level + boss (each with a different
    laser type), the secret level, endless mode and a death."""
    dt = 1 / 60
    frames = 0
    K = pygame

    def tick(n=1):
        nonlocal frames
        for _ in range(n):
            frames += 1
            game.step(dt)
            game.draw()
            game.present()

    def keys(*ks):
        for k in ks:
            game.on_key(k)
            tick(3)

    def bot():
        p = game.player
        ahead = [o for o in game.obstacles if o.x + o.w > p.x and getattr(o, "gap_top", None) is not None]
        target = (ahead[0].gap_top + ahead[0].gap_bot) / 2 if ahead else 85
        if hasattr(game.director, "c"):
            target = game.director.c
        if p.y > target + 4 and p.vy > -40:
            game.on_flap()
        if frames % 80 == 0:
            game.on_dash()

    def play_level(i):
        assert game.state == "play" and game.level_idx == i, (game.state, game.level_idx)
        game.god = True
        game.auto_fire = True
        game.on_flap()
        seen = set()
        for f in range(6000):
            if game.state != "play":
                break
            bot()
            if f == 120:
                for k in POWERS:
                    game.items.append(PowerItem(k, game.player.x + 4, game.player.y))
            if f == 900:
                game.stage_time = game.level.length
            b = game.boss
            if b and b.entered and f % 700 == 0:
                b.hp = min(b.hp, b.max_hp * 0.5) if b.phase == 1 else min(b.hp, 1)
            seen.update(type(o).__name__ for o in game.obstacles)
            seen.update(type(e).__name__ for e in game.enemies)
            if b:
                seen.add(type(b).__name__)
            tick()
        print(f"  {LEVELS[i].name:<14} laser={game.player.laser['key']:<8} state={game.state} "
              f"score={game.score} +{game.tokens_earned} tokens  saw={sorted(seen)}")
        assert game.state == "complete", game.state
        tick(80)

    # title -> menu -> shop (broke) -> skins -> how-to -> levels
    keys(K.K_SPACE, K.K_DOWN, K.K_DOWN, K.K_RETURN)
    assert game.state == "shop"
    keys(K.K_DOWN, K.K_RETURN, K.K_RIGHT, K.K_DOWN, K.K_RETURN, K.K_ESCAPE)
    assert game.data["tokens"] == 0 and game.state == "menu"
    keys(K.K_DOWN, K.K_RETURN, K.K_RIGHT, K.K_ESCAPE, K.K_DOWN, K.K_RETURN, K.K_ESCAPE)
    keys(K.K_UP, K.K_UP, K.K_UP, K.K_UP, K.K_RETURN, K.K_RIGHT, K.K_LEFT)
    assert game.state == "levels", game.state

    # rich now: buy every upgrade level and every laser through the shop UI
    game.data["tokens"] = 99999
    game.data["unlocked"] = MAIN_LEVELS
    keys(K.K_e)
    assert game.state == "shop"
    game.shop_tab = 0
    from game.progression import UPGRADES
    for row in range(len(UPGRADES)):
        game.shop_i = row
        keys(*([K.K_RETURN] * len(UPGRADES[row]["costs"])))
    keys(K.K_RIGHT)
    for row in range(len(LASERS)):
        game.shop_i = row
        keys(K.K_RETURN)
    keys(K.K_ESCAPE)
    assert game.state == "levels" and len(game.data["lasers"]) == len(LASERS)
    print(f"  shop OK: upgrades={game.data['upgrades']}")

    for i in range(MAIN_LEVELS):
        game.data["laser"] = LASERS[i % len(LASERS)]["key"]
        game.level_sel = i
        keys(K.K_RETURN)
        play_level(i)
        game.on_key(K.K_ESCAPE)
        assert game.state == "levels"

    # secret level via the hidden menu button (keyboard path), with the plasma laser
    game.data["laser"] = "plasma"
    game.on_key(K.K_ESCAPE)
    game.menu_i = len(menus.MENU)
    keys(K.K_RETURN)
    play_level(len(LEVELS) - 1)
    assert game.data["secret"]
    game.on_key(K.K_ESCAPE)

    # endless: run through a stage, then die
    game.on_key(K.K_ESCAPE)
    game.menu_i = 1
    game.on_key(K.K_RETURN)
    assert game.state == "play" and game.mode == "endless"
    game.god = True
    game.auto_fire = True
    game.on_flap()
    for f in range(4000):
        bot()
        if f == 300:
            game.stage_time = game.level.length
        if game.boss and game.boss.entered:
            game.boss.hp = min(game.boss.hp, 1)
        if game.level_idx == 1 and game.boss_state is None:
            break
        tick()
    assert game.level_idx == 1, game.level_idx
    keys(K.K_p, K.K_p)
    game.god = False
    game.auto_fire = False
    for _ in range(600):
        if game.state == "gameover":
            break
        game.player.vy = 200
        tick()
    assert game.state == "gameover", game.state
    tick(80)
    print(f"autotest: {frames} frames, endless score={game.score}")


def victory_and_revive(game):
    """Without god mode: after the boss's killing blow nothing can hurt you, and
    Second Wind saves you from one knockout."""
    from game.lasers import Bolt
    game.start_level(0)
    game.on_flap()
    game.god = game.auto_fire = False
    game.stage_time = game.level.length
    for _ in range(400):  # wait for the boss to arrive
        game.player.y, game.player.vy, game.player.invuln = 80, 0, 5
        game.step(1 / 60)
        if game.boss and game.boss.entered:
            break
    assert game.boss and game.boss.entered
    game.boss.take(10 ** 6, game)  # killing blow
    assert game.victory
    p = game.player
    p.invuln = 0
    for f in range(240):  # dive into the floor and get shot at: must survive
        p.y = 165
        game.bolts.append(Bolt(p.x, p.y, 0, 0))
        game.step(1 / 60)
        game.draw()
    assert p.alive and p.hp > 0, "player died after the boss was defeated"
    for _ in range(600):
        if game.state == "complete":
            break
        game.step(1 / 60)
    assert game.state == "complete", game.state
    print("  victory invincibility OK")

    game.data["upgrades"]["revive"] = 1
    game.start_level(0)
    game.on_flap()
    p = game.player
    assert p.revives == 1
    p.y = 170
    game.step(1 / 60)
    assert p.alive and p.hp == 1 and p.revives == 0, "second wind did not trigger"
    p.invuln = 0
    p.y = 170
    for _ in range(120):
        game.step(1 / 60)
    assert not p.alive, "second wind should only work once"
    print("  second wind OK")


if __name__ == "__main__":
    random.seed(1)
    g = harness.make_game()
    run(g)
    victory_and_revive(g)
    print("smoke test OK")
