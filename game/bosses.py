"""Boss base class: hit zones ('crit' / 'hit' / 'block'), three HP phases, a pattern
rotation, sweeping lasers with safe windows, and a shared death sequence.

Each world defines its own boss subclass and registers it with `@register_boss`.
"""
import math
import random


from .lasers import Beam, Bolt, sweep_beams
from .settings import H, W


class Boss:
    name = "BOSS"
    base_hp = 80
    hp_tier = 45
    size = 18
    colors = [(200, 60, 255), (255, 120, 180), (80, 230, 255)]
    patterns = {1: [], 2: [], 3: []}
    cools = {1: 1.7, 2: 1.35, 3: 1.05}

    def __init__(self, game, tier):
        self.tier = tier
        self.max_hp = self.base_hp + self.hp_tier * tier
        self.hp = float(self.max_hp)
        self.x = W + 60.0
        self.y = H * 0.42
        self.t = 0.0
        self.flash = 0.0
        self.alive = True
        self.entered = False
        self.dying = 0.0
        self.done = False
        self.cool = 2.0
        self.idx = 0
        self.boom_cd = 0.0
        self.spiral = 0.0
        self.spiral_a = 0.0
        self.spiral_cd = 0.0
        self.hold = 0.0  # boss stays still while sweeping so the safe band doesn't move

    @property
    def phase(self):
        r = self.hp / self.max_hp
        return 1 if r > 0.66 else (2 if r > 0.33 else 3)

    def zones(self):
        return []

    def hit_test(self, x, y):
        for r, k in self.zones():
            if r.collidepoint(x, y):
                return k
        return None

    def hits_rect(self, rect, kinds=("hit", "crit")):
        return any(r.colliderect(rect) for r, k in self.zones() if k in kinds)

    def take(self, dmg, game, point=None):
        if not self.entered or self.dying > 0:
            return "immune"
        kind = self.hit_test(*point) if point is not None else "hit"
        if kind == "block":
            return "block"
        kind = kind or "hit"
        self.hp -= dmg * (2.5 if kind == "crit" else 1.0) / game.boss_mult
        self.flash = 0.06
        if self.hp <= 0:
            self.hp = 0
            self.dying = 2.2
            game.on_boss_dying(self)
        return kind

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.dying > 0:
            self.dying -= dt
            self.y += 12 * dt
            self.boom_cd -= dt
            if self.boom_cd <= 0:
                self.boom_cd = 0.09
                s = self.size
                game.fx.explode(self.x + random.uniform(-s, s), self.y + random.uniform(-s, s), list(self.colors))
                game.fx.add_shake(4)
                game.audio.play("explode", 0.7)
            if self.dying <= 0:
                self.done = True
                self.alive = False
            return
        if self.hold > 0:
            self.hold -= dt
            return
        self.behave(dt, game)

    def behave(self, dt, game):
        pass

    def tick_patterns(self, dt, game):
        if self.spiral > 0:
            self.spiral -= dt
            self.spiral_cd -= dt
            if self.spiral_cd <= 0:
                self.spiral_cd = 0.07
                arms = 2 if self.phase == 3 else 1
                ox, oy = self.spiral_origin()
                for k in range(arms):
                    a = self.spiral_a + k * math.pi
                    game.bolts.append(Bolt(ox, oy, math.cos(a) * 80, math.sin(a) * 80, color=self.spiral_color))
                self.spiral_a += 0.55
                game.audio.play("eshot", 0.4)
            return
        self.cool -= dt
        if self.cool <= 0:
            pats = self.patterns[self.phase]
            pat = pats[self.idx % len(pats)]
            self.idx += 1
            self.attack(pat, game)
            self.cool = self.cools[self.phase] / (1 + 0.15 * self.tier)

    spiral_color = (255, 214, 64)

    def spiral_origin(self):
        return self.x, self.y

    def start_spiral(self, dur=1.3):
        self.spiral = dur
        self.spiral_a = random.uniform(0, math.tau)

    def attack(self, pat, game):
        pass

    def fan(self, game, ox, oy, n, spread=0.13, speed=None, color=(255, 70, 200), grav=0.0):
        p = game.player
        speed = speed or 95 + 10 * self.tier
        base = math.atan2(p.y - oy, p.x - ox)
        for i in range(n):
            a = base + (i - (n - 1) / 2) * spread
            game.bolts.append(Bolt(ox, oy, math.cos(a) * speed, math.sin(a) * speed, color=color, grav=grav))
        game.audio.play("eshot")

    def aimed_beam(self, game, origin, width=7, color=(255, 60, 200)):
        p = game.player
        gx, gy = origin()
        game.beams.append(Beam(origin, math.atan2(p.y - gy, p.x - gx), warn=0.7, fire=0.45, width=width,
                               color=color, owner=self))
        game.audio.play("charge")

    def sweep(self, game, origin, n=1, color=(255, 60, 200), width=6):
        beams = sweep_beams(self, origin, n=n, color=color, width=width, player_x=game.player.x)
        game.beams.extend(beams)
        self.hold = beams[0].warn + beams[0].fire
        game.audio.play("charge")

    def draw(self, surf, game):
        pass
