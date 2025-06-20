import json

class RecipeManager:
    def __init__(self):
        self._recipes = None
        self._load_recipes()

    def _load_recipes(self):
        with open('assets/items/recipes.json', 'r', encoding='utf-8') as f:
            self._recipes = json.load(f).get('recipes', {})
       

    def get_all_recipes(self):
        return self._recipes or {}

    def get_recipe(self, recipe_id):
        return self.get_all_recipes().get(recipe_id)
        
    def get_orderable_recipes(self):    
        return {
            rid: rdata for rid, rdata in self.get_all_recipes().items()
            if rdata.get('type') in ['cooked', 'baking']
        }

recipe_manager = RecipeManager() 