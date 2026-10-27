"""LASER BIRD - run with:  python main.py

Tests (headless):  python -m tests.smoke   |   benchmark:  python -m tests.bench
"""
import pygame


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    from game.game import Game
    Game().run()


if __name__ == "__main__":
    main()
