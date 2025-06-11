from character import NPC, INPUTS
from config import SCENE_DATA, PLAYER_STATE
from inventory import Inventory
import pygame

class Player(NPC):
    def __init__(self, game, scene, groups, pos,z, name):
        super().__init__(game, scene, groups, pos,z, name)
        self.state = Idle(self)
        
        self.max_energy = PLAYER_STATE['max_energy']
        if PLAYER_STATE['first_spawn']:
            self.energy = self.max_energy
            PLAYER_STATE['first_spawn'] = False
        else:
            self.energy = PLAYER_STATE['energy']
            
        self.low_energy_threshold = 20 
        self.exhausted_threshold = 5
        self.inventory = Inventory((5, 4))
        self.inventory.create_test_items()

    def movement(self):
        energy_multiplier = self.get_energy_multiplier()
        effective_force = self.force * energy_multiplier
        
        if INPUTS['left']:self.acc.x = -effective_force
        elif INPUTS['right']:self.acc.x = effective_force
        else:
            self.acc.x = 0 
        
        if INPUTS['up']:self.acc.y = -effective_force
        elif INPUTS['down']:self.acc.y = effective_force
        else:
            self.acc.y = 0 

    def exit_scene(self):
        for exit in self.scene.exit_sprites:
            if exit.hitbox.colliderect(self.hitbox):
                self.scene.next_scene = SCENE_DATA[self.scene.current_scene][exit.name]
                self.scene.entry_point = exit.name + '_entry'
                self.scene.transition.exiting = True
                
                
    def interact_with_objects(self):
        if INPUTS['interact']:
            interactive_objects = [
                obj for obj in self.scene.interactive_sprites 
                if obj.can_player_interact(self)
            ]
            
            if not interactive_objects:
                return
                
            nearest_obj = min(
                interactive_objects,
                key=lambda obj: pygame.math.Vector2(
                    obj.rect.centerx - self.rect.centerx,
                    obj.rect.centery - self.rect.centery
                ).length()
            )
            
            nearest_obj.interact(self)
            INPUTS['interact'] = False
    
        
    def rest(self, amount=50):
        old_energy = self.energy
        self.energy = min(self.max_energy, self.energy + amount)
        restored = self.energy - old_energy
        
        PLAYER_STATE['energy'] = self.energy
        return restored
        
        
    def get_energy_multiplier(self):
        if self.energy <= self.exhausted_threshold:
            return 0.3 
        elif self.energy <= self.low_energy_threshold:
            return 0.6 
        else:
            return 1.0 

    def change_state(self):
        if self.vel.magnitude() > 1:
            self.state = Walk(self)
        else:
            self.state = Idle(self)

    def update(self, dt):
        self.get_direction()
        self.exit_scene()
        self.interact_with_objects() 
        self.inventory.update()
        self.change_state()
        self.state.update(self, dt)

    def draw(self, screen):
        self.inventory.draw_all(screen)

class Idle:
    def __init__(self, player):
        self.frame_index = 0

    def enter_state(self, player):
        if player.vel.magnitude() > 1:
            return Walk(player)
    def update(self, player, dt):
        player.animate(f'idle_{player.get_direction()}', 15 * dt)
        player.movement()
        player.physics(dt, player.fric)
class Walk:
    def __init__(self, player):
        Idle.__init__(self, player)
    def enter_state(self, player):
        if player.vel.magnitude() <  1:
            return Idle(player) 
    def update(self, player, dt):
        player.animate(f'walk_{player.get_direction()}', 5 * dt)
        player.movement()
        player.physics(dt*1.5, player.fric)

