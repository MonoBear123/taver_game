from typing import Dict, List, Type, Any, Optional, Tuple
import pygame
import pygame.mask

class Component:
    def __init__(self):
        self.entity = None
    
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
    
    def update(self, dt: float) -> None:
        if not self.active:
            return
        for component in self.components.values():
            if hasattr(component, 'update'):
                component.update(dt)

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
    
    def get_state(self) -> Dict[str, Any]:
        return self.state.copy()
    
    def set_state(self, new_state: Dict[str, Any]) -> None:
        self.state.update(new_state)
    
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
    """Компонент для логики работы печки"""
    def __init__(self):
        super().__init__()
        self.is_lit = False
        self.energy_cost = 5
        self.cooking_cost = 15
        self.is_cooking = False
        self.cooking_time = 10
        self.fluid_amount = 0
        self.fluid_type = 'wood'
        self.fluid_max_amount = 100
        self.fluid_consumption_rate = 1
        self.fluid_consumption_time = 10
        self.fluid_consumption_amount = 1
        
    
    def interact(self, player):
        if not self.is_lit:
            if player.energy >= self.energy_cost and self.fluid_amount >= 0:
                self.is_lit = True
                player.energy -= self.energy_cost
                if anim := self.entity.get_component(AnimationComponent):
                    anim.play('lit')
            else:
                print("😴 Недостаточно энергии чтобы зажечь печку")
        else:
            if player.energy >= self.cooking_cost:
                player.energy -= self.cooking_cost
                self.is_cooking = True
                if anim := self.entity.get_component(AnimationComponent):
                    anim.play('cooking')
            else:
                print("😴 Недостаточно энергии чтобы готовить")

class BedComponent(Component):
    def __init__(self, rest_amount: int = 30):
        super().__init__()
        self.rest_amount = rest_amount
    
    def interact(self, player):
            print("💤 Отдыхаете...")
            player.rest(self.rest_amount)
            if hasattr(player, 'scene'):
                player.scene.transition.exiting = True

class StorageComponent(Component):
    """Компонент для логики работы сундука/хранилища"""
    def __init__(self):
        super().__init__()
        self.is_open = False
        self.items = []
    
    def interact(self, player):
        if not self.is_open:
            self.is_open = True
            if self.items:
                for item in self.items:
                    print(f"  - {item}")
        else:
            self.is_open = False

class ToiletComponent(Component):
    def __init__(self, rest_amount: int = 10):
        super().__init__()
        self.rest_amount = rest_amount
        self.is_occupied = False
    
    def interact(self, player):
        if not self.is_occupied:
            player.rest(self.rest_amount)
            self.is_occupied = True

class TableComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.items_on_table = []
    
    def interact(self, player):
        if not self.is_used:
            print("🪑 Садитесь за стол...")
            self.is_used = True

class WoodComponent(Component):
    def __init__(self):
        super().__init__()
        self.is_used = False
        self.cooldown = 10
        self.cooldown_time = 0
        
    def interact(self, player):
        if not self.is_used and self.cooldown_time < 0:
                self.is_used = True


    def update(self, dt: float):
        if self.is_used:
            self.cooldown_time -= dt
            if self.cooldown_time < 0:
                self.is_used = False
                self.cooldown_time = self.cooldown
        

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
    
    entity.add_component(InteractionComponent(
        radius=60,
        text="Нажмите E чтобы использовать печку"
    ))
    entity.add_component(StoveComponent())
    entity.add_component(StateComponent({"is_lit": False}))
    
    return entity

def create_bed(groups: List[pygame.sprite.Group],
               position: Tuple[float, float],
               animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    
    entity.add_component(InteractionComponent(
        radius=60,
        text="Нажмите E чтобы отдохнуть"
    ))
    entity.add_component(BedComponent())
    
    return entity

def create_storage(groups: List[pygame.sprite.Group],
                  position: Tuple[float, float],
                  animations: Dict[str, List[pygame.Surface]]) -> Entity:
    """Создает сущность сундука"""
    print("Создаем сундук")
    entity = create_interactive_object(groups, position, animations)
    
    entity.add_component(InteractionComponent(
        radius=60,
        text="Нажмите E чтобы открыть сундук"
    ))
    entity.add_component(StorageComponent())
    entity.add_component(StateComponent({
        "is_open": False,
        "items": []
    }))
    
    return entity

def create_table(groups: List[pygame.sprite.Group],
                position: Tuple[float, float],
                animations: Dict[str, List[pygame.Surface]]) -> Entity:
    """Создает сущность стола"""
    print("Создаем стол")
    entity = create_interactive_object(groups, position, animations)
    
    entity.add_component(InteractionComponent(
        radius=60,
        text="Нажмите E чтобы использовать стол"
    ))
    entity.add_component(TableComponent())
    
    return entity

def create_toilet(groups: List[pygame.sprite.Group],
                 position: Tuple[float, float],
                 animations: Dict[str, List[pygame.Surface]]) -> Entity:
    """Создает сущность туалета"""
    print("Создаем туалет")
    entity = create_interactive_object(groups, position, animations)
    
    entity.add_component(InteractionComponent(
        radius=60,
        text="Нажмите E чтобы использовать туалет"
    ))
    entity.add_component(ToiletComponent())
    entity.add_component(StateComponent({"is_occupied": False}))
    
    return entity

def create_wood(groups: List[pygame.sprite.Group],
                position: Tuple[float, float],
                animations: Dict[str, List[pygame.Surface]]) -> Entity:
    entity = create_interactive_object(groups, position, animations)
    entity.add_component(WoodComponent())
    return entity

