import json
from typing import Dict, Any, List
from entity_component_system import *
from asset_loader import get_asset
class Room:
    def __init__(self, json_path, scene):
        self.json_path = json_path
        self.scene = scene
        self.objects = []
        self.data = self.load_json(json_path)
        self.current_level = self.data.get("current_level", 1)
        self.saved_state = self.data.get("saved_state", {})
        
        self.level_data = next(lvl for lvl in self.data["levels"] 
                         if lvl["level"] == self.current_level)
        
        self.previous_levels_data = [
            lvl for lvl in self.data["levels"] 
            if lvl["level"] < self.current_level
        ]
        
        self.create_level_objects()
    
    def load_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки JSON: {e}")
            return {}
    
    def create_level_objects(self):
        # Загружаем объекты из предыдущих уровней
        for level in self.previous_levels_data:
            self._load_level_objects(level)
        
        self._load_level_objects(self.level_data)
    
    def _load_level_objects(self, level_data: Dict[str, Any]):
        for obj_data in level_data.get("objects", []):
            obj_type = obj_data["type"]
            obj_id = obj_data["id"]
            
            if any(obj.id == obj_id for obj in self.objects if hasattr(obj, 'id')):
                continue
            
            saved_state = self.saved_state.get(obj_id, {})
            
            obj = self.create_object(obj_type, obj_data, saved_state)
            
            self.objects.append(obj)
            
    
    def create_object(self, obj_type: str, obj_data: Dict[str, Any], state: Dict[str, Any]) -> Optional[Entity]:
        position = (obj_data.get("x", 0), obj_data.get("y", 0))
        
        groups = [
            self.scene.interactive_sprites,
            self.scene.drawn_sprites,
            self.scene.update_sprites,
            self.scene.block_sprites
        ]
        
        animations = None
        if "animations" in obj_data:
            animations = {}
            for anim_name, frames in obj_data["animations"].items():
                animations[anim_name] = [get_asset(frame) for frame in frames]
        
        entity = None
        if obj_type == "stove":
            entity = create_stove(groups, position, animations)
        elif obj_type == "bed":
            entity = create_bed(groups, position, animations)
        elif obj_type == "storage":
            entity = create_storage(groups, position, animations)
            if 'items' in state:
                entity.get_component(StorageComponent).items = state['items']
        elif obj_type == "toilet":
            entity = create_toilet(groups, position, animations)
        elif obj_type == "table":
            entity = create_table(groups, position, animations)
        
        if entity:
            entity.id = obj_data["id"]
            if state_comp := entity.get_component(StateComponent):
                state_comp.set_state(state)
        else:
            print(f"Ошибка: не удалось создать объект типа {obj_type}")
        
        return entity
    
    def save_state(self):
        state = {}
        for obj in self.objects:
            if hasattr(obj, 'id') and (state_comp := obj.get_component(StateComponent)):
                state[obj.id] = state_comp.get_state()
        
        self.data["saved_state"] = state
        with open(self.json_path, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def level_up(self):
        self.save_state()
        self.current_level += 1
        self.data["current_level"] = self.current_level
        with open(self.json_path, 'w') as f:
            json.dump(self.data, f, indent=4)
        self.load_json(self.json_path)
        self.create_level_objects()
    
    def update(self, dt):
        for obj in self.objects:
            obj.update(dt)
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class TavernRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
        self.customers = []
        self.orders = []
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class KitchenRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class ToiletRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass