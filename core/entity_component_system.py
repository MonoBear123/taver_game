from typing import Optional
import pygame
import pygame.mask
from core.game_time import game_time
from cooking.stove import StoveInterface
from items.slot import InventorySlot
from ui.drag_manager import drag_manager
from items.inventory import Inventory
from cooking.recipe_manager import recipe_manager
from config import *
import random
from utils.pathfinding import astar


class Component:
    def __init__(self):
        self.entity = None
        self.requires_game_time = False
    
    def on_add(self, entity):
        self.entity = entity
    
    def update(self, dt):
        pass

class SpriteComponent(Component):
    def __init__(self, image, pos, layer = 'objects', colorkey = None):
        super().__init__()
        self.image = image
        self.layer = layer
        if colorkey is not None:
            self.image.set_colorkey(colorkey)
            temp = pygame.Surface(image.get_size(), pygame.SRCALPHA)
            temp.blit(self.image, (0, 0))
            self.image = temp
        
        self.rect = self.image.get_rect(topleft=pos)
        
    @property
    def position(self):
        return self.rect.topleft
    
    @position.setter
    def position(self, value):
        self.rect.topleft = value

class CollisionComponent(Component):
    def __init__(self, shrink_hitbox = True):
        super().__init__()
        self.hitbox = pygame.Rect(0, 0, 0, 0)
        self.shrink_hitbox = shrink_hitbox
    
    def on_add(self, entity):
        super().on_add(entity)
        if self.entity.image:
            self.hitbox = self.entity.rect.copy()
            if self.shrink_hitbox:
                self.hitbox.inflate_ip(-self.hitbox.width * 0.5, -self.hitbox.height * 0.5)

class ShapedCollisionComponent(Component):
    def __init__(self):
        super().__init__()
        self.hitbox = None
        self.mask = None

    def on_add(self, entity):
        super().on_add(entity)
        sprite = self.entity.sprite
        self.mask = pygame.mask.from_surface(sprite.image)
        if self.mask.count():
            bounds = self.mask.get_bounding_rects()[0]
            if bounds:
                self.hitbox = pygame.Rect(
                    bounds.x + sprite.rect.x,
                    bounds.y + sprite.rect.y,
                    bounds.width,
                    bounds.height
                )

class AnimationComponent(Component):
    def __init__(self, animations, frame_duration = 0.1):
        super().__init__()
        self.animations = animations
        self.current_animation = None
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.time_accumulated = 0
        
    def play(self, animation_name, loop=True):
        if animation_name != self.current_animation:
            self.current_animation = animation_name
            self.current_frame = 0
            self.time_accumulated = 0
    
    def update(self, dt):
        if not self.current_animation or self.current_animation not in self.animations:
            return
            
        self.time_accumulated += dt
        if self.time_accumulated >= self.frame_duration:
            self.time_accumulated = 0
            self.current_frame = (self.current_frame + 1) % len(self.animations[self.current_animation])
            
            sprite = self.entity.get_component(SpriteComponent)
            if sprite:
                current_anchor = sprite.rect.midbottom 
                sprite.image = self.animations[self.current_animation][self.current_frame]
                sprite.rect = sprite.image.get_rect(midbottom=current_anchor)
                if self.entity.collision and self.entity.collision.hitbox:
                    self.entity.collision.hitbox.center = sprite.rect.center

class InteractionComponent(Component):
    def __init__(self, radius = 60, text = "Нажмите E для взаимодействия"):
        super().__init__()
        self.radius = radius
        self.can_interact = True
        self.interaction_text = text
    
    def can_player_interact(self, player_pos):
        if not self.can_interact: return False
        if not self.entity or not self.entity.sprite: return False
            
        entity_center = self.entity.rect.center
        distance = pygame.math.Vector2(player_pos[0] - entity_center[0], player_pos[1] - entity_center[1]).length()
        return distance <= self.radius
    
    def interact(self, player):
        for component in self.entity.components.values():
            if hasattr(component, 'interact') and component != self:
                component.interact(player)
                return

