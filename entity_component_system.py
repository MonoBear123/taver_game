from typing import Dict, List, Type, Any, Optional, Tuple
import pygame
import pygame.mask
from game_time import game_time
from cooking import CookingInterface
from slot import InventorySlot
from drag_manager import drag_manager
from inventory import Inventory
from recipe_manager import recipe_manager
from config import TOILET_REST_AMOUNT, BED_REST_AMOUNT

class Component:
    def __init__(self):
        self.entity = None
        self.requires_game_time = False
    
    def on_add(self, entity):
        self.entity = entity
    
    def update(self, dt: float):
        pass

class SpriteComponent(Component):
    def __init__(self, image: pygame.Surface, pos: Tuple[float, float], layer: str = 'objects', colorkey: Tuple[int, int, int] = None):
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
    def position(self) -> Tuple[float, float]:
        return self.rect.topleft
    
    @position.setter
    def position(self, value: Tuple[float, float]):
        self.rect.topleft = value

class CollisionComponent(Component):
    def __init__(self, shrink_hitbox: bool = True):
        super().__init__()
        self.hitbox = pygame.Rect(0, 0, 0, 0)
        self.shrink_hitbox = shrink_hitbox
        
        
    
    def on_add(self, entity):
        super().on_add(entity)
        if self.entity.image:
            self.hitbox = self.entity.rect.copy()
            if self.shrink_hitbox:
                self.hitbox.inflate(-self.hitbox.width / 0.2, -self.hitbox.height / 0.2)

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

class Entity(pygame.sprite.Sprite):
    def __init__(self, groups: List[pygame.sprite.Group]):
        super().__init__(groups)
        self.components: Dict[Type[Component], Component] = {}
        self.id: str = None
        self.active: bool = True

    @property
    def sprite(self) -> Optional[SpriteComponent]:
        return self.get_component(SpriteComponent)
    
    @property
    def collision(self) -> Optional[CollisionComponent]:
        return self.get_component(CollisionComponent)
    
    @property
    def interaction(self) -> Optional['InteractionComponent']:
        return self.get_component(InteractionComponent)
    
    @property
    def rect(self) -> pygame.Rect:
        if sprite := self.sprite:
            return sprite.rect
        return pygame.Rect(0, 0, 0, 0)
    
    @property
    def image(self) -> pygame.Surface:
        if sprite := self.sprite:
            return sprite.image
        return pygame.Surface((0, 0))
    
    @property
    def shaped_collision(self) -> Optional[ShapedCollisionComponent]:
        return self.get_component(ShapedCollisionComponent)

    @property
    def hitbox(self) -> pygame.Rect:
        if shaped_collision := self.shaped_collision:
            if shaped_collision.hitbox:
                return shaped_collision.hitbox
        if collision := self.collision:
            if collision.hitbox:
                return collision.hitbox
        return self.rect.copy()
    
    @property
    def position(self) -> Tuple[float, float]:
        if sprite := self.sprite:
            return sprite.position
        return (0, 0)

    @position.setter
    def position(self, value: Tuple[float, float]):
        if sprite := self.sprite:
            sprite.position = value

    @property
    def z(self) -> str:
        if sprite := self.sprite:
            return sprite.layer
        return 'objects'

    def add_component(self, component: Component) -> None:
        component_type = type(component)
        if component_type in self.components:
            raise ValueError(f"Component {component_type.__name__} already exists!")
        
        self.components[component_type] = component
        component.on_add(self)
    
    def get_component(self, component_type: Type[Component]) -> Optional[Component]:
        return self.components.get(component_type)
    
    def has_component(self, component_type: Type[Component]) -> bool:
        return component_type in self.components
    
    def remove_component(self, component_type: Type[Component]) -> None:
        if component_type in self.components:
            self.components[component_type].entity = None
            del self.components[component_type]
    
    def update(self, dt: float):
        try:
            state_component = None
            for component in self.components.values():
                if isinstance(component, StateComponent):
                    state_component = component
                    continue

                if hasattr(component, 'update'):
                    component.update(dt)

            if state_component:
                state_component.update(dt)

        except Exception as e:
            print(f"Error updating {self.id}: {e}")

    def can_player_interact(self, player) -> bool:
        if interaction := self.interaction:
            return interaction.can_player_interact(player.rect.center)
        return False
    
    def interact(self, player):
        if interaction := self.interaction:
            print(f"ДЕБАГ: [Entity.interact] Сущность {self.id} имеет InteractionComponent. Вызов...")
            interaction.interact(player)

class AnimationComponent(Component):
    def __init__(self, animations: Dict[str, List[pygame.Surface]], frame_duration: float = 0.1):
        super().__init__()
        self.animations = animations
        self.current_animation = None
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.time_accumulated = 0
        
    def play(self, animation_name: str):
        if animation_name != self.current_animation:
            self.current_animation = animation_name
            self.current_frame = 0
            self.time_accumulated = 0
    
    def update(self, dt: float):
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

