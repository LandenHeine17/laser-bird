"""Procedural pixel art (ASCII grids -> Surfaces) and a tiny 3x5 bitmap font."""
import pygame

from .settings import PAL, SKINS

OUTLINE = PAL["K"]

BIRD_UP = [
    "WW..YYYYY....",
    "WWWYYYYYCCC..",
    ".WWYYYYCCKC..",
    "..YYYYYYYYYOO",
    ".YYYYYYYYOOOO",
    ".YYYYYYYYYRR.",
    "..YYYYYYYYY..",
    "...yyyyyyy...",
]
BIRD_DOWN = [
    "....YYYYY....",
    "..YYYYYYCCC..",
    ".YYYYYYCCKC..",
    ".YYYYYYYYYYOO",
    "WWWYYYYYYOOOO",
    "WWWWYYYYYYRR.",
    ".WWWYYYYYYY..",
    "..WW.yyyyy...",
]
DRONE_A = [
    "LLLLLLLLL",
    "....D....",
    ".DDDDDDD.",
    "DLLLLLLLD",
    "DLRRLLLLD",
    "DLLLLLLLD",
    ".DDDDDDD.",
    "..D...D..",
]
DRONE_B = ["...LLL..."] + DRONE_A[1:]
SWOOPER_A = [
    "......RRR...",
    "..RRRRRRRRR.",
    "OOWKRRRRRRRR",
    "..RRRRRRRRRR",
    "....rrrrRRR.",
    "......rr....",
]
SWOOPER_B = [
    "......RRR...",
    "..RRRRRRRRR.",
    "OOWKRRRRRRRR",
    "..RRRRrrRRRR",
    "...rrrrrRR..",
    "............",
]
BAT_A = [
    "V.........V",
    "VV..V.V..VV",
    "VVV.VVV.VVV",
    "VVVVRVRVVVV",
    ".VVVVVVVVV.",
    "....VVV....",
]
BAT_B = [
    "....V.V....",
    "...VVVVV...",
    "..VVRVRVV..",
    ".VVVVVVVVV.",
    "VVV.VVV.VVV",
    "V...VVV...V",
]
TURRET = [
    "..DDDDD..",
    ".DLLLLLD.",
    "DLLMMMLLD",
    "DLLMMMLLD",
    ".DLLLLLD.",
    "..DDDDD..",
]
HEART = [
    ".RR.RR.",
    "RWRRRRR",
    "RRRRRRR",
    ".RRRRR.",
    "..RRR..",
    "...R...",
]
SHARD = [".C.", "CWC", "CCC", ".C."]
COP_A = [
    "....BBRR....",
    "..LLLLLLLL..",
    ".LCCCLLLLLL.",
    "LLLLLLLLLLLL",
    "YLDDDDDDDDLR",
    ".DDD....DDD.",
]
COP_B = ["....RRBB...."] + COP_A[1:]
SPITTER = [
    "..G.G..",
    ".GGGGG.",
    "GGWKWGG",
    ".gGGGg.",
    "..ggg..",
]
IMP_A = [
    ".R.....R.",
    ".RR...RR.",
    "..RRRRR..",
    ".RYKRYKR.",
    "RRRRRRRRR",
    ".ORRRRRO.",
    "..O...O..",
]
IMP_B = [
    ".........",
    "RR.....RR",
    ".RRRRRRR.",
    ".RYKRYKR.",
    "RRRRRRRRR",
    ".ORRRRRO.",
    "..O...O..",
]
FISH = [
    "...OOO....",
    ".OOOOOOO..",
    "OWKOOOOOOO",
    ".OOOOOOO.O",
    "...rrr..OO",
]
UFO = [
    "....CCC....",
    "...CWCCC...",
    ".LLLLLLLLL.",
    "LLGLLGLLGLL",
    ".DDDDDDDDD.",
    "...D...D...",
]
MINE = [
    "..R.R..",
    ".DDDDD.",
    "RDLRLDR",
    ".DRWRD.",
    "RDLRLDR",
    ".DDDDD.",
    "..R.R..",
]
BABY_PANDA = [
    ".K....K.",
    "KWWWWWWK",
    "WKKWWKKW",
    "WWWKKWWW",
    ".WWWWWW.",
    "KKWWWWKK",
    "KKWWWWKK",
    ".KK..KK.",
]
PANDA_NINJA = [
    ".KK.....KK.",
    "KKKWWWWWKKK",
    ".WWWWWWWWW.",
    "RRRRRRRRRRR",
    ".WKKWWWKKW.",
    ".WKWWWWWKW.",
    "..WWWKWWW..",
    "...WWWWW...",
    "..KKWWWKK..",
    ".KKKWWWKKK.",
    "..KK...KK..",
]
RED_PANDA_A = [
    ".O.O........",
    "OOOOO.......",
    "WKOWOOOOOOO.",
    "WWOOOOOOOObO",
    ".OOOOOOOOObO",
    ".b..b..bb.b.",
]
RED_PANDA_B = RED_PANDA_A[:5] + ["..b.b..b.b.."]
CRANE_A = [
    "......WWWW....",
    ".....WWWWW....",
    "YYWRWWWWWWWWKK",
    "...WWWWWWWW...",
    "......L...L...",
    "..............",
]
CRANE_B = [
    "..............",
    "..............",
    "YYWRWWWWWWWWKK",
    "...WWWWWWWW...",
    ".....WWWWW....",
    "......WWWW....",
]
SHURIKEN = [".L.", "LWL", ".L."]
STAR = ["..Y..", ".YYY.", "YYYYY", ".YYY.", "Y...Y"]
LOCK = [".LLL.", "L...L", "L...L", "YYYYY", "YYKYY", "YYYYY"]