class StateComponent(Component):
    def __init__(self, initial_state = None):
        super().__init__()
        self.state = initial_state or {}
        self.requires_game_time = True

    def get_state(self):
        return self.state.copy()

    def set_state(self, new_state):
        self.state.update(new_state)
        for component in self.entity.components.values():
            if hasattr(component, 'load_state'):
                component.load_state(self.state)

    def update(self, dt):
        if not self.entity: return
        for component in self.entity.components.values():
            if hasattr(component, 'save_state'):
                self.state.update(component.save_state())

class StoveComponent(Component):
    def __init__(self):
        super().__init__()
        self.energy_cost = 5
        self.cooking_cost = 15
        self.is_cooking = False
        self.cooking_time = 10
        self.cooking_timer = 0
        self.fluid_amount = 0
        self.fluid_type = 'wood'
        self.fluid_max_amount = 100
        self.fluid_consumption_timer = 0
        self.fluid_consumption_time = 60
        self.fluid_consumption_amount = 1
        self.requires_game_time = True
        self.cooking_interface = None
        self.recipes = recipe_manager.get_all_recipes()
        self.current_recipe = None
        self.ingredient_slots = [InventorySlot() for _ in range(6)]
        self.result_slot = InventorySlot()
        self.fuel_slot_item_id = None
        self.ingredients_changed = True

    @property
    def is_lit(self):
        return self.fluid_amount > 0

    def add_fuel(self, amount, fuel_type = 'wood'):
        if fuel_type != self.fluid_type: return False
        if self.fluid_amount + amount <= self.fluid_max_amount:
            was_unlit = not self.is_lit
            self.fluid_amount += amount
            if was_unlit and self.is_lit:
                if anim := self.entity.get_component(AnimationComponent):
                    anim.play('lit')
            self.ingredients_changed = True
            self._sync_state()
            return True
        return False

    def _sync_state(self):
        if self.entity:
            if state_comp := self.entity.get_component(StateComponent):
                state_comp.state.update(self.save_state())
        self.ingredients_changed = True

    def _close_interface(self):
        if not self.cooking_interface: return
        player = self.cooking_interface.player
        drag_manager.unregister(self.cooking_interface)
        self.cooking_interface.is_open = False
        player.inventory.external_drop_target = None
        self.cooking_interface = None

    def interact(self, player):
        if not self.cooking_interface:
            self.cooking_interface = StoveInterface(self, player, player.scene.game.screen)
            drag_manager.register(self.cooking_interface)
            self._sync_state()
        else:
            self._close_interface()

    def try_start_cooking(self):
        if self.is_cooking or not self.is_lit or not self.recipes or not self.ingredients_changed: return
        self.ingredients_changed = False

        if not self.cooking_interface or not self.cooking_interface.player: return
        player = self.cooking_interface.player
        player_stats = player.get_component(PlayerStatsComponent)
        if not player_stats or player_stats.energy < self.energy_cost: return
        if self.fluid_amount < self.cooking_cost: return
        if not self.result_slot.is_empty(): return

        ingredient_counts = {}
        for s in self.ingredient_slots:
            if not s.is_empty():
                ingredient_counts[s.item_id] = ingredient_counts.get(s.item_id, 0) + s.amount
        
        if not ingredient_counts:
            return
        
        for recipe_id, recipe in self.recipes.items():
            required_ingredients = recipe.get("ingredients", {})
            if ingredient_counts == required_ingredients:
                if player_stats.spend_energy(self.energy_cost):
                    self.is_cooking = True
                    self.cooking_timer = recipe["cooking_time"]
                    self.fluid_amount -= self.cooking_cost
                    self.current_recipe = {'id': recipe_id, **recipe}
                    for slot in self.ingredient_slots: slot.clear()
                    if anim := self.entity.get_component(AnimationComponent): anim.play('cooking')
                    self.ingredients_changed = True
                    self._sync_state()
                return

    def update(self, dt):
        if not self.is_cooking: self.try_start_cooking()
        
        if self.is_lit:
            self.fluid_consumption_timer += dt 
            if self.fluid_consumption_timer >= self.fluid_consumption_time:
                self.fluid_consumption_timer -= self.fluid_consumption_time
                self.fluid_amount -= self.fluid_consumption_amount
                if self.fluid_amount <= 0:
                    self.fluid_amount = 0
                    self.is_cooking = False
                    if anim := self.entity.get_component(AnimationComponent): anim.play('idle')

        if self.is_cooking:
            self.cooking_timer -= dt 
            if self.cooking_timer <= 0:
                self.is_cooking = False
                if self.current_recipe:
                    self.result_slot.item_id = self.current_recipe['result']
                    self.result_slot.amount = self.current_recipe.get('amount', 1)
                    self.current_recipe = None
                    self.ingredients_changed = True
                    self._sync_state()
                if self.is_lit:
                    if anim := self.entity.get_component(AnimationComponent): anim.play('lit')

        if self.cooking_interface and self.cooking_interface.is_open:
            self.cooking_interface.update(dt, game_time)
            player = self.cooking_interface.player
            if player.inventory.visible: self._close_interface()
            elif (comp := self.entity.get_component(InteractionComponent)) and \
                 pygame.math.Vector2(player.rect.center).distance_to(self.entity.rect.center) > comp.radius:
                self._close_interface()
        self.save_state()

    def save_state(self):
        return {
            "is_cooking": self.is_cooking, "fluid_amount": self.fluid_amount,
            "cooking_timer": self.cooking_timer, "cooking_time": self.cooking_time,
            "ingredients": [s.to_dict() for s in self.ingredient_slots],
            "result": self.result_slot.to_dict(), "fuel_item": self.fuel_slot_item_id,
            "current_recipe": self.current_recipe
        }

    def load_state(self, state):
        self.is_cooking = state.get("is_cooking", False)
        self.fluid_amount = state.get("fluid_amount", 0)
        self.cooking_timer = state.get("cooking_timer", 0)
        self.cooking_time = state.get("cooking_time", 10)
        self.ingredient_slots = [InventorySlot.from_dict(d) for d in state.get("ingredients", [])]
        while len(self.ingredient_slots) < 6: self.ingredient_slots.append(InventorySlot())
        self.result_slot = InventorySlot.from_dict(state.get("result", {}))
        self.fuel_slot_item_id = state.get("fuel_item")
        self.current_recipe = state.get("current_recipe")
        if anim := self.entity.get_component(AnimationComponent):
            if self.is_cooking: anim.play('cooking') 
            elif self.is_lit: anim.play('lit')
            else: anim.play('idle')