class InteractionComponent(Component):
    def __init__(self, radius: float = 60, text: str = "Нажмите E для взаимодействия"):
        super().__init__()
        self.radius = radius
        self.can_interact = True
        self.interaction_text = text
    
    def can_player_interact(self, player_pos: Tuple[float, float]) -> bool:
        if not self.can_interact:
            return False
        if not self.entity or not self.entity.sprite:
            return False
            
        entity_center = self.entity.rect.center
        distance = pygame.math.Vector2(
            player_pos[0] - entity_center[0],
            player_pos[1] - entity_center[1]
        ).length()
        
        return distance <= self.radius
    
    def interact(self, player):
        for component in self.entity.components.values():
            if hasattr(component, 'interact') and component != self:
                component.interact(player)
                return

class StateComponent(Component):
    def __init__(self, initial_state: Dict[str, Any] = None):
        super().__init__()
        self.state = initial_state or {}
        self.last_update_time = 0
        self.requires_game_time = True

    def get_state(self) -> Dict[str, Any]:
        return self.state.copy()

    def set_state(self, new_state: Dict[str, Any]) -> None:
        self.state.update(new_state)
        for component in self.entity.components.values():
            if hasattr(component, 'load_state'):
                component.load_state(self.state)

    def update(self, dt: float) -> None:
        if not self.entity: return

        for component in self.entity.components.values():
            if hasattr(component, 'save_state'):
                self.state.update(component.save_state())

    def to_json(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "entity_id": self.entity.id if self.entity else None
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'StateComponent':
        component = cls(data.get("state", {}))
        return component

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
        self.fluid_consumption_rate = 1
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

    @property
    def is_lit(self) -> bool:
        return self.fluid_amount > 0

    def add_fuel(self, amount: float, fuel_type: str = 'wood') -> bool:
        if fuel_type != self.fluid_type:
            return False
        if self.fluid_amount + amount <= self.fluid_max_amount:
            was_unlit = not self.is_lit
            self.fluid_amount += amount
            if was_unlit and self.is_lit:
                if anim := self.entity.get_component(AnimationComponent):
                    anim.play('lit')
            self._sync_state()
            return True
        return False

    def _sync_state(self):
        if self.entity:
            if state_comp := self.entity.get_component(StateComponent):
                state_comp.state.update(self.save_state())

    def _close_interface(self):
        if not self.cooking_interface:
            return
        player = self.cooking_interface.player
        drag_manager.unregister(self.cooking_interface)
        self.cooking_interface.is_open = False
        player.inventory.external_drop_target = None
        self.cooking_interface = None

    def interact(self, player):
        if not self.cooking_interface:
            self.cooking_interface = CookingInterface(self, player, player.game.screen)
            drag_manager.register(self.cooking_interface)
            self._sync_state()
        else:
            self._close_interface()

    def try_start_cooking(self):
        if self.is_cooking or not self.is_lit or not self.recipes:
            return
        if not self.cooking_interface or not self.cooking_interface.player:
            return
        player = self.cooking_interface.player
        if player.energy < self.energy_cost:
            return
        if self.fluid_amount < self.cooking_cost:
            return
        if not self.result_slot.is_empty():
            return

        ingredient_counts = {}
        for slot in self.ingredient_slots:
            if not slot.is_empty():
                ingredient_counts[slot.item_id] = ingredient_counts.get(slot.item_id, 0) + slot.amount

        if not ingredient_counts:
            return
        
        for recipe_id, recipe in self.recipes.items():
            if ingredient_counts == recipe.get("ingredients", {}):
                if player.spend_energy(self.energy_cost):
                    self.is_cooking = True
                    self.cooking_time = recipe["cooking_time"]
                    self.cooking_timer = recipe["cooking_time"]
                    self.fluid_amount -= self.cooking_cost
                    self.current_recipe = recipe.copy()
                    self.current_recipe['id'] = recipe_id
                    for slot in self.ingredient_slots:
                        slot.clear()
                    if anim := self.entity.get_component(AnimationComponent):
                        anim.play('cooking')
                    self._sync_state()
                return

    def update(self, dt: float) -> None:
        if not self.is_cooking:
            self.try_start_cooking()
        
        if self.is_lit:
            self.fluid_consumption_timer += dt * game_time.time_scale
            if self.fluid_consumption_timer >= self.fluid_consumption_time:
                self.fluid_consumption_timer -= self.fluid_consumption_time
                self.fluid_amount -= self.fluid_consumption_amount
                if self.fluid_amount <= 0:
                    self.fluid_amount = 0
                    self.is_cooking = False
                    if anim := self.entity.get_component(AnimationComponent):
                        anim.play('idle')

        if self.is_cooking:
            self.cooking_timer -= dt * game_time.time_scale
            if self.cooking_timer <= 0:
                self.is_cooking = False
                if self.current_recipe:
                    self.result_slot.item_id = self.current_recipe['result']
                    self.result_slot.amount = self.current_recipe.get('amount', 1)
                    self.current_recipe = None
                    self._sync_state()
                if self.is_lit:
                    if anim := self.entity.get_component(AnimationComponent):
                        anim.play('lit')

        if self.cooking_interface and self.cooking_interface.is_open:
            self.cooking_interface.update(dt, game_time)
            player = self.cooking_interface.player
            if player.inventory.visible:
                self._close_interface()
            elif comp := self.entity.get_component(InteractionComponent):
                dist = pygame.math.Vector2(player.rect.center).distance_to(self.entity.rect.center)
                if dist > comp.radius:
                    self._close_interface()

        self.save_state()

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_cooking": self.is_cooking, "fluid_amount": self.fluid_amount,
            "cooking_timer": self.cooking_timer, "cooking_time": self.cooking_time,
            "fluid_consumption_timer": self.fluid_consumption_timer,
            "ingredients": [s.to_dict() for s in self.ingredient_slots],
            "result": self.result_slot.to_dict(), "fuel_item": self.fuel_slot_item_id,
            "current_recipe": self.current_recipe
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_cooking = state.get("is_cooking", self.is_cooking)
        self.fluid_amount = state.get("fluid_amount", self.fluid_amount)
        self.cooking_timer = state.get("cooking_timer", self.cooking_timer)
        self.cooking_time = state.get("cooking_time", self.cooking_time)
        self.fluid_consumption_timer = state.get("fluid_consumption_timer", self.fluid_consumption_timer)
        
        ingredients_data = state.get("ingredients", [])
        self.ingredient_slots = [InventorySlot.from_dict(d) for d in ingredients_data]
        while len(self.ingredient_slots) < 6:
            self.ingredient_slots.append(InventorySlot())

        result_data = state.get("result")
        self.result_slot = InventorySlot.from_dict(result_data) if result_data else InventorySlot()
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
    
    def update(self, dt: float):
        if self.is_open and self.interacting_player:
            if comp := self.entity.get_component(InteractionComponent):
                player_center = self.interacting_player.rect.center
                entity_center = self.entity.rect.center
                dist = pygame.math.Vector2(player_center).distance_to(entity_center)
                if dist > comp.radius:
                    self.interact(self.interacting_player)

    def save_state(self) -> Dict[str, Any]:
        return {"inventory": self.inventory.to_dict()}

    def load_state(self, state: Dict[str, Any]) -> None:
        inventory_data = state.get("inventory")
        if isinstance(inventory_data, dict):
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
        if not self.is_occupied:
            player.rest(self.rest_amount)
            self.is_occupied = True
            self.occupation_timer = self.occupation_time

    def update(self, dt: float):
        if self.is_occupied:
            self.occupation_timer -= dt * game_time.time_scale
            if self.occupation_timer <= 0:
                self.is_occupied = False

    def save_state(self) -> Dict[str, Any]:
        return {"is_occupied": self.is_occupied, "occupation_timer": self.occupation_timer}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_occupied = state.get("is_occupied", self.is_occupied)
        self.occupation_timer = state.get("occupation_timer", self.occupation_timer)

class BedComponent(Component):
    def __init__(self, rest_amount: int = BED_REST_AMOUNT):
        super().__init__()
        self.rest_amount = rest_amount

    def interact(self, player):
        self.entity.scene.game.save_game()
        game_time.advance_to_next_day()
        player.scene.transition.exiting = True
        player.rest(self.rest_amount)

    def save_state(self) -> Dict[str, Any]:
        return {"rest_amount": self.rest_amount}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.rest_amount = state.get("rest_amount", self.rest_amount)

class TableComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.items_on_table = []

    def interact(self, player):
        self.is_used = not self.is_used

    def save_state(self) -> Dict[str, Any]:
        return {"is_used": self.is_used, "items_on_table": self.items_on_table.copy()}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_used = state.get("is_used", self.is_used)
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
        if not self.is_occupied:
            if not getattr(player, 'is_sitting', False):
                player.sit(self.entity)
        elif self.occupant == player:
            if getattr(player, 'is_sitting', False):
                player.stand_up()

    def save_state(self) -> Dict[str, Any]:
        return {"is_occupied": self.is_occupied, "table_id": self.table_id}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_occupied = state.get("is_occupied", self.is_occupied)

class WoodComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.cooldown = 60
        self.cooldown_timer = 0
        self.fuel_amount = 20
        self.requires_game_time = True

    def interact(self, player):
        if not self.is_used:
            overflow = player.inventory.add_item('wood', amount=self.fuel_amount)
            if (self.fuel_amount - overflow) > 0:
                self.is_used = True
                self.cooldown_timer = self.cooldown

    def update(self, dt: float):
        if self.is_used:
            self.cooldown_timer -= dt * game_time.time_scale
            if self.cooldown_timer <= 0:
                self.is_used = False

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_used": self.is_used, "cooldown_timer": self.cooldown_timer,
            "fuel_amount": self.fuel_amount
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_used = state.get("is_used", self.is_used)
        self.cooldown_timer = state.get("cooldown_timer", self.cooldown_timer)
        self.fuel_amount = state.get("fuel_amount", self.fuel_amount)