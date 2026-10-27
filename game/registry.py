"""Name -> class registries, so levels can refer to enemies and bosses by key.

    @register_enemy("drone")
    class Drone(Enemy): ...

Registration happens when the defining module is imported; `game.worlds` imports
every world module, so everything is registered before the first level starts.
"""
ENEMIES = {}
BOSSES = {}


def _register(table, key):
    def deco(cls):
        if key in table and table[key] is not cls:
            raise ValueError(f"duplicate registration for {key!r}")
        table[key] = cls
        cls.key = key
        return cls
    return deco


def register_enemy(key):
    return _register(ENEMIES, key)


def register_boss(key):
    return _register(BOSSES, key)
