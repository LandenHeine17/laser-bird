# LASER BIRD

A retro pixel-art flappy shooter with five worlds, each with its own bosses, enemies and terrain. You flap, blast enemies with your laser, and dash into enemy fire to send it back. All the art, sound effects and chiptune music are generated in code, so there are no asset files.

## Run

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Modes

- **Adventure** has 5 levels. Each one gets harder until a boss appears at the end. Clear a level to unlock the next one. You earn up to 3 stars per level based on score, plus a FLAWLESS badge if you take no hits.
- **Endless** loops through all five worlds back to back and keeps your score and hearts between them. Each full loop gets harder.

## Tokens and the shop (the grind)

The bird starts out weak: slow fire, lots of heat, and a long dash cooldown. The way to get stronger is the **Shop**, which you can open from the main menu, from level select (E), or after any run (E).

**Earning tokens:**

- Every shard you collect turns into tokens when a run ends, even if you die. Later worlds pay more per shard.
- Clearing a level pays a bonus, more for stars and for a FLAWLESS run.
- Each level also pays a big **first-clear bonus**.

**Upgrades** go up to 10 levels, and each level costs about 45% more than the last. The shop shows exactly what the next level gives you ("2.1S > 1.9S"), plus your overall **Bird Rank**.

| Upgrade | Effect | Levels |
|---|---|---|
| Damage | +0.3x laser damage per level | 10 |
| Fire Rate | Shorter time between shots | 10 |
| Cooling | Less heat per shot, faster cooldown | 10 |
| Dash Core | Shorter dash cooldown, wider reflect | 10 |
| Extra Heart | +1 max heart | 3 |
| Token Boost | +12% tokens from every run | 8 |
| Shard Magnet | Pull shards from farther away | 5 |
| Lucky Drops | Enemies drop power-ups more often | 5 |
| Power Time | Power-ups last longer | 5 |
| Combo Keeper | More time before your combo drops | 4 |
| Start Shield | Begin every level with a shield | 1 |
| Second Wind | Survive one knockout per run | 1 |

**Lasers** are bought once and can be swapped any time:

- **Twin** fires two parallel beams.
- **Piercer** goes through up to 3 enemies.
- **Seeker** homes in on targets.
- **Scatter** fires 5 short-range pellets.
- **Plasma** is a slow orb with splash damage.

Heavier lasers build more heat.

**Difficulty:** Sunset Hills is gentle. From then on, enemies get tougher in each world: they take 1.5x as many hits in Neon City, rising to 4.4x in Deep Space. You'll need upgrades to keep going.

**Beating a boss ends the danger.** The instant the killing blow lands, you're untouchable for the rest of the level. The bird glides to safety while the boss explodes.

## The worlds

| # | World | Terrain | Enemies | Boss |
|---|---|---|---|---|
| 1 | Sunset Hills | Crystal and armored pillars, laser gates, turrets | Drones, Swoopers, Mirror Bats | **Prism Owl** |
| 2 | Neon City | Skyscrapers, hanging neon signs (shootable), oncoming hover-car traffic, searchlights | Drones, Hover Cops, Swoopers | **Neon Serpent** |
| 3 | Crystal Caves | A twisting tunnel, falling stalactites, crystal clusters | Mirror Bats, Crystal Spitters | **Geode Golem** |
| 4 | Magma Depths | Lava floor, erupting geysers, basalt spires, meteors | Fire Imps, Lava Fish | **Lava Leviathan** |
| 5 | Deep Space | Low gravity, asteroids that split, black holes, spinning satellite debris | UFOs, Space Mines | **The Mothership** |

**Secret level: Bamboo Grove.** Click the tiny bamboo leaf in the bottom-left corner of the main menu to find it. Pressing Down past QUIT also selects it.

- A misty bamboo forest with a distant pagoda, falling leaves and baby pandas munching bamboo.
- **Terrain:** bamboo bundles you can chop apart with your laser, mossy stone spires, and sharpened bamboo spikes that burst from the ground after a rustle.
- **Enemies:**
  - Ninja Pandas that ride little clouds and throw shuriken fans.
  - Red Pandas that dash in after a "!" warning.
  - Cranes that glide in waves and flick feathers.
- **Boss: the GRANDMASTER PANDA**, meditating on a cloud.
  - Attacks: shuriken fans, bamboo-spike strikes, leaf-storm spirals, ninja summons and staff-laser sweeps (with the usual SAFE zone).
  - Hit the jade amulet for crits. The bamboo staff blocks shots.

