import json
from typing import Dict, Any, Optional, List

class RecipeManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RecipeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._recipes: Optional[Dict[str, Any]] = None
        self._load_recipes()
        self._initialized = True

    def _load_recipes(self):
        try:
            with open('assets/items/recipes.json', 'r', encoding='utf-8') as f:
                self._recipes = json.load(f).get('recipes', {})
                print(f"RecipeManager: Loaded {len(self._recipes)} recipes.")
        except FileNotFoundError:
            self._recipes = {}
        except json.JSONDecodeError:
            self._recipes = {}

    def get_all_recipes(self) -> Dict[str, Any]:
        return self._recipes or {}

    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        return self.get_all_recipes().get(recipe_id)
        
    def get_orderable_recipes(self) -> Dict[str, Any]:
        return {
            rid: rdata for rid, rdata in self.get_all_recipes().items()
            if rdata.get('type') in ['cooked', 'baking']
        }

recipe_manager = RecipeManager() 