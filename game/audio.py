"""Procedurally synthesized chiptune SFX and music (no asset files)."""
import io
import math
import random
import threading
import wave
from array import array

import pygame

SR = 22050


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def synth(dur, f0, f1=None, wave_="square", vol=0.4, duty=0.5, curve=2.0, attack=0.004):
    n = int(SR * dur)
    f1 = f0 if f1 is None else f1
    out = []
    ph = 0.0
    hold = 0.0
    last = -1
    att = max(1, int(attack * SR))
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        ph += f / SR
        p = ph % 1.0
        if wave_ == "square":
            v = 1.0 if p < duty else -1.0
        elif wave_ == "tri":
            v = 4.0 * abs(p - 0.5) - 1.0
        elif wave_ == "saw":
            v = 2.0 * p - 1.0
        elif wave_ == "sine":
            v = math.sin(math.tau * ph)
        else:  # sample-and-hold noise, pitched by f
            k = int(ph)
            if k != last:
                last = k
                hold = random.uniform(-1, 1)
            v = hold
        env = min(1.0, i / att) * (1.0 - t) ** curve
        out.append(v * env * vol)
    return out


def seq(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def mix(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)]


def to_sound(samples):
    arr = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(arr.tobytes())
    bio.seek(0)
    return pygame.mixer.Sound(file=bio)


