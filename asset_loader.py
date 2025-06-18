import pygame
import os

_asset_cache = {}

def get_asset(path: str) -> pygame.Surface:
    if path not in _asset_cache:
        if not os.path.sep in path and not path.endswith('.png'):
            full_path = os.path.join('assets', 'objects', f'{path}.png')
        else:
            full_path = path

        _asset_cache[path] = pygame.image.load(full_path).convert_alpha()
        
    return _asset_cache[path]
