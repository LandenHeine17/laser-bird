"""Frame-time benchmark: a bot plays each level (god mode, standard laser) and we time
update + draw + present per frame. Run:  python -m tests.bench
"""
import random
import time

from tests import harness

from game.worlds import LEVELS


def bench(game, frames=1500):
    every = []
    for i, L in enumerate(LEVELS):
        random.seed(i)
        game.start_level(i)
        game.god = game.auto_fire = True
        game.on_flap()
        times = []
        for f in range(frames):
            p = game.player
            if p.y > getattr(game.director, "c", 85) + 4 and p.vy > -40:
                game.on_flap()
            if f == frames * 3 // 5:
                game.stage_time = L.length  # bring in the boss
            t0 = time.perf_counter()
            game.step(1 / 60)
            game.draw()
            game.present()
            times.append(time.perf_counter() - t0)
        times = sorted(times[60:])
        every += times
        print(f"{L.name:<14} avg {sum(times) / len(times) * 1000:5.2f} ms   p95 {times[int(len(times) * .95)] * 1000:5.2f} ms"
              f"   max {times[-1] * 1000:6.2f} ms")
    every.sort()
    print(f"{'ALL':<14} avg {sum(every) / len(every) * 1000:5.2f} ms   p95 {every[int(len(every) * .95)] * 1000:5.2f} ms"
          f"   (budget at 60 FPS: 16.67 ms)")


if __name__ == "__main__":
    bench(harness.make_game())