def make_music(bpm, prog, seed, intense=False):
    step = 60.0 / bpm / 4
    steps = 16 * len(prog)
    n = int(SR * step * steps)
    buf = [0.0] * n
    rnd = random.Random(seed)

    def note(st, ln_steps, m, kind, vol, duty=0.5, decay=3.0):
        s0 = int(st * step * SR)
        ln = int(ln_steps * step * SR)
        inc = midi(m) / SR
        ph = 0.0
        for i in range(ln):
            ph += inc
            p = ph % 1.0
            if kind == "sq":
                v = 1.0 if p < duty else -1.0
            else:
                v = 4.0 * abs(p - 0.5) - 1.0
            env = math.exp(-decay * i / ln) * min(1.0, i / 60) * min(1.0, (ln - i) / 60)
            buf[(s0 + i) % n] += v * vol * env

    def kick(st):
        s0 = int(st * step * SR)
        ln = int(0.11 * SR)
        ph = 0.0
        for i in range(ln):
            f = 160 * (1 - i / ln) + 40
            ph += f / SR
            buf[(s0 + i) % n] += math.sin(math.tau * ph) * 0.55 * (1 - i / ln)

    def noise(st, dur, vol, hold_every=1):
        s0 = int(st * step * SR)
        ln = int(dur * SR)
        v = 0.0
        for i in range(ln):
            if i % hold_every == 0:
                v = random.uniform(-1, 1)
            buf[(s0 + i) % n] += v * vol * (1 - i / ln) ** 2

    # lead rhythm reused every two bars so the tune has a hook
    rhythm = []
    pos = 0
    while pos < 32:
        ln = rnd.choice([1, 2, 2, 2, 3, 4])
        ln = min(ln, 32 - pos)
        rhythm.append((pos, ln, rnd.random() < 0.18))
        pos += ln
    picks = [rnd.randrange(5) for _ in rhythm]

    for bar, (root, minor) in enumerate(prog):
        b0 = bar * 16
        chord = [0, 3 if minor else 4, 7]
        for k in range(8):
            note(b0 + k * 2, 2, root + (12 if k % 2 else 0), "tri", 0.32, decay=2.0)
        for k in range(16):
            arp = root + 24 + chord[k % 3] + (12 if (k // 3) % 2 else 0)
            note(b0 + k, 1, arp, "sq", 0.045, duty=0.125, decay=4.0)
        for k in (0, 4, 8, 12) if intense else (0, 8, 10):
            kick(b0 + k)
        for k in (4, 12):
            noise(b0 + k, 0.12, 0.25, 2)
        for k in range(2, 16, 2) if not intense else range(1, 16, 2):
            noise(b0 + k, 0.03, 0.08)

    scale_tones = [0, 3, 5, 7, 10]
    for half in range(len(prog) // 2):
        root = prog[half * 2][0]
        for (p, ln, rest), pick in zip(rhythm, picks):
            if rest:
                continue
            bar = half * 2 + p // 16
            r = prog[bar][0]
            m = r + 36 + scale_tones[(pick + half) % 5]
            if root != r:
                m = r + 36 + scale_tones[pick % 5]
            note(half * 32 + p, ln, m, "sq", 0.11, duty=0.25 if intense else 0.5, decay=1.6)

    peak = max(1e-6, max(abs(v) for v in buf))
    return to_sound([v * 0.85 / peak for v in buf])


TRACKS = {
    "main": (150, [(57, True), (53, False), (48, False), (55, False)], 7),
    "city": (162, [(52, True), (52, True), (48, False), (50, False)], 21),
    "caves": (118, [(45, True), (50, True), (45, True), (52, False)], 33),
    "magma": (140, [(41, True), (41, True), (44, False), (39, False)], 44, True),
    "space": (126, [(48, False), (52, True), (45, True), (53, False)], 55),
    "bamboo": (128, [(50, True), (45, True), (48, False), (43, False)], 77),
    "boss": (172, [(52, True), (48, False), (50, True), (47, False)], 13, True),
}


class Audio:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self.tracks = {}
        self.current = None
        self._last = {}
        self._lock = threading.Lock()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 1, 512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)
            self.music_ch = pygame.mixer.Channel(0)
            self._build()
            self.ok = True
            # synthesize the rest of the soundtrack in the background so starting a
            # level or a boss fight never stalls a frame
            threading.Thread(target=self._prebuild, daemon=True).start()
        except Exception as e:  # no audio device: play silently
            print("Audio disabled:", e)

    def _build(self):
        s = {}
        s["flap"] = synth(0.08, 280, 540, "square", 0.22, duty=0.25)
        s["shoot"] = synth(0.09, 1300, 320, "square", 0.16)
        s["eshot"] = synth(0.12, 600, 200, "square", 0.14, duty=0.25)
        s["hit"] = synth(0.06, 3500, 1500, "noise", 0.3)
        s["explode"] = synth(0.4, 1400, 150, "noise", 0.45, curve=1.5)
        s["big_explode"] = mix(synth(1.0, 900, 50, "noise", 0.55, curve=1.2),
                               synth(0.6, 90, 30, "sine", 0.6))
        s["hurt"] = synth(0.3, 420, 90, "saw", 0.35)
        s["powerup"] = seq(*(synth(0.06, midi(m), None, "square", 0.22, curve=0.5)
                             for m in (72, 76, 79, 84, 88)))
        s["reflect"] = mix(synth(0.14, 1500, 2600, "square", 0.18, duty=0.25),
                           synth(0.14, 3000, 5000, "tri", 0.12))
        s["perfect"] = seq(*(synth(0.05, midi(m), None, "square", 0.22, curve=0.4)
                             for m in (84, 88, 91, 96, 100)))
        s["overheat"] = mix(synth(0.45, 160, 90, "saw", 0.28, curve=1),
                            synth(0.45, 2000, 600, "noise", 0.12))
        s["dash"] = synth(0.18, 3500, 700, "noise", 0.25, curve=1.2)
        s["shard"] = synth(0.05, 1800, 2600, "square", 0.12, duty=0.25)
        s["crystal"] = mix(synth(0.18, 2500, 1200, "tri", 0.2), synth(0.12, 6000, 3000, "noise", 0.15))
        s["clank"] = synth(0.06, 900, 700, "square", 0.12, duty=0.1)
        s["warn"] = seq(*(synth(0.18, f, f * 0.95, "square", 0.2, curve=0.3) for f in (660, 880, 660, 880)))
        s["charge"] = synth(0.5, 200, 1100, "square", 0.1, duty=0.25, curve=0.2)
        s["beam"] = mix(synth(0.4, 220, 70, "saw", 0.3, curve=1), synth(0.4, 2500, 800, "noise", 0.18))
        s["zap"] = synth(0.15, 5000, 2000, "noise", 0.25)
        s["select"] = synth(0.05, 900, 1100, "square", 0.15)
        s["combo"] = seq(synth(0.05, 988, None, "square", 0.18), synth(0.08, 1319, None, "square", 0.18))
        s["pass"] = synth(0.04, 1200, 1400, "tri", 0.12)
        s["shield_pop"] = mix(synth(0.25, 1800, 300, "tri", 0.3), synth(0.2, 4000, 1000, "noise", 0.15))
        s["gameover"] = seq(*(synth(0.18, midi(m), None, "tri", 0.3, curve=0.8) for m in (72, 67, 64, 60, 55)))
        s["boss_down"] = seq(*(synth(0.09, midi(m), None, "square", 0.22, curve=0.5)
                               for m in (72, 76, 79, 84, 79, 84, 88, 91, 96)))
        self.sounds = {k: to_sound(v) for k, v in s.items()}
        self.track("main")

    def track(self, name):
        """The looping Sound for a track, synthesizing it on first use."""
        with self._lock:
            snd = self.tracks.get(name)
            if snd is None:
                snd = self.tracks[name] = make_music(*TRACKS[name])
            return snd

    def _prebuild(self):
        for name in ["boss", *TRACKS]:
            self.track(name)

    def play(self, name, vol=1.0):
        if not self.ok or self.muted:
            return
        now = pygame.time.get_ticks()
        if now - self._last.get(name, -999) < 35:
            return
        self._last[name] = now
        snd = self.sounds.get(name)
        if snd:
            ch = snd.play()
            if ch:
                ch.set_volume(vol)

    def music(self, name):
        if not self.ok or name == self.current:
            return
        self.current = name
        self.music_ch.play(self.track(name), loops=-1, fade_ms=600)
        self.music_ch.set_volume(0 if self.muted else 0.45)

    def stop_music(self):
        if self.ok:
            self.music_ch.fadeout(600)
        self.current = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok:
            self.music_ch.set_volume(0 if self.muted else 0.45)
