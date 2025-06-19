import os
import json
from typing import Dict, Tuple, Optional
import pygame
from slot import InventorySlot
from item_manager import item_manager

_sprite_cache: Dict[Tuple[str, Tuple[int, int]], pygame.Surface] = {}


def _find_sprite_path(item_id: str) -> Optional[str]:
    item_data = item_manager.get_item_data(item_id)
    if item_data and (sprite_name := item_data.get('sprite')):
        if not sprite_name.endswith('.png'):
            sprite_name += '.png'
        return os.path.join('assets/items', sprite_name)
    return None


def get_item_sprite(item_id: str, size: int = 32) -> Optional[pygame.Surface]:
    if isinstance(size, int):
        size = (size, size)
    key = (item_id, size)
    if key in _sprite_cache:
        return _sprite_cache[key]

    path = _find_sprite_path(item_id)
    if path is None:
        return None

    try:
        surf = pygame.image.load(path).convert_alpha()
    except Exception as e:
        print(f"[item_renderer] Не удалось загрузить '{path}': {e}")
        return None

    if surf.get_size() != size:
        surf = pygame.transform.smoothscale(surf, size)

    _sprite_cache[key] = surf
    return surf


def draw_item(surface: pygame.Surface, 
              item_slot: 'InventorySlot', 
              rect: pygame.Rect,
              font: pygame.font.Font,
              is_ghost: bool = False):
    if not item_slot or item_slot.is_empty():
        return

    sprite = get_item_sprite(item_slot.item_id)
    if not sprite:
        return

    scaled_sprite = pygame.transform.scale(sprite, (rect.width, rect.height))
    
    if is_ghost:
        scaled_sprite.set_alpha(100)  
    else:
        scaled_sprite.set_alpha(255)  

    surface.blit(scaled_sprite, rect.topleft)

    if item_slot.amount > 1:
        text = font.render(str(item_slot.amount), True, (255, 255, 255))
        text_rect = text.get_rect(bottomright=(rect.right - 2, rect.bottom - 2))
        surface.blit(text, text_rect) 