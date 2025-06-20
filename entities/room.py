import json
from core.game_time import game_time
from core.entity_component_system import StateComponent, ChairComponent, Leaving, CharacterStateComponent, AIControllerComponent
import random
from config import TILE_SIZE, NPC_SPAWN_MIN_CUSTOMERS, NPC_SPAWN_INTERVAL

class Room:
    def __init__(self, json_path, scene):
        self.json_path = json_path
        self.scene = scene
        self.data = self._load_json(json_path)
        self.current_level = self.data["current_level"]
        self.saved_state = self.data["saved_state"]
        self.objects = []
        self.statics = []
        self.npcs = []
        
        self.load_levels_undo()

    def load_levels_undo(self):
        self.all_objects_data = []
        for level_data in self.data["levels"]:
            if level_data["level"] <= self.current_level:
                self.all_objects_data.extend(level_data["objects"])

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_state(self):
        data = self._load_json(self.json_path)

        saved_obj_states = {}
        for obj in self.objects:
            if obj.has_component(AIControllerComponent) or obj.has_component(ChairComponent):
                continue
            
            if hasattr(obj, 'id'):
                if state_comp := obj.get_component(StateComponent):
                    saved_obj_states[obj.id] = state_comp.get_state()

        data['saved_state'] = saved_obj_states
        
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def level_up(self):
        self.save_state()
        self.current_level += 1
        self.data["current_level"] = self.current_level
        
        self.data = self._load_json(self.json_path)
        self.load_levels_undo()

        self.scene.recreate_room_objects()
        
    def get_blocking_sprites(self):
        return [obj for obj in self.objects if getattr(obj, 'is_blocking', False)] + \
               [s for s in self.statics if getattr(s, 'is_blocking', False)] + \
               [npc for npc in self.npcs if getattr(npc, 'is_blocking', False)]

    def get_interactive_sprites(self):
        from core.entity_component_system import InteractionComponent
        return [obj for obj in self.objects if obj.has_component(InteractionComponent)] + \
               [npc for npc in self.npcs if npc.has_component(InteractionComponent)]
               
    def get_drawable_sprites(self):
        return self.objects + self.npcs + self.statics

    def update(self, dt):
        for obj in self.objects:
            if hasattr(obj, 'update'):
                obj.update(dt)
        for npc in self.npcs:
            if hasattr(npc, 'update'):
                npc.update(dt)

    

class RoomManager:
    def __init__(self):
        self.rooms = {}

    def get_room(self, json_path, scene, room_class):
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
        self.orders = []
        
        self.spawn_points = []
        for obj in self.scene.tmx_data.get_layer_by_name("enteries"):
            if obj.name == "enter":
                self.spawn_points.append((obj.x, obj.y))
        
        self.spawn_timer = NPC_SPAWN_INTERVAL
        self.grid_scale = 4
        self.sub_tile_size = TILE_SIZE // self.grid_scale
        self.chairs = None
        self.grid = None

    def _initialize(self):
        if self.chairs is not None:
            return
        self.chairs = [
            obj for obj in self.objects
            if hasattr(obj, 'has_component') and obj.has_component(ChairComponent)
        ]
        
        self.grid = self.create_grid()

    def create_grid(self):
        grid_width = self.scene.tmx_data.width * self.grid_scale
        grid_height = self.scene.tmx_data.height * self.grid_scale
        grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
        blocks = self.get_blocking_sprites()
        
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

    def add_order(self, order):
        customer, item_id, recipe_id = order
        new_order = (customer, item_id, recipe_id)
        self.orders.append(new_order)

    def remove_order(self, customer):
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
        

        if free_chairs:
            return random.choice(free_chairs)
        return None

    def find_target(self, target_entity):

        center_x = target_entity.rect.centerx // self.sub_tile_size
        center_y = target_entity.rect.centery // self.sub_tile_size
        
        grid_height = len(self.grid)
        grid_width = len(self.grid[0])

        for radius in range(1, 2): 
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue

                    nx, ny = center_x + dx, center_y + dy

                    if 0 <= nx < grid_width and 0 <= ny < grid_height:
                        if self.grid[ny][nx] == 0:
                            return (nx, ny)
        return None

    def spawn_npc(self):
        if not self.spawn_points:
            return
        
        spawn_pos = random.choice(self.spawn_points)
        
        new_npc = self.scene.factory.create_guest(pos=spawn_pos)
        self.npcs.append(new_npc)

    def update(self, dt):
        super().update(dt)
        
        self.npcs = [c for c in self.npcs if c.alive()]

        if 8 <= game_time.hours < 22:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                if len(self.npcs) < NPC_SPAWN_MIN_CUSTOMERS:
                    self.spawn_npc()
                self.spawn_timer = NPC_SPAWN_INTERVAL
        else:
            for customer in self.npcs:
                state_comp = customer.get_component(CharacterStateComponent)
                if state_comp and not isinstance(state_comp.state, Leaving):
                    state_comp.set_state(Leaving(customer))
        
        for order in self.orders:
            pass


class KitchenRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
       
    

class ToiletRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
        
    

class RestRoom(Room):
    def __init__(self, json_path, scene):
        super().__init__(json_path, scene)
    
    def update(self, dt):
        super().update(dt)
    