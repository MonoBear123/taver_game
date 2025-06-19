import json
from game_time import game_time
from typing import Dict, Any, Optional, List
from entity_component_system import Entity, StateComponent, ChairComponent
from character import NPC, Guest, Leaving
import random
import pygame
from config import TILE_SIZE, NPC_SPAWN_MIN_CUSTOMERS, NPC_SPAWN_INTERVAL

class Room:
    def __init__(self, json_path: str, scene):
        self.json_path = json_path
        self.scene = scene
        self.data = self._load_json(json_path)
        self.current_level = self.data.get("current_level", 1)
        self.saved_state = self.data.get("saved_state", {})
        
        self.all_objects_data = []
        for level_data in self.data.get("levels", []):
            if level_data["level"] <= self.current_level:
                self.all_objects_data.extend(level_data.get("objects", []))

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки JSON {path}: {e}")
            return {"current_level": 1, "levels": [], "saved_state": {}}

    def save_state(self):
        state = {}
        room_object_ids = {obj_data['id'] for obj_data in self.all_objects_data}
        
        for obj in self.scene.interactive_sprites:
            if hasattr(obj, 'id') and obj.id in room_object_ids:
                if state_comp := obj.get_component(StateComponent):
                    state[obj.id] = state_comp.get_state()

        self.data["saved_state"] = state
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения состояния в {self.json_path}: {e}")

    def level_up(self):
        self.save_state()
        self.current_level += 1
        self.data["current_level"] = self.current_level
        
        self.data = self._load_json(self.json_path)
        self.all_objects_data = []
        for level_data in self.data.get("levels", []):
            if level_data["level"] <= self.current_level:
                self.all_objects_data.extend(level_data.get("objects", []))

        self.scene.recreate_room_objects()
        
    def update(self, dt: float):
        pass 

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
            return room

        room = room_class(json_path, scene)
        self.rooms[json_path] = room
        return room

    def update_all_rooms(self, dt):
        for room in self.rooms.values():
            room.update(dt)

room_manager = RoomManager()

class TavernRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
        self.customers: List[Guest] = []
        self.orders: List[tuple] = []
        
        self.spawn_points = []
        for obj in self.scene.tmx_data.get_layer_by_name("enteries"):
            if obj.name == "enter":
                self.spawn_points.append((obj.x, obj.y))
        
        self.spawn_timer = NPC_SPAWN_INTERVAL
        self.grid_scale = 2
        self.sub_tile_size = TILE_SIZE // self.grid_scale
        self.chairs = None
        self.grid = None

    def _initialize(self):
        if self.chairs is not None:
            return
        self.chairs = [
            obj for obj in self.scene.interactive_sprites 
            if hasattr(obj, 'has_component') and obj.has_component(ChairComponent)
        ]
        
        self.grid = self.create_grid()

    def create_grid(self):
        grid_width = self.scene.tmx_data.width * self.grid_scale
        grid_height = self.scene.tmx_data.height * self.grid_scale
        grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
        
        blocks = [sprite for sprite in self.scene.block_sprites if hasattr(sprite, 'has_component')]
        
        for sprite in blocks:
            box = sprite.hitbox
            start_x = box.left // self.sub_tile_size
            end_x = box.right // self.sub_tile_size
            start_y = box.top // self.sub_tile_size
            end_y = box.bottom // self.sub_tile_size

            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    if 0 <= y < grid_height and 0 <= x < grid_width:
                        grid[y][x] = 1
        print(self.chairs)
        for sprite in self.chairs:
            box = sprite.hitbox
            start_x = box.left // self.sub_tile_size
            end_x = box.right // self.sub_tile_size
            start_y = box.top // self.sub_tile_size
            end_y = box.bottom // self.sub_tile_size

            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    if 0 <= y < grid_height and 0 <= x < grid_width:
                        grid[y][x] = 1

        return grid

    def add_order(self, customer: Guest, item_id: str, recipe_id: str):
        new_order = (customer, item_id, recipe_id)
        self.orders.append(new_order)
        customer.order = new_order 

    def remove_order(self, customer: Guest):
        order_to_remove = next((order for order in self.orders if order[0] == customer), None)
        if order_to_remove:
            self.orders.remove(order_to_remove)
            customer.order = None

    def get_free_chair(self):
        self._initialize()

        self.free_chairs = free_chairs = [
            chair for chair in self.chairs 
            if chair.get_component(ChairComponent) and not chair.get_component(ChairComponent).is_occupied
        ]
        print(free_chairs)
        if free_chairs:
            return random.choice(free_chairs)
        return None

    def spawn_npc(self):
        if not self.spawn_points:
            return
        
        spawn_pos = random.choice(self.spawn_points)
        
        npc_scene = self.scene 
        
        active_scene = self.scene.game.get_current_state()
        groups = [active_scene.update_sprites, active_scene.drawn_sprites, active_scene.interactive_sprites]

        new_npc = Guest(
            game=self.scene.game, 
            scene=npc_scene, 
            groups=groups, 
            pos=spawn_pos, 
            z='characters', 
            name='guest' 
        )
        self.customers.append(new_npc)

    def update(self, dt):
        super().update(dt)
        
        self.customers = [c for c in self.customers if c.alive()]

        if 8 <= game_time.hours < 22:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                if len(self.customers) < NPC_SPAWN_MIN_CUSTOMERS:
                    self.spawn_npc()
                self.spawn_timer = NPC_SPAWN_INTERVAL
        else:
            for customer in self.customers:
                if not isinstance(customer.state, Leaving):
                    customer.set_state(Leaving(customer))
        
        for order in self.orders:
            pass

    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class KitchenRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
       
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class ToiletRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
        
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass

class RestRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
    
    def handle_event(self, event):
        pass
    
    def room_specific_logic(self):
        pass