class StorageComponent(Component):
    def __init__(self):
        super().__init__()
        self.inventory = Inventory(size=(6, 4), inventory_type='storage')
        self.interacting_player = None

    @property
    def is_open(self):
        return self.inventory.visible

    def interact(self, player):
        self.inventory.visible = not self.inventory.visible
        if self.is_open:
            self.interacting_player = player
            drag_manager.register(self.inventory)
        else:
            self.interacting_player = None
            drag_manager.unregister(self.inventory)
    
    def update(self, dt):
        if self.is_open and self.interacting_player:
            if (comp := self.entity.get_component(InteractionComponent)) and \
               pygame.math.Vector2(self.interacting_player.rect.center).distance_to(self.entity.rect.center) > comp.radius:
                    self.interact(self.interacting_player)

    def save_state(self):
        return {"inventory": self.inventory.to_dict()}

    def load_state(self, state):
        if inventory_data := state.get("inventory"):
            self.inventory.from_dict(inventory_data)

class ToiletComponent(Component):
    def __init__(self, rest_amount: int = TOILET_REST_AMOUNT):
        super().__init__()
        self.rest_amount = rest_amount
        self.is_occupied = False
        self.occupation_timer = 0
        self.occupation_time = 5
        self.requires_game_time = True

    def interact(self, player):
        player_stats = player.get_component(PlayerStatsComponent)
        if not self.is_occupied and player_stats:
            player_stats.rest(self.rest_amount)
            self.is_occupied = True
            self.occupation_timer = self.occupation_time

    def update(self, dt):
        if self.is_occupied:
            self.occupation_timer -= dt 
            if self.occupation_timer <= 0: self.is_occupied = False

    def save_state(self):
        return {"is_occupied": self.is_occupied, "occupation_timer": self.occupation_timer}

    def load_state(self, state):
        self.is_occupied = state.get("is_occupied", False)
        self.occupation_timer = state.get("occupation_timer", 0)

