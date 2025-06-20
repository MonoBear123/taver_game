import json
import pygame
import os
from utils.asset_loader import asset_loader

class ItemManager:
    

    def __init__(self):
        
        self._items = None
        self._load_items()
     

    def _load_items(self):
        with open('assets/items/items_data.json', 'r', encoding='utf-8') as f:
            self._items = json.load(f)

    def get_sprite(self, item_id, size = (32, 32)):
        if not item_id:
            return None
        
        item_data = self.get_item_data(item_id)
        if not item_data or 'sprite' not in item_data:
            return None

        sprite_name = item_data['sprite']
        return asset_loader.get_item_image(sprite_name, size)
        

    def get_all_items(self):
        return self._items or {}

    def get_item_data(self, item_id):
        for category in self.get_all_items().values():
            if isinstance(category, dict) and 'items' in category and item_id in category['items']:
                item_info = category['items'][item_id]
                if isinstance(item_info, str):
                    return {'sprite': item_info}
                return item_info
        return None

item_manager = ItemManager() 