Some world-specific details:

- **Neon City:** if a searchlight catches you, it calls in Hover Cops.
- **Deep Space:** UFOs have tractor beams that pull you up. Black holes pull you in and bend lasers, both yours and enemy bolts.

**Sweeping boss lasers** always skip a **SAFE** zone. It flashes green during the warning, and the boss holds still for the whole sweep. The Mothership's laser curtains also leave one gap, marked with `SAFE >`.

## Controls

| Action | Keyboard | Mouse | Gamepad |
|---|---|---|---|
| Flap | Space / W / Up | Left click | A |
| Laser (hold) | J / F / X | Right click | X / RB / RT |
| Reflect-dash | K / Shift / S / Down | Middle click | B / LB |
| Pause (R restart, Q quit) | P / Esc | | Start |
| Menus | Arrows / WASD, Enter, Esc | Left click | D-pad, A, B |
| Fullscreen / Mute | F11 / M | | |

## Core mechanics

- **Heat gauge**: holding fire builds heat. If it fills, your laser locks for a moment, so fire in bursts.
- **Reflect-dash**: a quick dash that makes you invulnerable for its duration.
  - Enemy bolts you dash into fly back at the nearest enemy.
  - Dash just as a bolt reaches you to get a **PERFECT** reflect, which triggers slow-mo and bonus points.
  - Dashing through a firing beam scores **PHASED!**
  - Dashing into small enemies rams and destroys them. Dashing into breakable blocks smashes them.
- **Combo multiplier** up to x8. It grows with kills, pillars passed, reflects, pickups and **CLOSE!** near-misses.
- **Boss weak points**:
  - The Owl's gem, the Serpent's eye, the Golem's core, the Leviathan's eye and the Mothership's hatch all take critical damage.
  - Armored parts block your shots: the Serpent's body, the Golem's crystal shields and the Mothership's hull.
  - Reflected bolts hit bosses for 4x damage.
- **Power-ups**: Spread Shot, Mega Beam, Chill (no heat), Shard Magnet, Tiny Bird, Shield Bubble, Extra Heart.
- **Skins** unlock as your lifetime shard total grows.

Your progress is saved to `save.json`.

## Code layout

```
main.py             entry point
game/
  game.py           app shell: window, main loop, input, state machine, drawing
  run.py            a play session: setup, scoring, firing, boss flow, rewards
  combat.py         collisions and damage
  menus.py          every menu screen (key handler + draw function per screen)
  hud.py            in-game HUD
  worlds/           one self-contained module per world
    __init__.py       LEVELS, in play order
    hills.py  city.py  caves.py  magma.py  space.py  bamboo.py
  levels.py         LevelDef: the settings record for a level
  director.py       base class for the per-world spawners
  obstacles.py      Obstacle / Part base types, block materials, shared obstacles
  enemies.py        Enemy base + enemies shared by several worlds
  bosses.py         Boss base: hit zones, phases, attack rotation, safe sweeps
  registry.py       name -> class tables for enemies and bosses
  weapons.py        laser firing patterns
  progression.py    shop upgrades, laser types, purchases
  lasers.py  player.py  powerups.py  effects.py  world.py  sprites.py  audio.py
  util.py           shared color / math helpers and cached overlays
  settings.py       tuning constants, power-ups, skins
tests/
  smoke.py          headless bot playthrough of everything
  bench.py          frame-time benchmark for every level
```

## Adding content

Each world is one file in `game/worlds/`. To add a new world:

1. Copy a world module, for example `hills.py`.
2. Give it a `BIOME` dict, a background painter (`@register_backdrop("style")`), a `Director` subclass, its enemies (`@register_enemy("key")`), a boss (`@register_boss("key")`) and a `LEVEL = LevelDef(...)`.
3. Add it to the `LEVELS` list in `game/worlds/__init__.py`. Secret worlds go last.

Smaller additions:

- **New laser:** add a pattern function in `weapons.py` and a row in `progression.LASERS`.
- **New breakable material:** call `register_block(name, colors, hp, decor)`.
- **New menu screen:** add a key handler to `menus.KEY_HANDLERS` and a draw function to `menus.SCREENS`.

## Tests

```sh
.venv/bin/python -m tests.smoke   # bot plays everything headless; never touches save.json
.venv/bin/python -m tests.bench   # per-level frame times (60 FPS budget = 16.7 ms)
```

The smoke test goes through the menus and buys everything in the shop. It then beats all 6 levels and their bosses with a different laser on each, plays a stage of Endless, and dies on purpose.
