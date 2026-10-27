"""The laser bird: flap physics, heat, reflect-dash, powers and HP."""
import pygame

from .settings import (DASH_COOLDOWN, DASH_DIST, DASH_TIME, FLAP_V, FLOOR_Y, GRAVITY,
                       HEAT_COOL_RATE, H, MAX_FALL, MAX_HP, OVERHEAT_LOCK, PLAYER_X)


class Bird:
    def __init__(self, skin=0):
        self.skin = skin
        self.x = PLAYER_X
        self.y = H * 0.45
        self.vy = 0.0
        self.hp = MAX_HP
        self.alive = True
        self.invuln = 0.0
        self.heat = 0.0
        self.overheat = 0.0
        self.fire_cd = 0.0
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.powers = {}
        self.shield = False
        self.flap_anim = 0.0
        self.spin = 0.0
        self.afterimages = []
        self.grav = GRAVITY
        self.flap_v = FLAP_V
        # shop-upgradable stats (see progression.apply_stats)
        self.heat_mult = 1.0
        self.cool_mult = 1.0
        self.rate_mult = 1.0
        self.dmg = 1.0
        self.dash_cd_max = DASH_COOLDOWN
        self.reflect_r = 13
        self.max_hp = MAX_HP
        self.magnet_r = 18
        self.token_mult = 1.0
        self.luck = 0.08
        self.power_mult = 1.0
        self.combo_time = 3.0
        self.revives = 0
        self.laser = None

    @property
    def r(self):
        return 2.5 if "tiny" in self.powers else 4.0

    @property
    def dashing(self):
        return self.dash_t > 0

    @property
    def can_hurt(self):
        return self.alive and self.invuln <= 0 and not self.dashing

    def hitbox(self):
        r = self.r
        return pygame.Rect(int(self.x - r), int(self.y - r), int(r * 2), int(r * 2))

    def flap(self):
        if self.alive and not self.dashing:
            self.vy = self.flap_v
            self.flap_anim = 0.15
            return True
        return False

    def start_dash(self):
        if self.alive and self.dash_cd <= 0 and not self.dashing:
            self.dash_t = DASH_TIME
            self.dash_cd = self.dash_cd_max
            self.vy = 0
            return True
        return False

    def update(self, dt):
        self.flap_anim = max(0.0, self.flap_anim - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.fire_cd = max(0.0, self.fire_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        for k in list(self.powers):
            self.powers[k] -= dt
            if self.powers[k] <= 0:
                del self.powers[k]
        if self.overheat > 0:
            self.overheat -= dt
            self.heat = max(0.0, self.overheat / OVERHEAT_LOCK)
        else:
            self.heat = max(0.0, self.heat - HEAT_COOL_RATE * self.cool_mult * dt)
        for a in self.afterimages:
            a[2] -= dt
        self.afterimages = [a for a in self.afterimages if a[2] > 0]

        if not self.alive:
            self.vy = min(MAX_FALL, self.vy + self.grav * dt)
            self.y += self.vy * dt
            self.spin += 600 * dt
            if self.y > FLOOR_Y - 3:
                self.y = FLOOR_Y - 3
                self.vy = 0
            return
        if self.dashing:
            self.dash_t -= dt
            self.x += DASH_DIST / DASH_TIME * dt
            self.vy = 0
            self.afterimages.append([self.x, self.y, 0.25])
        else:
            self.vy = min(MAX_FALL, self.vy + self.grav * dt)
            self.x += (PLAYER_X - self.x) * min(1.0, dt * 1.5)
        self.y += self.vy * dt

    def draw(self, surf, art, t):
        up, down = art.bird[self.skin]
        img = up if self.flap_anim > 0 else down
        tiny = "tiny" in self.powers
        for ax, ay, life in self.afterimages:
            ghost = art.tint(down, (120, 230, 255))
            if tiny:
                ghost = art.small(ghost)
            g = ghost.copy()
            g.set_alpha(int(150 * life / 0.25))
            surf.blit(g, (int(ax - g.get_width() / 2), int(ay - g.get_height() / 2)))
        if self.alive and self.invuln > 0 and int(self.invuln * 14) % 2 == 0:
            return
        if tiny:
            img = art.small(img)
        if not self.alive:
            angle = -self.spin
        elif self.dashing:
            angle = 0
        else:
            angle = max(-55.0, min(25.0, -self.vy * 0.12))
        rot = pygame.transform.rotate(img, angle)
        surf.blit(rot, (int(self.x - rot.get_width() / 2), int(self.y - rot.get_height() / 2)))
        if self.shield and self.alive:
            col = (140, 200, 255) if int(t * 8) % 2 else (255, 255, 255)
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), 10, 1)
        if self.overheat > 0 and int(t * 12) % 2:
            surf.fill((255, 80, 40), (int(self.x + 6), int(self.y), 2, 2))
