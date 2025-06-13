import json
from game_time import GameTimeManager
from asset_loader import get_asset
from typing import Dict, Any, Optional, List
from entity_component_system import Entity, create_stove, create_bed, create_storage, create_toilet, create_table, create_wood, StateComponent

class Room:
    def __init__(self, json_path: str, scene):
        self.json_path = json_path
        self.scene = scene
        self.objects: List[Entity] = []
        self.data = self.load_json(json_path)
        self.current_level = self.data.get("current_level", 1)
        self.saved_state = self.data.get("saved_state", {})

        self.level_data = next((lvl for lvl in self.data.get("levels", []) 
                               if lvl["level"] == self.current_level), None)
        if not self.level_data:
            print(f"Ошибка: уровень {self.current_level} не найден в {json_path}")
            self.level_data = {"level": self.current_level, "objects": []}

        self.previous_levels_data = [
            lvl for lvl in self.data.get("levels", []) 
            if lvl["level"] < self.current_level
        ]

        self.create_level_objects()

    def load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Загружен JSON: {path}")
                return data
        except Exception as e:
            print(f"Ошибка загрузки JSON {path}: {e}")
            return {"current_level": 1, "levels": [], "saved_state": {}}

    def create_level_objects(self):
        self.objects.clear()

        for level in self.previous_levels_data:
            self._load_level_objects(level)

        self._load_level_objects(self.level_data)


    def _load_level_objects(self, level_data: Dict[str, Any]):
        for obj_data in level_data.get("objects", []):
            obj_type = obj_data.get("type")
            obj_id = obj_data.get("id")

            if any(obj.id == obj_id for obj in self.objects if hasattr(obj, 'id')):
                continue

            saved_state = self.saved_state.get(obj_id, {})
            obj = self.create_object(obj_type, obj_data, saved_state)
            if obj:
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
        elif obj_type == "toilet":
            entity = create_toilet(groups, position, animations)
        elif obj_type == "table":
            entity = create_table(groups, position, animations)
        elif obj_type == "wood":
            entity = create_wood(groups, position, animations)

        if entity:
            entity.id = obj_data["id"]
            if state_comp := entity.get_component(StateComponent):
                state_comp.set_state(state)
            else:
                print(f"Предупреждение: объект {obj_type} с ID {entity.id} не имеет StateComponent")
        else:
            print(f"Ошибка: не удалось создать объект типа {obj_type}")

        return entity

    def save_state(self):
        state = {}
        for obj in self.objects:
            if hasattr(obj, 'id') and (state_comp := obj.get_component(StateComponent)):
                state[obj.id] = state_comp.get_state()
        self.data["saved_state"] = state
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            print(f"Состояние сохранено в {self.json_path}: {state}")
        except Exception as e:
            print(f"Ошибка сохранения состояния в {self.json_path}: {e}")

    def level_up(self):
        self.save_state()
        self.current_level += 1
        self.data["current_level"] = self.current_level
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
            self.data = self.load_json(self.json_path)
            self.level_data = next((lvl for lvl in self.data.get("levels", []) 
                                   if lvl["level"] == self.current_level), {"level": self.current_level, "objects": []})
            self.previous_levels_data = [
                lvl for lvl in self.data.get("levels", []) 
                if lvl["level"] < self.current_level
            ]
            self.create_level_objects()
            print(f"Уровень повышен до {self.current_level}")
        except Exception as e:
            print(f"Ошибка повышения уровня: {e}")

    def update(self, dt: float, game_time: 'GameTimeManager'):
        for obj in self.objects:
            obj.update(dt, game_time)

    def handle_event(self, event):
        pass

    def room_specific_logic(self):
        pass
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def get_room(self, json_path: str, scene, room_class: type) -> Room:
        if json_path in self.rooms:
            room = self.rooms[json_path]
            room.scene = scene 
            room.create_level_objects()
            return room

        room = room_class(json_path, scene)
        self.rooms[json_path] = room
        return room

    def update_all_rooms(self, dt, game_time):
        for room in self.rooms.values():
            room.update(dt, game_time)

class TavernRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
        self.customers = []
        self.orders = []
    
    def update(self, dt, game_time):
        super().update(dt, game_time)
        if 8 <= game_time.hours < 20:
            if not self.customers:
                self.customers.append({"id": "customer1"}) 
        else:
            self.customers.clear()  
        for order in self.orders:
            pass

    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class KitchenRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt, game_time):
        super().update(dt, game_time)
        if 6 <= game_time.hours < 12:
            for obj in self.objects:
                if obj.id == "stove":
                    print(f"[{game_time.get_time_string()}] Плита активна")
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class ToiletRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt, game_time):
        super().update(dt, game_time)
        # Пример: туалет доступен в любое время
        pass
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class RestRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt, game_time):
        super().update(dt, game_time)
        # Пример: восстановление энергии игрока ночью
        if 22 <= game_time.hours or game_time.hours < 6:
            if self.scene.player in self.objects:
                self.scene.player.rest(dt * 10)  # Ускоренное восстановление
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass