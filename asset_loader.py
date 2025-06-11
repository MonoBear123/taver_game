import pygame

_asset_cache = {}

def get_asset(name: str) -> pygame.Surface:

    if name not in _asset_cache:
        path = f"assets/objects/{name}.png"
        _asset_cache[name] = pygame.image.load(path).convert_alpha()
    return _asset_cache[name]
