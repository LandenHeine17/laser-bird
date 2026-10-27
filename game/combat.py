"""Collisions and damage for a play session (mixed into Game)."""
import math
import random

import pygame

from .powerups import Shard
from .util import WHITE

CYAN = (80, 230, 255)


class CombatMixin:
    # ------------------------------------------------------------------ queries
    def solid_at(self, x, y, exclude=None):
        """The (obstacle, part) occupying a point, or (None, None)."""
        for ob in self.obstacles:
            if ob is exclude or not ob.solid or x < ob.x - 2 or x > ob.x + ob.w + 2:
                continue
            for part in ob.parts:
                if part.alive and part.x <= x < part.x + part.w and part.y <= y < part.y + part.h:
                    return ob, part
        return None, None

    # ------------------------------------------------------------------ damage helpers
    def hit_part(self, ob, part, dmg, x, y):
        if part.breakable:
            part.hp -= dmg
            part.flash = 0.06
            if part.hp <= 0:
                self.break_part(ob, part)
            else:
                self.audio.play("hit", 0.4)
        else:
            self.sparks(x, y)
            self.audio.play("clank", 0.5)

    def break_part(self, ob, part, quiet=False):
        if not part.alive:
            return
        part.alive = False
        r = part.rect
        self.fx.burst(r.centerx, r.centery, ob.colors(part), n=10, speed=70, life=0.5, grav=140, size=(1, 2))
        if not quiet:
            self.audio.play("crystal", 0.7)
            self.score += 2
            if random.random() < ob.shard_chance:
                self.shards.append(Shard(r.centerx, r.centery, random.uniform(-30, 30), random.uniform(-60, -10)))
        ob.on_break(part, self)

    def sparks(self, x, y):
        self.fx.burst(x, y, [(255, 220, 120), WHITE], n=4, speed=60, life=0.2, grav=0, angle=math.pi, spread=1.6)

    def splash(self, x, y, r, dmg):
        self.fx.ring(x, y, r, (200, 120, 255))
        self.fx.burst(x, y, [(200, 120, 255), WHITE], n=10, speed=80, life=0.3, grav=0)
        self.audio.play("explode", 0.4)
        for e in self.enemies:
            if e.alive and math.hypot(e.x - x, e.y - y) < r + 4:
                if e.take(dmg, self) == "kill":
                    self.on_enemy_killed(e)
        if self.boss and self.boss.hits_rect(pygame.Rect(int(x - r), int(y - r), int(2 * r), int(2 * r))):
            self.boss.take(dmg * 0.5, self)

    def boss_hit_fx(self, res, x, y):
        if res == "crit":
            self.fx.burst(x, y, [(255, 214, 64), WHITE, CYAN], n=6, speed=70, life=0.3, grav=0)
            if random.random() < 0.3:
                self.fx.text(x, y - 8, "CRIT!", (255, 214, 64))
            self.audio.play("crystal", 0.4)
        elif res == "hit":
            self.fx.burst(x, y, [WHITE, (200, 120, 230)], n=3, speed=40, life=0.2, grav=0)
            self.audio.play("hit", 0.4)
        elif res == "block":
            self.sparks(x, y)
            self.audio.play("clank", 0.5)

    def reflect_bolt(self, b, perfect=False):
        p = self.player
        targets = [e for e in self.enemies if e.alive and e.x > p.x]
        if self.boss is not None and self.boss.entered and self.boss.dying <= 0:
            targets.append(self.boss)
        target = None
        if targets:
            e = min(targets, key=lambda e: (e.x - b.x) ** 2 + (e.y - b.y) ** 2)
            target = (e.x, e.y)
        b.reflect(target)
        self.reflects += 1
        self.fx.burst(b.x, b.y, [CYAN, WHITE], n=8, speed=70, life=0.3, grav=0)
        if not perfect:
            self.audio.play("reflect")
            self.add_score(10, b.x, b.y - 6, CYAN)
            self.bump_combo()

    # ------------------------------------------------------------------ per-frame collisions
    def collide(self):
        self._collide_shots()
        self._collide_bolts()
        self._collide_beams()
        self._collide_obstacles()
        self._collide_bodies()
        self._collect_pickups()

    def _collide_shots(self):
        boss = self.boss
        for s in self.shots:
            ob, part = self.solid_at(s.x, s.y)
            if part:
                s.alive = False
                self.hit_part(ob, part, s.dmg, s.x, s.y)
                if s.splash:
                    self.splash(s.x, s.y, s.splash, s.dmg * 0.5)
                continue
            for e in self.enemies:
                if e.alive and id(e) not in s.hit and e.rect().collidepoint(s.x, s.y):
                    res = e.take(s.dmg, self, s)
                    if res == "kill":
                        self.on_enemy_killed(e)
                    elif res == "hit":
                        self.fx.burst(s.x, s.y, [WHITE, (255, 220, 120)], n=4, speed=50, life=0.2, grav=0)
                        self.audio.play("hit", 0.5)
                    if s.splash:
                        self.splash(s.x, s.y, s.splash, s.dmg * 0.5)
                        s.alive = False
                    elif s.pierce > 0 and res != "reflect":
                        s.pierce -= 1
                        s.hit.add(id(e))
                    else:
                        s.alive = False
                    break
            if s.alive and boss and boss.hit_test(s.x, s.y):
                s.alive = False
                self.boss_hit_fx(boss.take(s.dmg, self, point=(s.x, s.y)), s.x, s.y)
                if s.splash:
                    self.splash(s.x, s.y, s.splash, s.dmg * 0.5)

    def _collide_bolts(self):
        p = self.player
        boss = self.boss
        for b in self.bolts:
            if not b.alive:
                continue
            ob, part = self.solid_at(b.x, b.y)
            if part:
                b.alive = False
                self.fx.burst(b.x, b.y, [b.color, WHITE], n=3, speed=40, life=0.2, grav=0)
                if not b.hostile and part.breakable:
                    self.hit_part(ob, part, 3, b.x, b.y)
                continue
            if b.hostile:
                self._hostile_bolt(b)
                continue
            for e in self.enemies:  # reflected bolts hit enemies hard
                if e.alive and e.rect().collidepoint(b.x, b.y):
                    b.alive = False
                    if e.take(2 + p.dmg, self, b) == "kill":
                        self.on_enemy_killed(e, "reflect")
                    break
            if b.alive and boss and boss.hit_test(b.x, b.y):
                b.alive = False
                res = boss.take(3 + p.dmg, self, point=(b.x, b.y))
                self.boss_hit_fx(res, b.x, b.y)
                if res in ("hit", "crit"):
                    self.fx.text(b.x, b.y - 8, "REFLECT!" if res == "hit" else "REFLECT CRIT!", CYAN)

    def _hostile_bolt(self, b):
        p = self.player
        d = math.hypot(b.x - p.x, b.y - p.y)
        if p.dashing and d < p.reflect_r:
            self.reflect_bolt(b)
        elif d < b.r + p.r:
            if p.can_hurt and not self.safe:
                b.alive = False
                self.hurt_player()
        else:
            # near miss: award once the bolt has come close and is moving away again
            if d < 14:
                b.close = True
            elif b.close and not b.awarded and d > b.last_d and p.can_hurt:
                b.awarded = True
                self.near_misses += 1
                self.fx.text(p.x, p.y - 12, "CLOSE!", (255, 214, 64))
                self.add_score(10)
                self.bump_combo()
            b.last_d = d

    def _collide_beams(self):
        p = self.player
        for bm in self.beams:
            if not bm.hits(p.x, p.y, p.r):
                continue
            if not p.dashing:
                self.hurt_player()
            elif not bm.phased:
                bm.phased = True
                self.fx.text(p.x, p.y - 14, "PHASED!", (255, 120, 255))
                self.add_score(25)
                self.bump_combo()

    def _collide_obstacles(self):
        p = self.player
        hb = p.hitbox()
        for ob in self.obstacles:
            if ob.scores and not ob.passed and ob.x + ob.w < p.x - 4:
                ob.passed = True
                self.add_score(10)
                self.bump_combo()
                self.audio.play("pass", 0.5)
            if ob.x > p.x + 12 or ob.x + ob.w < p.x - 12:
                continue
            if not p.dashing and ob.hazard_hits(p.x, p.y, p.r):
                self.hurt_player()
            for part in ob.parts:
                if not (part.alive and part.rect.colliderect(hb)):
                    continue
                if p.dashing:  # dashing smashes through anything breakable
                    if part.breakable:
                        self.break_part(ob, part)
                        self.fx.add_shake(2)
                elif p.can_hurt:
                    if part.breakable:
                        self.break_part(ob, part)
                    self.hurt_player()
                    p.vy = 120 if part.y + part.h / 2 < p.y else -150

    def _collide_bodies(self):
        p = self.player
        hb = p.hitbox()
        for e in self.enemies:
            if not (e.alive and e.rect().colliderect(hb)):
                continue
            if p.dashing and e.rammable:
                e.alive = False
                self.on_enemy_killed(e, "ram")
            elif p.can_hurt:
                self.hurt_player()
                if e.rammable:
                    e.alive = False
                    self.on_enemy_killed(e)
        boss = self.boss
        if boss and boss.dying <= 0 and boss.hits_rect(hb, ("hit", "crit", "block")):
            self.hurt_player()
            p.vy = -120

    def _collect_pickups(self):
        p = self.player
        for s in self.shards:
            if (s.x - p.x) ** 2 + (s.y - p.y) ** 2 < 64:
                s.alive = False
                self.shard_count += 1
                self.add_score(5)
                self.audio.play("shard", 0.5)
                self.fx.burst(s.x, s.y, [CYAN, WHITE], n=3, speed=30, life=0.2, grav=0)
        for it in self.items:
            if (it.x - p.x) ** 2 + (it.y - p.y) ** 2 < 121:
                it.alive = False
                self.apply_power(it.kind)

    # ------------------------------------------------------------------ mega beam power-up
    def update_mega(self, dt):
        p = self.player
        x0, y0 = p.x + 8, p.y - 2
        end = 330.0
        for ob in self.obstacles:  # unbreakable blocks stop the beam
            if not ob.solid or ob.x + ob.w < x0:
                continue
            for part in ob.parts:
                if part.alive and not part.breakable and part.x > x0 and part.y < y0 + 5 and part.y + part.h > y0:
                    end = min(end, part.x)
        self.mega_end = end
        beam = pygame.Rect(int(x0), int(y0), max(1, int(end - x0)), 5)
        for b in self.bolts:
            if b.hostile and beam.collidepoint(b.x, b.y):
                b.alive = False
                self.fx.burst(b.x, b.y, [(255, 60, 200), WHITE], n=3, speed=40, life=0.2, grav=0)
        self.mega_snd -= dt
        if self.mega_snd <= 0:
            self.mega_snd = 0.12
            self.audio.play("zap", 0.35)
        self.mega_tick -= dt
        if self.mega_tick > 0:
            return
        self.mega_tick = 0.05  # damage ticks 20x per second
        for e in self.enemies:
            if e.alive and beam.colliderect(e.rect()):
                if e.take(p.dmg, self) == "kill":
                    self.on_enemy_killed(e)
        for ob in self.obstacles:
            if ob.solid and ob.x < beam.right and ob.x + ob.w > beam.x:
                for part in ob.parts:
                    if part.alive and part.breakable and beam.colliderect(part.rect):
                        part.hp -= 1
                        part.flash = 0.05
                        if part.hp <= 0:
                            self.break_part(ob, part)
        if self.boss and self.boss.hits_rect(beam):
            self.boss.take(0.6 * p.dmg, self)
            if random.random() < 0.3:
                self.fx.burst(beam.right, p.y, [(255, 60, 200), WHITE], n=3, speed=60, life=0.2, grav=0)
