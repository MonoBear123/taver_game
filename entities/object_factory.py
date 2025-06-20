from typing import Dict, List, Any, Optional, Tuple
import pygame
from core.entity_component_system import (
    Entity, SpriteComponent, CollisionComponent, ShapedCollisionComponent,
    AnimationComponent, InteractionComponent, StateComponent,
    StoveComponent, StorageComponent, ToiletComponent, BedComponent,
    TableComponent, ChairComponent, WoodComponent, PlayerControllerComponent,
    CharacterStateComponent, Idle, CharacterMovementComponent, AIControllerComponent, 
    WaitingForFood, Eating, PlayerStatsComponent, ThoughtBubbleComponent
)
from config import *
from items.inventory import Inventory
from utils.asset_loader import asset_loader


class InteractionSystem:
    def __init__(self, scene):
        self.scene = scene

    def get_nearest_interactive_object(self, position):
        interactive_sprites = self.scene.room.get_interactive_sprites()
        if not interactive_sprites:
            return None

        try:
            return min(
                interactive_sprites,
                key=lambda obj: pygame.math.Vector2(position).distance_to(obj.rect.center)
            )
        except ValueError:
            return None

    def interact_with_nearest(self, player_entity):
        nearest_obj = self.get_nearest_interactive_object(player_entity.rect.center)
        if not nearest_obj:
            return

        interaction_distance = TILE_SIZE * INTERACTION_DISTANCE
        distance = pygame.math.Vector2(player_entity.rect.center).distance_to(nearest_obj.rect.center)

        if distance < interaction_distance:
            if hasattr(nearest_obj, 'interact'):
                nearest_obj.interact(player_entity)


