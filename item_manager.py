import json
from typing import Dict, Any, Optional

class ItemManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ItemManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._items: Optional[Dict[str, Any]] = None
        self._load_items()
        self._initialized = True

    def _load_items(self):
        try:
            with open('assets/items/items_data.json', 'r', encoding='utf-8') as f:
                self._items = json.load(f)
                print(f"ItemManager: Loaded item data.")
        except FileNotFoundError:
            print("ItemManager: Error - items_data.json not found.")
            self._items = {}
        except json.JSONDecodeError:
            print("ItemManager: Error - Failed to parse items_data.json.")
            self._items = {}

    def get_all_items(self) -> Dict[str, Any]:
        """Возвращает словарь со всеми данными предметов."""
        return self._items or {}

    def get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает данные конкретного предмета по его ID."""
        for category in self.get_all_items().values():
            if isinstance(category, dict) and 'items' in category and item_id in category['items']:
                item_info = category['items'][item_id]
                if isinstance(item_info, str):
                    return {'sprite': item_info}
                return item_info
        return None

item_manager = ItemManager() 