class BedComponent(Component):
    def __init__(self):
        super().__init__()
        self.rest_amount = BED_REST_AMOUNT
        self.is_used = False
        self.cooldown = 10  
        self.cooldown_timer = 0
        self.requires_game_time = True

    def interact(self, player):
        if self.is_used:
            return

        game_time.advance_to_next_day()
        player.scene.game.save_game()
        if player_stats := player.get_component(PlayerStatsComponent):
            player_stats.rest(self.rest_amount)
        
        self.is_used = True
        self.cooldown_timer = self.cooldown

    def update(self, dt):
        if self.is_used:
            self.cooldown_timer -= dt
            if self.cooldown_timer <= 0:
                self.is_used = False

    def save_state(self):
        return {
            "is_used": self.is_used,
            "cooldown_timer": self.cooldown_timer,
        }

    def load_state(self, state):
        self.is_used = state.get("is_used", False)
        self.cooldown_timer = state.get("cooldown_timer", 0)

class TableComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.items_on_table = []

    def interact(self, player):
        self.is_used = not self.is_used

    def save_state(self):
        return {"is_used": self.is_used, "items_on_table": self.items_on_table.copy()}

    def load_state(self, state):
        self.is_used = state.get("is_used", False)
        self.items_on_table = state.get("items_on_table", [])

class ChairComponent(Component):
    def __init__(self, table_id: Optional[str] = None):
        super().__init__()
        self.is_occupied = False
        self.occupant = None
        self.table_id = table_id

    def occupy(self, character):
        if not self.is_occupied:
            self.is_occupied = True
            self.occupant = character
            return True
        return False

    def vacate(self):
        self.is_occupied = False
        self.occupant = None

    def interact(self, player):
        state_comp = player.get_component(CharacterStateComponent)
        if not state_comp: return

        if not self.is_occupied and not state_comp.is_sitting():
            if self.occupy(player):
                state_comp.chair = self.entity
                state_comp.set_state(Sitting(player))
        elif self.occupant == player and state_comp.is_sitting():
            self.vacate()
            state_comp.chair = None
            state_comp.set_state(Idle(player))

    def save_state(self): return {}
    def load_state(self, state): pass

class WoodComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.cooldown = 60
        self.cooldown_timer = 0
        self.fuel_amount = 20
        self.requires_game_time = True

    def interact(self, player):
        if not self.is_used and hasattr(player, 'inventory'):
            overflow = player.inventory.add_item('wood', amount=self.fuel_amount)
            if (self.fuel_amount - overflow) > 0:
                self.is_used = True
                self.cooldown_timer = self.cooldown

    def update(self, dt):
        if self.is_used:
            self.cooldown_timer -= dt 
            if self.cooldown_timer <= 0: self.is_used = False

    def save_state(self):
        return {"is_used": self.is_used, "cooldown_timer": self.cooldown_timer}

    def load_state(self, state):
        self.is_used = state.get("is_used", False)
        self.cooldown_timer = state.get("cooldown_timer", 0)

class PlayerControllerComponent(Component):
    def __init__(self):
        super().__init__()

    def update(self, dt):
        if (state_comp := self.entity.get_component(CharacterStateComponent)) and state_comp.is_sitting(): return
        if not (movement := self.entity.get_component(CharacterMovementComponent)): return

        move_direction = pygame.math.Vector2(
            INPUTS.get('right', 0) - INPUTS.get('left', 0),
            INPUTS.get('down', 0) - INPUTS.get('up', 0)
        )
        movement.move_direction = move_direction

        if INPUTS['interact']:
            if hasattr(self.entity, 'interaction_system'):
                self.entity.interaction_system.interact_with_nearest(self.entity)
            INPUTS['interact'] = False
        
        if INPUTS.get('inventory'):
            if hasattr(self.entity, 'inventory'):
                self.entity.inventory.visible = not self.entity.inventory.visible
            INPUTS['inventory'] = False
            
        self.check_exits()

    def check_exits(self):
        scene = self.entity.scene
        for exit_sprite in scene.exit_sprites:
            if self.entity.hitbox.colliderect(exit_sprite.hitbox):
                scene.next_scene = SCENE_DATA[scene.current_scene][exit_sprite.name]
                scene.entry_point = exit_sprite.name + '_entry'
                scene.go_to_scene()
                break

class AIControllerComponent(Component):
    def __init__(self):
        super().__init__()
        self.decision_timer = random.uniform(NPC_IDLE_MIN_TIME, NPC_IDLE_MAX_TIME)

    def interact(self, player):
        state_comp = self.entity.get_component(CharacterStateComponent)
        if not state_comp or not isinstance(state_comp.state, WaitingForFood):
            return

        if not state_comp.order: return

        ordered_item_id = state_comp.order[1]
        if player.inventory.remove_item(ordered_item_id, 1):
            if bubble_comp := self.entity.get_component(ThoughtBubbleComponent):
                bubble_comp.hide_bubble()
            
            state_comp.set_state(Eating(self.entity, ordered_item_id))
            state_comp.order = None

    def update(self, dt):
        state_comp = self.entity.get_component(CharacterStateComponent)
        if not state_comp or not isinstance(state_comp.state, Idle):
            self.decision_timer = random.uniform(NPC_IDLE_MIN_TIME, NPC_IDLE_MAX_TIME)
            return
            
        self.decision_timer -= dt
        if self.decision_timer <= 0:
            state_comp.set_state(FindingChair(self.entity))
            
class CharacterStateComponent(Component):
    def __init__(self, initial_state_class):
        super().__init__()
        self.state = None
        self.initial_state_class = initial_state_class
        self.chair = None
        self.order = None
    
    def on_add(self, entity):
        super().on_add(entity)
        self.set_state(self.initial_state_class(self.entity))

    def set_state(self, new_state_instance):
        if not self.state or self.state.__class__ != new_state_instance.__class__:
            self.state = new_state_instance
    
    def is_sitting(self):
        return isinstance(self.state, Sitting)

    def update(self, dt):
        if self.state:
            if new_state := self.state.update(dt):
                self.set_state(new_state)

class CharacterMovementComponent(Component):
    def __init__(self, speed, force, friction):
        super().__init__()
        self.speed = speed
        self.force = force
        self.friction = friction
        self.acc = pygame.math.Vector2()
        self.vel = pygame.math.Vector2()
        self.move_direction = pygame.math.Vector2()

    def movement(self):
        state_comp = self.entity.get_component(CharacterStateComponent)
        if state_comp and state_comp.is_sitting():
            self.acc = pygame.math.Vector2(0, 0)
        else:
            self.acc.x = self.move_direction.x * self.force
            self.acc.y = self.move_direction.y * self.force

    def physics(self, dt):
        self.vel = self.vel * (1 - self.friction) + self.acc * dt
        
        if self.vel.length_squared() > self.speed ** 2:
            self.vel.scale_to_length(self.speed)
            
        if self.move_direction.length() == 0 and self.vel.length() < 1:
            self.vel = pygame.math.Vector2(0, 0)
            
        self.entity.hitbox.centerx += self.vel.x * dt
        self._collide('x')

        self.entity.hitbox.centery += self.vel.y * dt
        self._collide('y')
        
        self.entity.rect.center = self.entity.hitbox.center

    def update(self, dt):
        self.movement()
        self.physics(dt)

    def _collide(self, axis):
        for sprite in self.entity.scene.block_sprites:
            if sprite != self.entity and self.entity.hitbox.colliderect(sprite.hitbox):
                if axis == 'x':
                    if self.vel.x > 0: self.entity.hitbox.right = sprite.hitbox.left
                    if self.vel.x < 0: self.entity.hitbox.left = sprite.hitbox.right
                    self.vel.x = 0
                if axis == 'y':
                    if self.vel.y > 0: self.entity.hitbox.bottom = sprite.hitbox.top
                    if self.vel.y < 0: self.entity.hitbox.top = sprite.hitbox.bottom
                    self.vel.y = 0

class PlayerStatsComponent(Component):
    def __init__(self):
        super().__init__()
        self.max_energy = PLAYER_STATE.get('max_energy', 100)
        self.energy = PLAYER_STATE.get('energy', 100)

    def spend_energy(self, amount):
        if self.energy >= amount:
            self.energy = max(0, self.energy - amount)
            return True
        return False

    def rest(self, amount):
        self.energy = min(self.max_energy, self.energy + amount)

    def save_state(self):
        return {
            'energy': self.energy,
            'max_energy': self.max_energy
        }

    def load_state(self, state):
        self.energy = state.get('energy', self.max_energy)
        self.max_energy = state.get('max_energy', 100)


class Entity(pygame.sprite.Sprite):
    def __init__(self, groups=None):
        super().__init__(groups) if groups else super().__init__()
        self.components = {}
        self.id = None
        self.active: bool = True
        self._is_blocking: bool = False
        self.scene = None

    @property
    def is_blocking(self):
        return self._is_blocking

    @is_blocking.setter
    def is_blocking(self, value):
        self._is_blocking = value

    @property
    def sprite(self): return self.get_component(SpriteComponent)
    @property
    def collision(self): return self.get_component(CollisionComponent)
    @property
    def interaction(self): return self.get_component(InteractionComponent)
    @property
    def shaped_collision(self): return self.get_component(ShapedCollisionComponent)
    
    @property
    def rect(self):
        return self.sprite.rect if self.sprite else pygame.Rect(0, 0, 0, 0)
    
    @property
    def image(self):
        return self.sprite.image if self.sprite else pygame.Surface((0, 0))
    
    @property
    def hitbox(self):
        if (sc := self.shaped_collision) and sc.hitbox: return sc.hitbox
        if (c := self.collision) and c.hitbox: return c.hitbox
        return self.rect.copy()
    
    @property
    def position(self):
        return self.sprite.position if self.sprite else (0, 0)

    @position.setter
    def position(self, value):
        if self.sprite: self.sprite.position = value

    @property
    def z(self):
        return self.sprite.layer if self.sprite else 'objects'

    def add_component(self, component):
        self.components[type(component)] = component
        component.on_add(self)
    
    def get_component(self, component_type):
        return self.components.get(component_type)
    
    def has_component(self, component_type):
        return component_type in self.components

    def update(self, dt):
        try:
            state_comp = self.get_component(CharacterStateComponent)
            for component in self.components.values():
                if component != state_comp and hasattr(component, 'update'):
                    component.update(dt)
            if state_comp: state_comp.update(dt)
        except Exception as e:
            print(f"Error updating entity {self.id}: {e}")

    def save_state(self):
        for component in self.components.values():
            if hasattr(component, 'save_state'):
                component.save_state()

    def can_player_interact(self, player):
        interaction_comp = self.get_component(InteractionComponent)
        return interaction_comp.can_player_interact(player.rect.center) if interaction_comp else False
    
    def interact(self, player):
        if self.interaction: self.interaction.interact(player)


class BaseState:
    def __init__(self, character_entity):
        self.entity = character_entity
        self.anim_comp = self.entity.get_component(AnimationComponent)
        self.move_comp = self.entity.get_component(CharacterMovementComponent)
        if self.anim_comp: self.anim_comp.current_frame = 0
        self._last_direction = 'down'

    def get_direction(self):
        if not self.move_comp or self.move_comp.vel.length_squared() == 0:
            return self._last_direction
        
        angle = self.move_comp.vel.angle_to(pygame.math.Vector2(0, 1))
        angle = (angle + 360) % 360
        
        if 45 <= angle < 135: self._last_direction = 'right'
        elif 135 <= angle < 225: self._last_direction = 'up'
        elif 225 <= angle < 315: self._last_direction = 'left'
        else: self._last_direction = 'down'
        return self._last_direction

    def update(self, dt):
        raise NotImplementedError

class Idle(BaseState):
    def update(self, dt):
        if self.entity.get_component(PlayerControllerComponent):
            if self.move_comp and self.move_comp.vel.length_squared() > 4:
                return Walk(self.entity)
        
        if self.anim_comp: self.anim_comp.play(f'idle_{self.get_direction()}')
        return None

class Walk(BaseState):
    def update(self, dt):
        if self.entity.get_component(PlayerControllerComponent):
            if not self.move_comp or self.move_comp.vel.length_squared() < 1:
                return Idle(self.entity)
        
        if self.anim_comp: self.anim_comp.play(f'walk_{self.get_direction()}')
        return None

class Sitting(BaseState):
    def __init__(self, character):
        super().__init__(character)
        self.sit_timer = random.uniform(NPC_SIT_MIN_TIME, NPC_SIT_MAX_TIME)
        state_comp = character.get_component(CharacterStateComponent)
        
        if state_comp and state_comp.chair:
            character.position = state_comp.chair.position
            if character.hitbox: character.hitbox.center = character.rect.center

            if (chair_comp := state_comp.chair.get_component(ChairComponent)) and chair_comp.table_id:
                if (table := character.scene.room.get_object_by_id(chair_comp.table_id)):
                    direction_vec = pygame.math.Vector2(table.rect.center) - pygame.math.Vector2(character.rect.center)
                    if direction_vec.length_squared() > 0:
                        angle = direction_vec.angle_to(pygame.math.Vector2(0, 1))
                        self._last_direction = ['down', 'right', 'up', 'left'][int(((angle + 360) % 360 + 45) / 90) % 4]

    def update(self, dt):
        if self.entity.get_component(PlayerControllerComponent):
            if INPUTS.get('space'):
                INPUTS['space'] = False
                state_comp = self.entity.get_component(CharacterStateComponent)
                if state_comp and state_comp.chair:
                    if chair_comp := state_comp.chair.get_component(ChairComponent):
                        chair_comp.vacate()
                    state_comp.chair = None
                return Idle(self.entity)
        else:
            self.sit_timer -= dt
            if self.sit_timer <= 0: return Ordering(self.entity)

        if self.anim_comp: self.anim_comp.play(f'idle_{self.get_direction()}', loop=False)
        return None

class Ordering(BaseState):
    def __init__(self, character):
        super().__init__(character)
        self.decision_timer = random.uniform(NPC_ORDERING_MIN_TIME, NPC_ORDERING_MAX_TIME)

    def update(self, dt):
        self.decision_timer -= dt
        if self.decision_timer <= 0:
            if not (orderable_recipes := recipe_manager.get_orderable_recipes()):
                return Idle(self.entity)
            
            ordered_recipe_id = random.choice(list(orderable_recipes.keys()))
            result_item_id = orderable_recipes[ordered_recipe_id].get('result', ordered_recipe_id)
            
            order = (self.entity, result_item_id, ordered_recipe_id)
            
            if state_comp := self.entity.get_component(CharacterStateComponent):
                state_comp.order = order

            if bubble_comp := self.entity.get_component(ThoughtBubbleComponent):
                bubble_comp.show_bubble(result_item_id)

            if hasattr(self.entity.scene.room, 'add_order'):
                self.entity.scene.room.add_order(order)
            return WaitingForFood(self.entity)
        
        if self.anim_comp: self.anim_comp.play(f'idle_{self.get_direction()}')
        return None

class WaitingForFood(BaseState):
    def __init__(self, character):
        super().__init__(character)
        state_comp = self.entity.get_component(CharacterStateComponent)
        if state_comp and state_comp.order:
            entity_id = self.entity.id 
            item_id = state_comp.order[1]
            print(f"DEBUG: NPC {entity_id} is now in WaitingForFood state, ordered: {item_id}")

    def update(self, dt):
        if self.anim_comp: self.anim_comp.play(f'idle_{self.get_direction()}')
        return None

class Eating(BaseState):
    def __init__(self, character, food_item_id):
        super().__init__(character)
        recipe = None
        state_comp = self.entity.get_component(CharacterStateComponent)
        if state_comp and state_comp.order and len(state_comp.order) > 2:
             recipe = recipe_manager.get_recipe(state_comp.order[2])
        self.eating_timer = (recipe.get('cooking_time', 5) if recipe else 5) * NPC_EATING_TIME
        
    def update(self, dt):
        self.eating_timer -= dt
        if self.eating_timer <= 0:
            state_comp = self.entity.get_component(CharacterStateComponent)
            if state_comp and state_comp.chair:
                if chair_comp := state_comp.chair.get_component(ChairComponent):
                    chair_comp.vacate()
                state_comp.chair = None
            return Leaving(self.entity)

        if self.anim_comp: self.anim_comp.play(f'idle_{self.get_direction()}', loop=False)
        return None

class Leaving(BaseState):
    def __init__(self, character):
        super().__init__(character)
        state_comp = character.get_component(CharacterStateComponent)
        if state_comp:
            state_comp.order = None # Clear any outstanding order if leaving
        
        if state_comp and state_comp.chair:
            if chair_comp := state_comp.chair.get_component(ChairComponent):
                chair_comp.vacate()

    def update(self, dt):
        self.entity.kill()
        return None

class FindingChair(BaseState):
    def __init__(self, character):
        super().__init__(character)

    def update(self, dt):
        if free_chair := self.entity.scene.room.get_free_chair():
            self.entity.target = free_chair
            return MovingToTarget(self.entity)
        else:
            return Idle(self.entity)

class MovingToTarget(BaseState):
    def __init__(self, character):
        super().__init__(character)
        self.path = []
        state_comp = character.get_component(CharacterStateComponent)
        if not state_comp: return
        
        if not hasattr(character, 'target') or not character.target:
            state_comp.set_state(Idle(character))
            return

        room = character.scene.room
        start_pos = (character.rect.centerx // room.sub_tile_size, character.rect.centery // room.sub_tile_size)
        
        target_pos = None
        if hasattr(room, 'find_target'):
            target_pos = room.find_target(character.target)

        if not target_pos:
            state_comp.set_state(Idle(character))
            return
            

        self.path = astar(room.grid, start_pos, target_pos)
        if self.path:
            self.path = [(x * room.sub_tile_size + room.sub_tile_size / 2, y * room.sub_tile_size + room.sub_tile_size / 2) for x, y in self.path]
        else:
            state_comp.set_state(Idle(character))

    def update(self, dt):
        if not hasattr(self.entity, 'target') or not self.entity.target:
            return Idle(self.entity)

        distance_to_chair = (pygame.math.Vector2(self.entity.target.rect.center) - self.entity.rect.center).length()
        if distance_to_chair < INTERACTION_DISTANCE * TILE_SIZE:
            self.move_comp.move_direction.update(0, 0)
            self.move_comp.vel.update(0, 0)
            if (chair_comp := self.entity.target.get_component(ChairComponent)) and chair_comp.occupy(self.entity):
                if state_comp := self.entity.get_component(CharacterStateComponent):
                    state_comp.chair = self.entity.target
                return Sitting(self.entity)
            else:
                return Idle(self.entity)

        if self.path:
            target_pos = self.path[0]
            if (pygame.math.Vector2(target_pos) - self.entity.rect.center).length() < self.entity.scene.room.sub_tile_size * 0.8:
                self.path.pop(0)

            if self.path:
                self.move_comp.move_direction = (pygame.math.Vector2(self.path[0]) - self.entity.rect.center).normalize()
                if self.anim_comp:
                    self.anim_comp.play(f'walk_{self.get_direction()}')
                return None
        
        self.move_comp.move_direction.update(0, 0)
        self.move_comp.vel.update(0, 0)
        
        if (chair_comp := self.entity.target.get_component(ChairComponent)) and chair_comp.occupy(self.entity):
            if state_comp := self.entity.get_component(CharacterStateComponent):
                state_comp.chair = self.entity.target
            return Sitting(self.entity)

        return Idle(self.entity)

class ThoughtBubbleComponent(Component):
    def __init__(self, offset=(0, -50)):
        super().__init__()
        self.offset = offset
        self.item_id = None
        self.visible = False
        self.item_image = None

    def show_bubble(self, item_id):
        from items.item_manager import item_manager
        self.item_id = item_id
        self.visible = True
        self.item_image = item_manager.get_sprite(item_id, size=(32, 32))

    def hide_bubble(self):
        self.visible = False
        self.item_id = None
        self.item_image = None