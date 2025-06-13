from typing import Dict, List, Type, Any, Optional, Tuple
import pygame
import pygame.mask
from game_time import GameTimeManager
from cooking import CookingInterface
import json
class Component:
    def __init__(self):
        self.entity = None
        self.requires_game_time = False
    
    def on_add(self, entity):
        self.entity = entity
    
    def update(self, dt: float, game_time: Optional['GameTimeManager'] = None):
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
                self.hitbox.inflate_ip(-self.hitbox.width * 0.2, -self.hitbox.height * 0.2)

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
    
    def update(self, dt: float, game_time: Optional['GameTimeManager'] = None):
        print(game_time)
        try:
            state_component = None
            for component in self.components.values():
                if isinstance(component, StateComponent):
                    state_component = component
                    continue

                if hasattr(component, 'update'):
                    if component.requires_game_time:
                        component.update(dt, game_time)
                    else:
                        component.update(dt)

            if state_component:
                state_component.update(dt, game_time)

        except Exception as e:
            print(f"Error updating {self.id}: {e}")

    def can_player_interact(self, player) -> bool:
        if interaction := self.interaction:
            return interaction.can_player_interact(player.rect.center)
        return False
    
    def interact(self, player):
        if interaction := self.interaction:
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

    def update(self, dt: float, game_time: 'GameTimeManager') -> None:
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
        self.is_lit = False
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

    def add_fuel(self, amount: float, fuel_type: str = 'wood') -> bool:
        if fuel_type != self.fluid_type:
            print(f"Неправильный тип топлива: требуется {self.fluid_type}")
            return False
        if self.fluid_amount + amount <= self.fluid_max_amount:
            self.fluid_amount += amount
            print(f"Добавлено {amount} {fuel_type}. Топливо: {self.fluid_amount}/{self.fluid_max_amount}")
            return True
        print("Печка переполнена!")
        return False

    def interact(self, player):
        if not self.cooking_interface:
            # Загружаем JSON
            with open('assets/items/recipes.json', 'r', encoding='utf-8') as f:
                recipes = json.load(f)
            with open('assets/items/items_data.json', 'r', encoding='utf-8') as f:
                items = json.load(f)
            print(items)
            print(recipes)
            self.cooking_interface = CookingInterface(self, player, player.game.screen, recipes, items)
            print("Открыто окно готовки")
        else:
            self.cooking_interface.is_open = False
            self.cooking_interface = None
            print("Окно готовки закрыто")

    def update(self, dt: float, game_time: GameTimeManager) -> None:
        if game_time is None:
            print("Ошибка: game_time is None в StoveComponent.update")
            return
        game_minutes = dt * game_time.time_scale
        if self.is_lit:
            self.fluid_consumption_timer += game_minutes
            if self.fluid_consumption_timer >= self.fluid_consumption_time:
                self.fluid_consumption_timer -= self.fluid_consumption_time
                self.fluid_amount -= self.fluid_consumption_amount
                if self.fluid_amount <= 0:
                    self.fluid_amount = 0
                    self.is_lit = False
                    self.is_cooking = False
                    if anim := self.entity.get_component(AnimationComponent):
                        anim.play('idle')
                    print(f"[{game_time.get_time_string()}] Печка погасла")

        if self.is_cooking:
            self.cooking_timer -= game_minutes
            if self.cooking_timer <= 0:
                self.is_cooking = False
                if anim := self.entity.get_component(AnimationComponent):
                    anim.play('lit')
                print(f"[{game_time.get_time_string()}] Готовка завершена!")

        if self.cooking_interface and self.cooking_interface.is_open:
            self.cooking_interface.update(dt, game_time)

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_lit": self.is_lit,
            "is_cooking": self.is_cooking,
            "fluid_amount": self.fluid_amount,
            "cooking_timer": self.cooking_timer,
            "fluid_consumption_timer": self.fluid_consumption_timer
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_lit = state.get("is_lit", self.is_lit)
        self.is_cooking = state.get("is_cooking", self.is_cooking)
        self.fluid_amount = state.get("fluid_amount", self.fluid_amount)
        self.cooking_timer = state.get("cooking_timer", self.cooking_timer)
        self.fluid_consumption_timer = state.get("fluid_consumption_timer", self.fluid_consumption_timer)

class StorageComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_open = False
        self.items = []

    def interact(self, player):
        self.is_open = not self.is_open
        if self.is_open and self.items:
            for item in self.items:
                print(f"  - {item}")
        else:
            print("Сундук закрыт")

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_open": self.is_open,
            "items": self.items.copy()
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_open = state.get("is_open", self.is_open)
        self.items = state.get("items", self.items)

