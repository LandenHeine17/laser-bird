"""A play session: level setup, scoring, player actions, boss flow and rewards
(mixed into Game). Entities talk to the game through the methods defined here and
in combat.py, e.g. `game.add_score`, `game.bump_combo`, `game.add_obstacle`."""
import math
import random

from . import save, weapons
from .player import Bird
from .powerups import PowerItem, Shard, random_power
from .progression import apply_stats
from .registry import BOSSES
from .settings import (BASE_SCROLL, CEIL_Y, COMBO_PER_MULT, FIRE_COOLDOWN, FLAP_V, FLOOR_Y,
                       GRAVITY, H, HEAT_PER_SHOT, HP_CAP, MAX_MULT, OVERHEAT_LOCK, PERFECT_RADIUS, POWERS, SKINS, W)
from .util import WHITE, rainbow
from .world import Background
from .worlds import LEVELS, MAIN_LEVELS

CYAN = (80, 230, 255)


class RunMixin:
    # ------------------------------------------------------------------ setup
    def set_level(self, i):
        self.level_idx = i
        self.level = LEVELS[i]
        self.biome = self.level.biome
        self.bg = Background(self.biome)

    @property
    def hp_mult(self):
        """Enemy toughness: later worlds and Endless loops take more hits."""
        return self.level.hp_mult * (1 + 0.5 * self.tier)

    @property
    def boss_mult(self):
        return self.level.boss_mult * (1 + 0.4 * self.tier)

    @property
    def hp_cap(self):
        return min(HP_CAP + 2, self.player.max_hp + 2)

    @property
    def mult(self):
        return 1 + min(MAX_MULT - 1, self.combo // COMBO_PER_MULT)

    @property
    def progress(self):
        return min(1.0, self.stage_time / self.level.length)

    def apply_physics(self):
        p = self.player
        p.grav = GRAVITY * self.level.gravity
        p.flap_v = FLAP_V * self.level.flap

    def clear_world(self):
        self.shots, self.bolts, self.beams = [], [], []
        self.enemies, self.obstacles, self.pending = [], [], []
        self.shards, self.items, self.safe_marks = [], [], []
        self.boss = None
        self.boss_state = None  # None -> "warning" -> "fight" -> "cleared"
        self.victory = False    # set the instant the boss dies: nothing can hurt you after that
        self.boss_timer = 0.0
        self.stage_time = 0.0
        self.director = self.level.director(self, self.level)
        self.director.prefill()
        self.flush_pending()

    def reset_run(self):
        self.player = Bird(self.skin)
        apply_stats(self.player, self.data)
        self.apply_physics()
        self.clear_world()
        self.siren_cd = 0.0
        self.score = 0
        self.combo = 0
        self.combo_t = 0.0
        self.best_mult = 1
        self.kills = self.reflects = self.shard_count = self.near_misses = 0
        self.hits_taken = 0
        self.bosses = 0
        self.tier = 0
        self.elapsed = 0.0
        self.dead_t = 0.0
        self.death_msg = ""
        self.mega_on = False
        self.mega_end = W
        self.mega_tick = 0.0
        self.mega_snd = 0.0
        self.ready = True
        self.scroll = BASE_SCROLL
        self.diff = 0.0
        self.banner = None
        self.new_best = False
        self.fx.clear()

    def start_level(self, i, mode="adventure"):
        self.mode = mode
        self.set_level(i)
        self.reset_run()
        self.set_state("play")
        if mode == "endless":
            self.show_banner("ENDLESS", self.level.name)
        else:
            self.show_banner(self.level.name, f"LEVEL {i + 1}")
        self.audio.music(self.level.music)
        self.audio.play("select")

    def restart(self):
        self.start_level(0 if self.mode == "endless" else self.level_idx, self.mode)

    def next_stage(self):
        """Endless mode: move on to the next world, keeping score and health."""
        i = (self.level_idx + 1) % MAIN_LEVELS
        if i == 0:
            self.tier += 1
        self.set_level(i)
        self.apply_physics()
        self.clear_world()
        self.fx.do_flash(0.5)
        self.show_banner(self.level.name, f"STAGE {self.bosses + 1}")
        self.audio.music(self.level.music)

    def show_banner(self, title, sub="", dur=2.2):
        self.banner = [title, sub, dur]

    def add_obstacle(self, ob):
        """Queue an obstacle; it joins the world after the current update pass."""
        self.pending.append(ob)

    def flush_pending(self):
        if self.pending:
            self.obstacles += self.pending
            self.pending = []

    # ------------------------------------------------------------------ scoring
    def add_score(self, base, x=None, y=None, color=(255, 255, 120)):
        pts = int(base * self.mult)
        self.score += pts
        if x is not None:
            self.fx.text(x, y, f"+{pts}", color)
        return pts

    def bump_combo(self, n=1):
        old = self.mult
        self.combo += n
        self.combo_t = self.player.combo_time
        if self.mult > old:
            self.best_mult = max(self.best_mult, self.mult)
            p = self.player
            self.fx.text(p.x, p.y - 16, f"X{self.mult} COMBO!", rainbow(self.time))
            self.audio.play("combo")

    def break_combo(self):
        if self.combo >= COMBO_PER_MULT:
            self.fx.text(W // 2, 30, "COMBO LOST", (255, 80, 80))
        self.combo = 0
        self.combo_t = 0.0

    # ------------------------------------------------------------------ player actions
    def on_flap(self):
        p = self.player
        self.ready = False
        if p.flap():
            self.audio.play("flap", 0.7)
            self.fx.burst(p.x - 4, p.y + 4, [WHITE, (200, 200, 220)], n=3, speed=30, life=0.3, grav=20,
                          angle=math.pi * 0.75, spread=1.2)

    def on_dash(self):
        p = self.player
        if self.ready or not p.start_dash():
            return
        self.audio.play("dash")
        self.fx.burst(p.x - 6, p.y, [CYAN, WHITE], n=8, speed=60, life=0.3, grav=0, angle=math.pi, spread=1.0)
        r2 = PERFECT_RADIUS ** 2
        perfect = [b for b in self.bolts if b.hostile and (b.x - p.x) ** 2 + (b.y - p.y) ** 2 < r2]
        for b in perfect:
            self.reflect_bolt(b, perfect=True)
        if perfect:
            self.fx.slowmo(0.7)
            self.fx.do_flash(0.15, CYAN)
            self.fx.text(p.x, p.y - 22, "PERFECT!", CYAN, scale=2)
            self.audio.play("perfect")
            self.add_score(50)
            self.bump_combo(2)

    def try_fire(self):
        p = self.player
        if "mega" in p.powers:
            self.mega_on = True
            return
        if p.fire_cd > 0 or p.overheat > 0:
            return
        chill = "chill" in p.powers
        laser = p.laser
        p.fire_cd = FIRE_COOLDOWN * laser["cd"] * p.rate_mult * (0.75 if chill else 1.0)
        mx, my = p.x + 8, p.y + 1
        self.shots += weapons.fire(laser, mx, my, p.dmg, spread="spread" in p.powers)
        self.fx.burst(mx, my, [WHITE, laser["color"]], n=2, speed=40, life=0.12, grav=0, angle=0, spread=1.0)
        self.audio.play("shoot", 0.5)
        if chill:
            return
        p.heat += HEAT_PER_SHOT * laser["heat"] * p.heat_mult
        if p.heat >= 1.0:
            p.heat = 1.0
            p.overheat = OVERHEAT_LOCK
            self.audio.play("overheat")
            self.fx.text(p.x, p.y - 14, "OVERHEAT!", (255, 80, 40))
            self.fx.burst(p.x, p.y - 4, [(200, 200, 200), (140, 140, 160)], n=12, speed=30, life=0.8, grav=-40,
                          size=(1, 2))

    @property
    def safe(self):
        """True when the player can't be harmed (test god mode, or the boss is beaten)."""
        return self.god or self.victory

    def hurt_player(self):
        p = self.player
        if self.safe or not p.can_hurt:
            return
        if p.shield:
            p.shield = False
            p.invuln = 0.9
            self.fx.burst(p.x, p.y, [(140, 200, 255), WHITE], n=20, speed=90, life=0.4, grav=0)
            self.fx.ring(p.x, p.y, 20, (140, 200, 255))
            self.fx.text(p.x, p.y - 14, "SHIELD POP!", (140, 200, 255))
            self.fx.add_shake(3)
            self.audio.play("shield_pop")
            return
        p.hp -= 1
        self.hits_taken += 1
        p.invuln = 1.3
        self.fx.add_shake(5)
        self.fx.stop(0.07)
        self.fx.do_flash(0.15, (255, 40, 40))
        self.audio.play("hurt")
        sk = SKINS[p.skin]
        self.fx.burst(p.x, p.y, [sk["body"], sk["dark"], WHITE], n=14, speed=70, life=0.6, grav=80)
        self.break_combo()
        if p.hp <= 0:
            self.kill_player("OUT OF HEARTS!")

    def try_revive(self):
        """Second Wind upgrade: survive one knockout per run."""
        p = self.player
        if p.revives <= 0:
            return False
        p.revives -= 1
        p.hp = 1
        p.invuln = 2.5
        p.vy = FLAP_V * 1.2
        p.y = min(p.y, FLOOR_Y - 12)
        self.fx.do_flash(0.4, (255, 240, 160))
        self.fx.burst(p.x, p.y, [(255, 214, 64), WHITE], n=30, speed=110, life=0.6, grav=0)
        self.fx.text(p.x, p.y - 18, "SECOND WIND!", (255, 214, 64), scale=2)
        self.audio.play("perfect")
        return True

    def kill_player(self, msg=None):
        p = self.player
        if self.safe or not p.alive or self.try_revive():
            return
        self.death_msg = msg or self.level.death
        p.alive = False
        p.hp = 0
        p.vy = -130
        p.shield = False
        sk = SKINS[p.skin]
        self.fx.explode(p.x, p.y, [sk["body"], sk["dark"], (255, 140, 40)], big=True)
        self.fx.add_shake(8)
        self.fx.slowmo(0.8)
        self.audio.play("big_explode")
        self.audio.stop_music()
        self.break_combo()
        self.dead_t = 0.0
        self.mega_on = False

    def on_enemy_killed(self, e, how="shot"):
        self.kills += 1
        self.bump_combo()
        bonus = {"ram": ("RAM!", 15), "reflect": ("REFLECT KILL!", 40)}.get(how)
        if bonus:
            self.fx.text(e.x, e.y - 14, bonus[0], CYAN)
            self.add_score(bonus[1])
        self.add_score(e.score, e.x, e.y - 6)
        self.fx.explode(e.x, e.y, list(e.colors))
        self.fx.add_shake(2.5)
        self.fx.stop(0.03)
        self.audio.play("explode", 0.8)
        for _ in range(e.shards + self.level_idx // 2):
            self.shards.append(Shard(e.x, e.y, random.uniform(-60, 60), random.uniform(-90, -20)))
        if random.random() < self.player.luck:
            self.items.append(PowerItem(random_power(self.player.hp, self.hp_cap), e.x, e.y))

    def apply_power(self, kind):
        p = self.player
        info = POWERS[kind]
        if kind == "heart":
            p.hp = min(self.hp_cap, p.hp + 1)
        elif kind == "shield":
            p.shield = True
        else:
            p.powers[kind] = info["dur"] * p.power_mult
        self.fx.text(p.x, p.y - 14, info["label"], info["color"])
        self.fx.burst(p.x, p.y, [info["color"], WHITE], n=16, speed=80, life=0.4, grav=0)
        self.audio.play("powerup")
        self.bump_combo()

    # ------------------------------------------------------------------ boss flow
    def start_boss_warning(self):
        self.boss_state = "warning"
        self.boss_timer = 3.2
        self.siren_cd = 0.0
        self.show_banner("WARNING!", BOSSES[self.level.boss].name + " APPROACHES", 3.0)
        self.audio.music("boss")

    def on_boss_dying(self, boss):
        """Called by Boss.take on the killing blow: the level is won. Clear the screen
        and make the bird untouchable while the explosion plays out."""
        self.victory = True
        p = self.player
        p.overheat = p.heat = 0.0
        self.fx.text(p.x, p.y - 20, "VICTORY!", (255, 214, 64), scale=2)
        for e in self.enemies:
            if e.alive:
                e.alive = False
                self.fx.explode(e.x, e.y, list(e.colors))
        for bm in self.beams:
            bm.dead = True
        for b in self.bolts:
            if b.hostile and b.alive:
                b.alive = False
                self.shards.append(Shard(b.x, b.y, random.uniform(-20, 20), random.uniform(-30, 0)))
        self.fx.slowmo(0.8)
        self.fx.do_flash(0.3)
        self.fx.add_shake(8)

    def on_boss_defeated(self):
        b = self.boss
        self.boss = None
        self.bosses += 1
        self.boss_state = "cleared"
        self.boss_timer = 3.2
        self.kills += 1
        self.fx.explode(b.x, b.y, list(b.colors), big=True)
        self.fx.do_flash(0.4)
        self.fx.add_shake(9)
        self.audio.play("big_explode")
        self.audio.play("boss_down")
        pts = self.add_score(500 + 300 * self.tier)
        self.show_banner("BOSS DOWN!", f"+{pts}", 2.6)
        for _ in range(25):
            self.shards.append(Shard(b.x, min(b.y, FLOOR_Y - 20), random.uniform(-120, 60), random.uniform(-120, 20)))
        if self.mode == "endless":
            p = self.player
            self.items.append(PowerItem("heart" if p.hp < self.hp_cap else "shield", b.x - 20, min(b.y, 120)))
            self.items.append(PowerItem(random_power(p.hp, self.hp_cap), b.x + 10, min(b.y + 20, 130)))
        self.bump_combo(4)
        for e in self.enemies:
            if e.alive:
                e.alive = False
                self.fx.explode(e.x, e.y, list(e.colors))

    def update_boss_flow(self, dt):
        if self.boss_state == "warning":
            self.boss_timer -= dt
            self.siren_cd -= dt
            if self.siren_cd <= 0:
                self.siren_cd = 1.0
                self.audio.play("warn", 0.7)
            if self.boss_timer <= 0:
                self.boss = BOSSES[self.level.boss](self, self.tier)
                self.boss_state = "fight"
        elif self.boss_state == "fight":
            if self.boss.done:
                self.on_boss_defeated()
        elif self.boss_state == "cleared":
            self.boss_timer -= dt
            if self.boss_timer <= 0:
                if self.mode == "endless":
                    self.next_stage()
                else:
                    self.level_complete()

    # ------------------------------------------------------------------ run end + rewards
    def bank(self, bonus=0):
        """Turn shards into tokens and update lifetime stats. Returns newly unlocked skin names."""
        rate = 1 + 0.5 * min(self.level_idx, 4) if self.mode == "adventure" else 1.5
        endless_bonus = 40 * self.bosses if self.mode == "endless" else 0
        self.tokens_earned = int((self.shard_count * rate + bonus + endless_bonus) * self.player.token_mult)
        d = self.data
        d["tokens"] += self.tokens_earned
        before = d["shards"]
        d["shards"] += self.shard_count
        d["runs"] += 1
        return [s["name"] for s in SKINS if before < s["cost"] <= d["shards"]]

    def level_complete(self):
        i, L, d = self.level_idx, self.level, self.data
        stars = 1 + (self.score >= L.star) + (self.score >= L.star * 1.8)
        flawless = self.hits_taken == 0
        first = d["stars"][i] == 0
        bonus = L.tokens * 3 + 15 * stars + (25 if flawless else 0) + (L.tokens * 5 if first else 0)
        self.unlocks = self.bank(bonus=bonus)
        self.new_best = self.score > d["best"][i]
        d["best"][i] = max(d["best"][i], self.score)
        d["stars"][i] = max(d["stars"][i], stars)
        newly = i + 1 < MAIN_LEVELS and i + 2 > d["unlocked"]
        if i + 1 < MAIN_LEVELS:
            d["unlocked"] = max(d["unlocked"], i + 2)
        save.save(d)
        self.result = dict(stars=stars, flawless=flawless, first=first,
                           unlocked=LEVELS[i + 1].name if newly else None)
        self.set_state("complete")
        self.audio.play("perfect")

    def game_over(self):
        self.set_state("gameover")
        self.audio.play("gameover")
        self.unlocks = self.bank()
        d = self.data
        if self.mode == "endless":
            self.new_best = self.score > d["high"]
            d["high"] = max(d["high"], self.score)
            d["best_tier"] = max(d["best_tier"], self.bosses)
        else:
            i = self.level_idx
            self.new_best = self.score > d["best"][i]
            d["best"][i] = max(d["best"][i], self.score)
        save.save(d)

    # ------------------------------------------------------------------ per-frame update
    def update_play(self, dt):
        p = self.player
        self.fx.update(dt)
        if self.ready:  # bobbing in place until the first flap
            p.y = H * 0.45 + math.sin(self.time * 4) * 4
            p.flap_anim = 0.15 if int(self.time * 6) % 2 else 0
            self.bg.update(dt, self.scroll)
            return
        self.elapsed += dt
        self.stage_time += dt
        self.diff = self.level.base_diff + 0.8 * min(1.0, self.stage_time / 80.0) + 0.4 * self.tier
        target = BASE_SCROLL * (1 + 0.2 * min(self.diff, 2.5))
        if self.boss_state == "fight":
            target *= 0.8
        if not p.alive:
            target *= 0.4
        self.scroll += (target - self.scroll) * min(1.0, dt * 2)
        self.bg.update(dt, self.scroll)

        p.update(dt)
        if self.victory and p.alive:  # victory glide: ease the bird to the middle of the screen
            p.vy = (H * 0.45 - p.y) * 3
            if random.random() < 0.15:
                self.fx.burst(p.x, p.y, [(255, 214, 64), WHITE], n=1, speed=30, life=0.5, grav=-20)
        self.mega_on = False
        if p.alive and self.fire_held():
            self.try_fire()
        if self.combo > 0:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
        if self.safe_marks:
            for m in self.safe_marks:
                m[1] -= dt
            self.safe_marks = [m for m in self.safe_marks if m[1] > 0]

        self.director.update(dt)
        if self.boss_state is None and p.alive and self.stage_time >= self.level.length:
            self.start_boss_warning()
        self.update_boss_flow(dt)
        self._update_entities(dt)

        if p.alive:
            self.collide()
            if self.mega_on:
                self.update_mega(dt)
            self._check_bounds()
        else:
            self.dead_t += dt
            if self.dead_t > 1.4:
                self.game_over()
        self._cull()

    def _update_entities(self, dt):
        for ob in self.obstacles:
            ob.update(dt, self)
            ob.special(dt, self)
        self.flush_pending()
        homing = [s for s in self.shots if s.homing]
        if homing:
            targets = [e for e in self.enemies if e.alive and 0 < e.x < W]
            if self.boss and self.boss.entered:
                targets.append(self.boss)
            if targets:
                for sh in homing:
                    tg = min(targets, key=lambda e: (e.x - sh.x) ** 2 + (e.y - sh.y) ** 2)
                    sh.steer(tg.x, tg.y, dt)
        for s in self.shots:
            s.update(dt)
        for b in self.bolts:
            b.update(dt)
        for bm in self.beams:
            bm.update(dt)
            if bm.just_fired and not bm.in_safe:
                self.audio.play("beam", 0.8)
                self.fx.add_shake(2)
        for e in self.enemies:
            e.update(dt, self)
        if self.boss:
            self.boss.update(dt, self)
        for s in self.shards:
            s.update(dt, self)
        for it in self.items:
            it.update(dt, self)

    def _check_bounds(self):
        p = self.player
        if p.y + p.r >= FLOOR_Y:
            self.kill_player()
            if self.safe:
                p.y, p.vy = FLOOR_Y - p.r - 1, FLAP_V
        elif p.y - p.r <= CEIL_Y:  # electric ceiling: zap and bounce down
            p.y = CEIL_Y + p.r + 1
            p.vy = 140
            self.audio.play("zap")
            self.fx.burst(p.x, CEIL_Y, [CYAN, WHITE], n=10, speed=60, life=0.3, grav=100)
            self.hurt_player()

    def _cull(self):
        self.shots = [s for s in self.shots if s.alive]
        self.bolts = [b for b in self.bolts if b.alive]
        self.beams = [b for b in self.beams if not b.dead]
        self.enemies = [e for e in self.enemies if e.alive and not e.offscreen()]
        self.obstacles = [o for o in self.obstacles if not o.offscreen()]
        self.shards = [s for s in self.shards if s.alive]
        self.items = [i for i in self.items if i.alive]
