"""The application shell: window, main loop, input routing, state machine and drawing.

Play-session logic lives in RunMixin (run.py) and collisions in CombatMixin
(combat.py); menus and HUD are in menus.py / hud.py.
"""
import math
import random
import sys

import pygame

from . import hud, menus, save
from .audio import Audio
from .combat import CombatMixin
from .effects import FX
from .lasers import PlayerShot
from .run import RunMixin
from .settings import CEIL_Y, FPS, H, SCALE, SHOT_SPEED, SKINS, W
from .sprites import Art, draw_text
from .util import WHITE
from .worlds import LEVELS

FLAP_KEYS = (pygame.K_SPACE, pygame.K_w, pygame.K_UP)
DASH_KEYS = (pygame.K_k, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_s, pygame.K_DOWN)
FIRE_KEYS = (pygame.K_j, pygame.K_f, pygame.K_x, pygame.K_l)
FIRE_PAD_BUTTONS = (2, 5, 7)
SECRET_BUTTON = pygame.Rect(2, H - 12, 10, 10)  # tiny bamboo leaf in the main menu's corner
PLAY_STATES = ("play", "pause", "gameover", "complete")


class Game(RunMixin, CombatMixin):
    def __init__(self):
        pygame.display.set_caption("LASER BIRD")
        self.fullscreen = False
        self.window = pygame.display.set_mode((W * SCALE, H * SCALE), pygame.RESIZABLE)
        self.canvas = pygame.Surface((W, H))
        self.world = pygame.Surface((W, H))
        self.light = pygame.Surface((W, H), pygame.SRCALPHA)  # additive glow layer (cones, beams)
        self.scaled = None
        self.view = (0, 0, SCALE)  # window offset + scale, for mapping mouse clicks
        self.clock = pygame.time.Clock()
        self.art = Art()
        self.audio = Audio()
        self.fx = FX()
        self.data = save.load(len(LEVELS))
        self.skin = self.data["skin"] if self.skin_unlocked(self.data["skin"]) else 0
        self.auto_fire = False  # test hooks
        self.god = False
        self.joysticks = []
        self.time = 0.0
        self.state = "title"
        self.state_t = 0.0
        # menu state
        self.menu_i = 0
        self.level_sel = min(self.data["unlocked"], len(LEVELS)) - 1
        self.skin_sel = self.skin
        self.thumbs = None
        self.title_shots = []
        self.title_cd = 0.0
        self.shop_tab = 0
        self.shop_i = 0
        self.shop_scroll = 0
        self.shop_return = "menu"
        self.shop_msg = ("", 0.0)
        # results of the last run
        self.unlocks = []
        self.result = {}
        self.tokens_earned = 0
        self.mode = "adventure"
        self.tier = 0
        self.set_level(0)
        self.reset_run()
        self.audio.music("main")

    def skin_unlocked(self, i):
        return 0 <= i < len(SKINS) and self.data["shards"] >= SKINS[i]["cost"]

    def set_state(self, s):
        self.state = s
        self.state_t = 0.0

    # ------------------------------------------------------------------ main loop
    def run(self):
        while True:
            dt_real = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.handle_events()
            self.step(dt_real)
            self.draw()
            self.present()

    def step(self, dt_real):
        self.time += dt_real
        self.state_t += dt_real
        self.fx.tick_real(dt_real)
        if self.fx.hitstop > 0:  # freeze-frame on big hits
            self.fx.hitstop -= dt_real
            dt = 0.0
        else:
            dt = dt_real * (0.35 if self.fx.slow > 0 else 1.0)
        if self.banner:
            self.banner[2] -= dt_real
            if self.banner[2] <= 0:
                self.banner = None
        if self.state == "play":
            self.update_play(dt)
        elif self.state in ("gameover", "complete"):
            self.bg.update(dt, self.scroll * 0.3)
            self.fx.update(dt)
        elif self.state != "pause":
            self.update_menu_bg(dt)

    def update_menu_bg(self, dt):
        self.bg.update(dt, 40)
        self.fx.update(dt)
        self.title_cd -= dt
        if self.title_cd <= 0:
            self.title_cd = random.choice((0.15, 0.15, 0.5, 0.9))
            self.title_shots.append(PlayerShot(110, 113 + math.sin(self.time * 3) * 5, SHOT_SPEED, 0))
        for s in self.title_shots:
            s.update(dt)
        self.title_shots = [s for s in self.title_shots if s.alive]

    # ------------------------------------------------------------------ input
    def fire_held(self):
        if self.auto_fire:
            return True
        keys = pygame.key.get_pressed()
        if any(keys[k] for k in FIRE_KEYS) or pygame.mouse.get_pressed()[2]:
            return True
        return any(b < j.get_numbuttons() and j.get_button(b) for j in self.joysticks for b in FIRE_PAD_BUTTONS)

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.JOYDEVICEADDED:
                self.joysticks.append(pygame.joystick.Joystick(e.device_index))
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif e.key == pygame.K_m:
                    self.audio.toggle_mute()
                else:
                    self.on_key(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.on_click(e)
            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:
                    self.on_key(pygame.K_SPACE)
                elif e.button in (1, 4):
                    self.on_key(pygame.K_k if self.state == "play" else pygame.K_ESCAPE)
                elif e.button in (6, 9):
                    self.on_key(pygame.K_ESCAPE)
            elif e.type == pygame.JOYHATMOTION:
                hx, hy = e.value
                if hx:
                    self.on_key(pygame.K_RIGHT if hx > 0 else pygame.K_LEFT)
                if hy:
                    self.on_key(pygame.K_UP if hy > 0 else pygame.K_DOWN)

    def on_click(self, e):
        ox, oy, sc = self.view
        mx, my = (e.pos[0] - ox) / sc, (e.pos[1] - oy) / sc
        if e.button == 1 and self.state == "menu" and SECRET_BUTTON.inflate(4, 4).collidepoint(mx, my):
            menus.open_secret(self)
        elif e.button == 1:
            self.on_key(pygame.K_SPACE)
        elif e.button == 2:
            self.on_key(pygame.K_k)

    def on_key(self, k):
        if self.state != "play":
            menus.on_key(self, k)
        elif k in FLAP_KEYS:
            self.on_flap()
        elif k in DASH_KEYS:
            self.on_dash()
        elif k in (pygame.K_p, pygame.K_ESCAPE) and self.player.alive:
            self.set_state("pause")
            self.audio.play("select")

    def to_menu(self, state="menu"):
        self.set_level(self.level_sel if state == "levels" else 0)
        self.reset_run()
        self.set_state(state)
        self.audio.music("main")

    def quit(self):
        save.save(self.data)
        pygame.quit()
        sys.exit(0)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.scaled = None
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((W * SCALE, H * SCALE), pygame.RESIZABLE)

    # ------------------------------------------------------------------ drawing
    def draw(self):
        c = self.canvas
        if self.state not in PLAY_STATES:
            menus.draw_menu_state(c, self)
        else:
            self.draw_world()
            c.fill((0, 0, 0))
            c.blit(self.world, self.fx.offset())
            if self.state in ("play", "pause"):
                hud.draw(c, self)
            if self.ready and self.state == "play":
                menus.draw_ready(c, self)
            menus.draw_banner(c, self)
            overlay = {"pause": menus.draw_pause, "gameover": menus.draw_gameover,
                       "complete": menus.draw_complete}.get(self.state)
            if overlay:
                overlay(c, self)
        self.fx.draw_flash(c)

    def draw_world(self):
        s = self.world
        t = self.time
        self.light.fill((0, 0, 0, 0))
        self.bg.draw_back(s, t)
        for o in self.obstacles:
            o.draw(s, self)
        for o in self.shards:
            o.draw(s, self.art)
        for o in self.items:
            o.draw(s, self.art)
        for o in self.enemies:
            o.draw(s, self)
        if self.boss:
            self.boss.draw(s, self)
        s.blit(self.light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        for bm in self.beams:
            bm.draw(s, t)
        for group in (self.bolts, self.shots):
            for o in group:
                o.draw(s)
        if self.mega_on and self.player.alive:
            self.draw_mega(s)
        self.player.draw(s, self.art, t)
        self.fx.draw(s)
        self.bg.draw_ground(s, t)
        self.draw_ceiling(s)
        for y, left in self.safe_marks:
            if int(left * 8) % 2:
                draw_text(s, "SAFE >", 4, int(y) - 2, (90, 255, 120))
        self.fx.draw_texts(s)

    def draw_ceiling(self, s):
        """The crackling electric fence along the top of the screen."""
        rnd = random.random
        for x in range(0, W, 2):
            if rnd() < 0.6:
                s.set_at((x, CEIL_Y - 1 - int(rnd() * 3)), (80, 230, 255) if rnd() < 0.8 else WHITE)

    def draw_mega(self, s):
        p = self.player
        x0, y = int(p.x + 8), int(p.y)
        w = int(self.mega_end - x0)
        thick = 5 + (1 if int(self.time * 40) % 2 else 0)
        s.fill((150, 20, 110), (x0, y - thick // 2 - 1, w, thick + 2))
        s.fill((255, 60, 200), (x0, y - thick // 2, w, thick))
        s.fill(WHITE, (x0, y - 1, w, 2))
        pygame.draw.circle(s, WHITE, (x0, y), 4)
        if random.random() < 0.6:
            self.fx.burst(self.mega_end, y, [(255, 60, 200), WHITE], n=2, speed=60, life=0.2, grav=0,
                          angle=math.pi, spread=2.0)

    def present(self):
        """Scale the 320x180 canvas by the largest whole number that fits the window."""
        ww, wh = self.window.get_size()
        s = max(1, min(ww // W, wh // H))
        size = (W * s, H * s)
        if self.scaled is None or self.scaled.get_size() != size:
            self.scaled = pygame.Surface(size)
            self.window.fill((0, 0, 0))
        pygame.transform.scale(self.canvas, size, self.scaled)
        ox, oy = (ww - size[0]) // 2, (wh - size[1]) // 2
        self.window.blit(self.scaled, (ox, oy))
        self.view = (ox, oy, s)
        pygame.display.flip()