class ToiletComponent(Component):
    def __init__(self, rest_amount: int = 10):
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
            print("🚽 Туалет занят")

    def update(self, dt: float, game_time: 'GameTimeManager') -> None:
        if self.is_occupied:
            game_minutes = dt * game_time.time_scale
            self.occupation_timer -= game_minutes
            if self.occupation_timer <= 0:
                self.is_occupied = False
                print(f"[{game_time.get_time_string()}] Туалет свободен")

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_occupied": self.is_occupied,
            "occupation_timer": self.occupation_timer
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_occupied = state.get("is_occupied", self.is_occupied)
        self.occupation_timer = state.get("occupation_timer", self.occupation_timer)

class BedComponent(Component):
    def __init__(self, rest_amount: int = 30):
        super().__init__()
        self.rest_amount = rest_amount

    def interact(self, player):
        print("💤 Отдыхаете...")
        player.rest(self.rest_amount)
        if hasattr(player, 'scene'):
            player.scene.transition.exiting = True

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
        if self.is_used:
            print("🪑 Садитесь за стол...")
        else:
            print("Встаете из-за стола")

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_used": self.is_used,
            "items_on_table": self.items_on_table.copy()
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_used = state.get("is_used", self.is_used)
        self.items_on_table = state.get("items_on_table", self.items_on_table)

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
        
            player.inventory.add_item('wood')
            print(f"Подобрано {self.fuel_amount} дров")
            self.is_used = True
            self.cooldown_timer = self.cooldown
        

    def update(self, dt: float, game_time: 'GameTimeManager'):
        if self.is_used:
            game_minutes = dt * game_time.time_scale
            self.cooldown_timer -= game_minutes
            if self.cooldown_timer <= 0:
                self.is_used = False
                print(f"[{game_time.get_time_string()}] Новые дрова появились")

    def save_state(self) -> Dict[str, Any]:
        return {
            "is_used": self.is_used,
            "cooldown_timer": self.cooldown_timer,
            "fuel_amount": self.fuel_amount
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        self.is_used = state.get("is_used", self.is_used)
        self.cooldown_timer = state.get("cooldown_timer", self.cooldown_timer)
        self.fuel_amount = state.get("fuel_amount", self.fuel_amount)

        

def create_interactive_object(groups: List[pygame.sprite.Group],
                            position: Tuple[float, float],
                            animations: Dict[str, List[pygame.Surface]],
                            use_collision: bool = True,
                            shaped_collision: bool = True) -> Entity:
    
    base_image = None
    if 'idle' in animations and animations['idle']:
        base_image = animations['idle'][0]
    if base_image is None:
        raise ValueError("Base image is None — cannot create SpriteComponent")

    entity = Entity(groups)
    
    entity.add_component(SpriteComponent(base_image, position, layer='interactive'))
    
    if use_collision:
        entity.add_component(ShapedCollisionComponent())
    
    if animations:
        entity.add_component(AnimationComponent(animations))
    
    return entity

def create_stove(groups: List[pygame.sprite.Group], 
                position: Tuple[float, float],
                animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    stove = StoveComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы использовать печку"))
    entity.add_component(stove)
    entity.add_component(StateComponent(stove.save_state()))
    return entity

def create_storage(groups: List[pygame.sprite.Group],
                  position: Tuple[float, float],
                  animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    storage = StorageComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы открыть сундук"))
    entity.add_component(storage)
    entity.add_component(StateComponent(storage.save_state()))
    return entity

def create_toilet(groups: List[pygame.sprite.Group],
                 position: Tuple[float, float],
                 animations: List[pygame.Surface]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    toilet = ToiletComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы использовать туалет"))
    entity.add_component(toilet)
    entity.add_component(StateComponent(toilet.save_state()))
    return entity

def create_bed(groups: List[pygame.sprite.Group],
               position: Tuple[float, float],
               animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    bed = BedComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы отдохнуть"))
    entity.add_component(bed)
    entity.add_component(StateComponent(bed.save_state()))
    return entity

def create_table(groups: List[pygame.sprite.Group],
                position: Tuple[float, float],
                animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    table = TableComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы использовать стол"))
    entity.add_component(table)
    entity.add_component(StateComponent(table.save_state()))
    return entity

def create_wood(groups: List[pygame.sprite.Group],
                position: Tuple[float, float],
                animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    wood = WoodComponent()
    entity.add_component(InteractionComponent(radius=60, text="Нажмите E чтобы подобрать дрова"))
    entity.add_component(wood)
    entity.add_component(StateComponent(wood.save_state()))
    return entity