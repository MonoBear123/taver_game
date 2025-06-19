from typing import Dict, List, Any, Optional, Tuple
import pygame
from entity_component_system import (
    Entity, SpriteComponent, CollisionComponent, ShapedCollisionComponent,
    AnimationComponent, InteractionComponent, StateComponent,
    StoveComponent, StorageComponent, ToiletComponent, BedComponent,
    TableComponent, ChairComponent, WoodComponent
)
from config import TILE_SIZE
from asset_loader import get_asset


class ObjectFactory:
    def __init__(self, scene):
        self.scene = scene
        self.tmx_data = scene.tmx_data

    def create_from_tmx_layers(self):
        layer_handlers = {
            'background': self.generate_background,
            'decorations': self.generate_decorations,
            'objects': self.generate_objects,
            'walls': self.generate_objects,
            'lighting': self.generate_lighting,
            'windows': self.generate_windows,
            'cosmetics': self.generate_cosmetics,
            'enteries': self.generate_enteries,
            'exits': self.generate_exits
        }
        for layer in self.tmx_data.layers:
            if layer.name in layer_handlers:
                layer_handlers[layer.name]()

    def create_from_room_data(self, room):
        for obj_data in room.all_objects_data:
            obj_type = obj_data.get("type")
            obj_id = obj_data.get("id")

            if any(obj.id == obj_id for obj in self.scene.interactive_sprites if hasattr(obj, 'id')):
                 continue

            saved_state = room.saved_state.get(obj_id, {})
            self.create_interactive_entity(obj_type, obj_data, saved_state)

    def create_interactive_entity(self, obj_type, obj_data, saved_state):
        position = (obj_data.get("x", 0), obj_data.get("y", 0))

        animations = None
        if "animations" in obj_data:
            animations = {}
            for anim_name, frames in obj_data["animations"].items():
                animations[anim_name] = [get_asset(frame) for frame in frames]
        
        creator_map = {
            "stove": self._create_stove, 
            "bed": self._create_bed,
            "storage": self._create_storage,
            "toilet": self._create_toilet,
            "table": self._create_table,
            "wood": self._create_wood,
            "chair": self._create_chair
        }
        
        entity = None
        if obj_type in creator_map:
            entity = creator_map[obj_type](position, animations, obj_data)
        
        if entity:
            entity.id = obj_data["id"]
            if state_comp := entity.get_component(StateComponent):
                state_comp.set_state(saved_state)
            return entity
        return None

    def _create_base_interactive(self, position, animations, is_blocking=True):
        groups = [
            self.scene.interactive_sprites, self.scene.drawn_sprites,
            self.scene.update_sprites
        ]
        if is_blocking:
            groups.append(self.scene.block_sprites)
        
        base_image = animations.get('idle', [pygame.Surface((TILE_SIZE, TILE_SIZE))])[0]
        
        entity = Entity(groups)
        entity.add_component(SpriteComponent(base_image, position, layer='interactive'))
        entity.add_component(ShapedCollisionComponent())
        if animations:
            entity.add_component(AnimationComponent(animations))
        return entity

    def _create_stove(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        stove = StoveComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(stove)
        entity.add_component(StateComponent(stove.save_state()))
        return entity

    def _create_storage(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        storage = StorageComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(storage)
        entity.add_component(StateComponent(storage.save_state()))
        return entity

    def _create_toilet(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        toilet = ToiletComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(toilet)
        entity.add_component(StateComponent(toilet.save_state()))
        return entity

    def _create_bed(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        bed = BedComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(bed)
        entity.add_component(StateComponent(bed.save_state()))
        return entity

    def _create_table(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        table = TableComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(table)
        entity.add_component(StateComponent(table.save_state()))
        return entity

    def _create_chair(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations, is_blocking=False)
        table_id = obj_data.get("properties", {}).get("table_id")
        chair = ChairComponent(table_id=table_id)
        entity.add_component(InteractionComponent())
        entity.add_component(chair)
        entity.add_component(StateComponent(chair.save_state()))
        return entity

    def _create_wood(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        wood = WoodComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(wood)
        entity.add_component(StateComponent(wood.save_state()))
        return entity

    def _create_basic_entity(self, pos, image, layer, use_collision=False, shaped_collision=False, colorkey=None):
        groups = [self.scene.drawn_sprites]
        if use_collision:
            groups.append(self.scene.block_sprites)
            groups.append(self.scene.update_sprites)
            
        entity = Entity(groups)
        sprite = SpriteComponent(image, pos, layer, colorkey)
        entity.add_component(sprite)
        if use_collision:
            entity.add_component(ShapedCollisionComponent() if shaped_collision else CollisionComponent())
        return entity
        
    def generate_background(self):
        for x, y, image in self.tmx_data.get_layer_by_name("background").tiles():
            self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'background')
    
    def generate_cosmetics(self):
        for x, y, image in self.tmx_data.get_layer_by_name("cosmetics").tiles():
            self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'objects', colorkey=(255, 255, 255))
    
    def generate_objects(self):
        layer_name = "walls" if "walls" in [layer.name for layer in self.tmx_data.layers] else "objects"
        for x, y, image in self.tmx_data.get_layer_by_name(layer_name).tiles():
            if pygame.mask.from_surface(image).count() > 0:
                self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'objects', use_collision=True, shaped_collision=True)
    
    def generate_lighting(self):
        for x, y, image in self.tmx_data.get_layer_by_name("lighting").tiles():
            self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'lighting')
    
    def generate_windows(self):
        for x, y, image in self.tmx_data.get_layer_by_name("windows").tiles():
            image.set_colorkey((255, 255, 255))
            self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'windows')
    
    def generate_decorations(self):
        for x, y, image in self.tmx_data.get_layer_by_name('decorations').tiles():
            if pygame.mask.from_surface(image).count() > 0:
                self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'decorations', use_collision=True, shaped_collision=True, colorkey=(255, 255, 255))
    
    def generate_enteries(self):
        for obj in self.tmx_data.get_layer_by_name("enteries"):
            if obj.name == self.scene.entry_point:
                self.scene.player.set_position((obj.x, obj.y))
                
    def generate_exits(self):
        for obj in self.tmx_data.get_layer_by_name("exits"):
            entity = Entity([self.scene.exit_sprites, self.scene.update_sprites])
            exit_surface = pygame.Surface((obj.width, obj.height), pygame.SRCALPHA)
            entity.add_component(SpriteComponent(exit_surface, (obj.x, obj.y)))
            entity.add_component(CollisionComponent(shrink_hitbox=False))
            entity.name = obj.name 