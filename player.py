from character import BaseCharacter, Sitting
from inventory import Inventory
from config import *
import pygame
from entity_component_system import ChairComponent

class PlayerIdle:
    def __init__(self, player):
        player.frame_index = 0

    def update(self, player, dt):
        if player.sit_down_trigger:
            player.sit_down_trigger = False
            return PlayerSitting(player)
        if player.vel.magnitude() > 2:
            return PlayerWalk(player)

        player.animate(f'idle_{player.get_direction()}', ANIMATION_SPEED_IDLE * dt)
        player.movement()
        player.physics(dt, player.fric)
        return None

class PlayerWalk:
    def __init__(self, player):
        player.frame_index = 0

    def update(self, player, dt):
        if player.sit_down_trigger:
            player.sit_down_trigger = False
            return PlayerSitting(player)
        if player.vel.magnitude() < 0.5:
            return PlayerIdle(player)

        player.animate(f'walk_{player.get_direction()}', ANIMATION_SPEED_WALK * dt)
        player.movement()
        player.physics(dt * 1.5, player.fric)
        return None

class PlayerSitting(Sitting):
    def __init__(self, player):
        super().__init__(player)

    def update(self, player, dt):
        if INPUTS.get('space'):
             player.stand_up()
             INPUTS['space'] = False 
             return PlayerIdle(player)

        direction = player.get_direction()
        player.animate(f'idle_{direction}', ANIMATION_SPEED_IDLE * dt, loop=False)
        return None

class Player(BaseCharacter):
    _instance = None

    @classmethod
    def get_instance(cls, game=None, scene=None, groups=None, pos=(0, 0), z='characters', name='player'):
        if cls._instance is None:
            cls._instance = cls(game, scene, groups, pos, z, name)
        return cls._instance

    def __init__(self, game, scene, groups, pos,z, name):
        if hasattr(self, '_initialized'):
            return
        super().__init__(game, scene, groups, pos,z, name)
        
        self.state = None
        self.set_state(PlayerIdle(self))
        
        self.inventory = Inventory((5, 4))
        if PLAYER_STATE['first_spawn']:
            self.inventory.create_test_items()
        self.inventory.load_from_state()

        self.max_energy = PLAYER_STATE['max_energy']
        self.energy = PLAYER_STATE['energy']
        self.low_energy_threshold = PLAYER_LOW_ENERGY_THRESHOLD
        self.exhausted_threshold = PLAYER_EXHAUSTED_THRESHOLD
        
        self.sit_down_trigger = False
        self.chair = None
        self._initialized = True

    def set_state(self, new_state_instance):
        if not self.state or self.state.__class__ != new_state_instance.__class__:
            self.state = new_state_instance
   
    def save_state(self):
        PLAYER_STATE['energy'] = self.energy
        PLAYER_STATE['inventory'] = self.inventory.to_dict()

    def sit(self, chair_entity):
        if not isinstance(self.state, PlayerSitting):
            chair_comp = chair_entity.get_component(ChairComponent)
            if chair_comp and chair_comp.occupy(self):
                self.sit_down_trigger = True
                self.chair = chair_entity

    def stand_up(self):
        if self.chair:
            chair_comp = self.chair.get_component(ChairComponent)
            if chair_comp:
                chair_comp.vacate()
            self.chair = None

    def movement(self):
        energy_multiplier = self.get_energy_multiplier()
        effective_force = self.force * energy_multiplier
        
        if self.move['left']: self.acc.x = -effective_force
        elif self.move['right']: self.acc.x = effective_force
        else: self.acc.x = 0 
        
        if self.move['up']: self.acc.y = -effective_force
        elif self.move['down']: self.acc.y = effective_force
        else: self.acc.y = 0 

    def exit_scene(self):
        for exit in self.scene.exit_sprites:
            if exit.hitbox.colliderect(self.hitbox):
                self.scene.next_scene = SCENE_DATA[self.scene.current_scene][exit.name]
                self.scene.entry_point = exit.name + '_entry'
                self.scene.transition.exiting = True
                
    def interact_with_objects(self):
        if isinstance(self.state, PlayerSitting):
            return

        interactive_sprites = self.scene.interactive_sprites
        if not interactive_sprites:
            return

        try:
            nearest_obj = min(
                interactive_sprites,
                key=lambda obj: pygame.math.Vector2(self.rect.center).distance_to(obj.rect.center)
            )
        except ValueError:
            return

        interaction_distance = TILE_SIZE * INTERACTION_DISTANCE_MULTIPLIER 
        distance = pygame.math.Vector2(self.rect.center).distance_to(nearest_obj.rect.center)


        if distance < interaction_distance:
            if hasattr(nearest_obj, 'interact'):
                 nearest_obj.interact(self)
        
    def rest(self, amount=50):
        old_energy = self.energy
        self.energy = min(self.max_energy, self.energy + amount)
        restored = self.energy - old_energy
        PLAYER_STATE['energy'] = self.energy
        return restored
        
    def spend_energy(self, amount):
        if self.energy >= amount:
            self.energy -= amount
            PLAYER_STATE['energy'] = self.energy
            return True
        return False
        
    def get_energy_multiplier(self):
        if self.energy <= self.exhausted_threshold:
            return PLAYER_EXHAUSTED_MULTIPLIER
        elif self.energy <= self.low_energy_threshold:
            return PLAYER_LOW_ENERGY_MULTIPLIER
        else:
            return 1.0 

    def update(self, dt):
        self.input()
        self.exit_scene()
        
        new_state = self.state.update(self, dt)
        if new_state:
            self.set_state(new_state)

        self.inventory.update()

    def draw(self, screen, offset):
        screen.blit(self.image, self.rect.topleft - offset)
        if self.game.debug:
            offset_hitbox = self.hitbox.copy()
            offset_hitbox.topleft -= offset
            pygame.draw.rect(screen, (255, 0, 0), offset_hitbox, 2)
    
    def input(self):
        self.move = {'left': False, 'right': False, 'up': False, 'down': False}
        
        if not isinstance(self.state, PlayerSitting):
            if INPUTS.get('left'): self.move['left'] = True
            elif INPUTS.get('right'): self.move['right'] = True
            if INPUTS.get('up'): self.move['up'] = True
            elif INPUTS.get('down'): self.move['down'] = True

        if INPUTS.get('interact'):
            if not isinstance(self.state, PlayerSitting):
                self.interact_with_objects()
            else:
                self.stand_up() 
            INPUTS['interact'] = False
        
        if INPUTS.get('inventory'):
            self.inventory.visible = not self.inventory.visible
            INPUTS['inventory'] = False