def from_grid(rows, palette=None, outline=True):
    pal = palette or PAL
    h = len(rows)
    w = max(len(r) for r in rows)
    pad = 1 if outline else 0
    surf = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    filled = set()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in ". ":
                surf.set_at((x + pad, y + pad), pal[ch])
                filled.add((x + pad, y + pad))
    if outline:
        for x, y in filled:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + dx, y + dy)
                if p not in filled:
                    surf.set_at(p, OUTLINE)
    return surf


class Art:
    def __init__(self):
        self.bird = []
        for sk in SKINS:
            pal = dict(PAL, Y=sk["body"], y=sk["dark"])
            self.bird.append((from_grid(BIRD_UP, pal), from_grid(BIRD_DOWN, pal)))
        self.drone = [from_grid(DRONE_A), from_grid(DRONE_B)]
        self.swooper = [from_grid(SWOOPER_A), from_grid(SWOOPER_B)]
        self.bat = [from_grid(BAT_A), from_grid(BAT_B)]
        self.turret = from_grid(TURRET)
        self.heart = from_grid(HEART)
        self.heart_empty = from_grid(HEART, dict(PAL, R=PAL["D"], W=PAL["L"]))
        self.shard = from_grid(SHARD)
        self.cop = [from_grid(COP_A), from_grid(COP_B)]
        self.spitter = from_grid(SPITTER)
        self.spitter_down = pygame.transform.flip(self.spitter, False, True)
        self.imp = [from_grid(IMP_A), from_grid(IMP_B)]
        self.fish = from_grid(FISH)
        self.ufo = from_grid(UFO)
        self.mine = from_grid(MINE)
        self.ninja = from_grid(PANDA_NINJA)
        self.redpanda = [from_grid(RED_PANDA_A), from_grid(RED_PANDA_B)]
        self.crane = [from_grid(CRANE_A), from_grid(CRANE_B)]
        self.star = from_grid(STAR)
        self.star_empty = from_grid(STAR, dict(PAL, Y=PAL["D"]))
        self.lock = from_grid(LOCK)
        self._tints = {}
        self._small = {}

    def tint(self, surf, color=(255, 255, 255)):
        """Solid-color silhouette of a sprite (for hit flashes / afterimages)."""
        key = (id(surf), color)
        s = self._tints.get(key)
        if s is None:
            s = surf.copy()
            s.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            s.fill(color + (0,), special_flags=pygame.BLEND_RGBA_ADD)
            self._tints[key] = s
        return s

    def white(self, surf):
        return self.tint(surf, (255, 255, 255))

    def small(self, surf, f=0.6):
        key = (id(surf), f)
        s = self._small.get(key)
        if s is None:
            w, h = surf.get_size()
            s = pygame.transform.scale(surf, (max(1, int(w * f)), max(1, int(h * f))))
            self._small[key] = s
        return s


# ---------------------------------------------------------------- font
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011",
    "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111",
    "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010",
    "P": "110101110100100", "Q": "010101101110011", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111",
    "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111",
    "0": "111101101101111", "1": "010110010010111", "2": "110001010100111",
    "3": "110001010001110", "4": "101101111001001", "5": "111100110001110",
    "6": "011100111101111", "7": "111001010010010", "8": "111101111101111",
    "9": "111101111001110",
    " ": "000000000000000", ".": "000000000000010", ",": "000000000010100",
    "!": "010010010000010", "?": "110001010000010", ":": "000010000010000",
    "-": "000000111000000", "+": "000010111010000", "/": "001001010100100",
    "(": "010100100100010", ")": "010001001001010", "'": "010010000000000",
    ">": "100010001010100", "<": "001010100010001", "=": "000111000111000",
    "*": "101010101000000", "%": "101001010100101",
}
_glyphs = {}


def _glyph(ch, color, scale):
    key = (ch, color, scale)
    g = _glyphs.get(key)
    if g is None:
        bits = FONT.get(ch, FONT["?"])
        g = pygame.Surface((3 * scale, 5 * scale), pygame.SRCALPHA)
        for i, b in enumerate(bits):
            if b == "1":
                g.fill(color, ((i % 3) * scale, (i // 3) * scale, scale, scale))
        _glyphs[key] = g
    return g


def text_width(s, scale=1):
    return max(0, len(s) * 4 * scale - scale)


def draw_text(surf, s, x, y, color, scale=1, shadow=OUTLINE, align="left"):
    s = str(s).upper()
    w = text_width(s, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    x, y = int(x), int(y)
    off = max(1, scale // 2)
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        cx = x + i * 4 * scale
        if shadow:
            surf.blit(_glyph(ch, shadow, scale), (cx + off, y + off))
        surf.blit(_glyph(ch, color, scale), (cx, y))
    return w