class ObjectFactory:
    
        
    def __init__(self, scene):
        self.scene = scene
        self.tmx_data = scene.tmx_data
        self.guest_counter = 0

    def create_player(self):
        pos = (0, 0) 
        
        animations = asset_loader.get_animations('assets/characters/player', size=CHARACTER_SPRITE_SIZE)
        initial_image = animations['idle_down'][0]

        player_entity = Entity()
        player_entity.scene = self.scene
        
        player_entity.add_component(SpriteComponent(initial_image, pos, layer='characters'))
        player_entity.add_component(AnimationComponent(animations))
        
        collision_comp = CollisionComponent(shrink_hitbox=True)
        player_entity.add_component(collision_comp)
        
        player_entity.add_component(PlayerControllerComponent())
        player_entity.add_component(CharacterMovementComponent(SPEED, FORCE, FRICTION))
        player_entity.add_component(CharacterStateComponent(initial_state_class=Idle))
        player_entity.add_component(PlayerStatsComponent())
        
        player_entity.inventory = Inventory(size=(5, 4), inventory_type='player')
        player_entity.interaction_system = InteractionSystem(self.scene)
        
        if 'inventory' in PLAYER_STATE:
            player_entity.inventory.from_dict(PLAYER_STATE.get('inventory'))

        if PLAYER_STATE and PLAYER_STATE.get('last_scene') == self.scene.current_scene:
            player_entity.position = (PLAYER_STATE.get('x', 0), PLAYER_STATE.get('y', 0))
            if collision_comp.hitbox:
                collision_comp.hitbox.center = player_entity.rect.center
            if stats_comp := player_entity.get_component(PlayerStatsComponent):
                stats_comp.load_state(PLAYER_STATE)

        def save_state_func():
            PLAYER_STATE['x'] = player_entity.rect.x
            PLAYER_STATE['y'] = player_entity.rect.y
            PLAYER_STATE['inventory'] = player_entity.inventory.to_dict()
            PLAYER_STATE['last_scene'] = self.scene.current_scene
            if stats_comp := player_entity.get_component(PlayerStatsComponent):
                PLAYER_STATE.update(stats_comp.save_state())
        
        player_entity.save_state = save_state_func

        return player_entity

    def create_guest(self, pos, animations_path='assets/characters/guest'):
        animations = asset_loader.get_animations(animations_path, size=CHARACTER_SPRITE_SIZE)
        initial_image = animations['idle_down'][0]

        guest_entity = Entity()
        guest_entity.scene = self.scene
        guest_entity.id = f"guest_{self.guest_counter}"
        self.guest_counter += 1

        guest_entity.add_component(SpriteComponent(initial_image, pos, layer='characters'))
        guest_entity.add_component(AnimationComponent(animations))
        guest_entity.add_component(CollisionComponent(shrink_hitbox=True))
        guest_entity.add_component(InteractionComponent(text="Отдать блюдо"))
        guest_entity.add_component(CharacterMovementComponent(NPC_SPEED, NPC_FORCE, NPC_FRICTION))
        guest_entity.add_component(AIControllerComponent())
        guest_entity.add_component(CharacterStateComponent(initial_state_class=Idle))
        guest_entity.add_component(StateComponent())
        guest_entity.add_component(ThoughtBubbleComponent())

        guest_entity.order = None
        guest_entity.target = None
        guest_entity.is_blocking = False

        self.scene.drawn_sprites.add(guest_entity)

        return guest_entity

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

    def create_from_room_data(self):
        room = self.scene.room
        for obj_data in room.all_objects_data:
            obj_type = obj_data.get("type")
            obj_id = obj_data.get("id")

            if any(obj.id == obj_id for obj in room.objects if hasattr(obj, 'id')):
                 continue

            saved_state = room.saved_state.get(obj_id, {})
            entity = self.create_interactive_entity(obj_type, obj_data, saved_state)
            if entity:
                room.objects.append(entity)

    def create_interactive_entity(self, obj_type, obj_data, saved_state):
        position = (obj_data.get("x", 0), obj_data.get("y", 0))

        animations = None
        if "animations" in obj_data:
            animations = {}
            for anim_name, frames in obj_data["animations"].items():
                animations[anim_name] = [asset_loader.get_image(frame) for frame in frames]
        
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
        base_image = animations.get('idle', [pygame.Surface((TILE_SIZE, TILE_SIZE))])[0]
        
        entity = Entity()
        entity.is_blocking = is_blocking
        entity.add_component(SpriteComponent(base_image, position, layer='interactive'))
        entity.add_component(ShapedCollisionComponent())
        if animations:
            entity.add_component(AnimationComponent(animations))
        return entity

    def _create_stove(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        entity.add_component(InteractionComponent())
        entity.add_component(StoveComponent())
        entity.add_component(StateComponent())
        return entity

    def _create_storage(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        storage = StorageComponent()
        entity.add_component(InteractionComponent())
        entity.add_component(storage)
        entity.add_component(StateComponent())
        return entity

    def _create_toilet(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        entity.add_component(InteractionComponent())
        entity.add_component(ToiletComponent())
        entity.add_component(StateComponent())
        return entity

    def _create_bed(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        entity.add_component(InteractionComponent())
        entity.add_component(BedComponent())
        entity.add_component(StateComponent())
        return entity

    def _create_table(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        entity.add_component(InteractionComponent())
        entity.add_component(TableComponent())
        entity.add_component(StateComponent())
        return entity

    def _create_chair(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations, is_blocking=False)
        table_id = obj_data.get("properties", {}).get("table_id")
        entity.add_component(InteractionComponent())
        entity.add_component(ChairComponent(table_id=table_id))
        entity.add_component(StateComponent())
        return entity

    def _create_wood(self, position, animations, obj_data):
        entity = self._create_base_interactive(position, animations)
        entity.add_component(InteractionComponent())
        entity.add_component(WoodComponent())
        entity.add_component(StateComponent())
        return entity

    def _create_basic_entity(self, pos, image, layer, use_collision=False, shaped_collision=False, colorkey=None):
        entity = Entity()
        entity.is_blocking = use_collision
        sprite = SpriteComponent(image, pos, layer, colorkey)
        entity.add_component(sprite)
        if use_collision:
            entity.add_component(ShapedCollisionComponent() if shaped_collision else CollisionComponent())
        return entity
        
    def generate_background(self):
        for x, y, image in self.tmx_data.get_layer_by_name("background").tiles():
            entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'background')
            self.scene.room.statics.append(entity)
    
    def generate_cosmetics(self):
        for x, y, image in self.tmx_data.get_layer_by_name("cosmetics").tiles():
            entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'objects', colorkey=(255, 255, 255))
            self.scene.room.statics.append(entity)
    
    def generate_objects(self):
        layer_name = "walls" if "walls" in [layer.name for layer in self.tmx_data.layers] else "objects"
        for x, y, image in self.tmx_data.get_layer_by_name(layer_name).tiles():
            if pygame.mask.from_surface(image).count() > 0:
                entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'objects', use_collision=True, shaped_collision=True)
                self.scene.room.statics.append(entity)
    
    def generate_lighting(self):
        for x, y, image in self.tmx_data.get_layer_by_name("lighting").tiles():
            entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'lighting')
            self.scene.room.statics.append(entity)
    
    def generate_windows(self):
        for x, y, image in self.tmx_data.get_layer_by_name("windows").tiles():
            image.set_colorkey((255, 255, 255))
            entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'windows')
            self.scene.room.statics.append(entity)
    
    def generate_decorations(self):
        for x, y, image in self.tmx_data.get_layer_by_name('decorations').tiles():
            if pygame.mask.from_surface(image).count() > 0:
                entity = self._create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'decorations', use_collision=True, shaped_collision=True, colorkey=(255, 255, 255))
                self.scene.room.statics.append(entity)
    
    def generate_enteries(self):
        for obj in self.tmx_data.get_layer_by_name("enteries"):
            if obj.name == self.scene.entry_point:
                self.scene.player.position = (obj.x, obj.y)
                if self.scene.player.hitbox:
                    self.scene.player.hitbox.center = self.scene.player.rect.center
                
    def generate_exits(self):
        for obj in self.tmx_data.get_layer_by_name("exits"):
            entity = Entity([self.scene.exit_sprites])
            exit_surface = pygame.Surface((obj.width, obj.height), pygame.SRCALPHA)
            entity.add_component(SpriteComponent(exit_surface, (obj.x, obj.y)))
            entity.add_component(CollisionComponent(shrink_hitbox=False))
            entity.name = obj.name
