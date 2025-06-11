import pygame
from config import *

from pytmx.util_pygame import load_pygame
from camera import Camera
from player import Player
from transition import Transition
from room import TavernRoom, KitchenRoom, ToiletRoom
from entity_component_system import (
    Entity, SpriteComponent,
    CollisionComponent, ShapedCollisionComponent
)

class State:
    def __init__(self,game):
        self.game = game
        self.prev_state = None

    def enter_state(self):
        if len(self.game.states) > 1:
            self.prev_state = self.game.states[-1]
        self.game.states.append(self)
    def exit_state(self):
        self.game.states.pop()
    def update(self,dt):
        pass

    def draw(self,screen):
        pass


class SplashScreen(State):
    def __init__(self,game):
        State.__init__(self, game)



    def update(self,dt):
        if INPUTS['space']:
            Scene(self.game, 'tavern', 'enter').enter_state()
            self.game.reset_inputs()

    def draw(self,screen):
        screen.fill(COLOURS['green'])
        self.game.render_text("Tavern",COLOURS['white'],self.game.font,(WIN_WIDTH/2,WIN_HEIGHT/2))
    

class Scene(State):
    def __init__(self, game, current_scene, entry_point):
        State.__init__(self, game)
        self.current_scene = current_scene
        self.entry_point = entry_point
        self.tmx_data = self.game.load_tmx(self.current_scene)
        self.exit_sprites = pygame.sprite.Group()
        self.update_sprites = pygame.sprite.Group()
        self.drawn_sprites = pygame.sprite.Group()
        self.block_sprites = pygame.sprite.Group()
        self.interactive_sprites = pygame.sprite.Group()
        self.camera = Camera(self)
        self.transition = Transition(self)

        self.setup_player()
        self.create_scene()
        self.room = self.create_room()

    def setup_player(self):
        print("setup_player")
        self.player = Player.get_instance(
            game=self.game,
            scene=self,
            groups=[self.update_sprites, self.drawn_sprites],
            pos=(0, 0), 
            z='characters',
            name='player'
        )
        self.player.set_scene(self, [self.update_sprites, self.drawn_sprites])
        self.target = self.player
    def go_to_scene(self):
        self.room.save_state()
        self.player.save_state()
        Scene(self.game, self.next_scene, self.entry_point).enter_state()
        
    def create_room(self):
        room_classes = {
            "tavern": TavernRoom,
            "room1": TavernRoom,
            "kitchen": KitchenRoom,
            "toilet": ToiletRoom
        }
        
        json_path = f'scenes/objects/{self.current_scene}.json'
        return room_classes[self.current_scene](json_path, self)
    def create_scene(self):
        generator = ObjectGenerator(self)
        layer_handlers = {
            'background': generator.generate_background,
            'decorations': generator.generate_decorations,
            'objects': generator.generate_objects,
            'walls': generator.generate_objects,
            'lighting': generator.generate_lighting,
            'windows': generator.generate_windows,
            'foreground': generator.generate_foreground,
            'enteries': generator.generate_enteries,
            'exits': generator.generate_exits
        }
        for layer in self.tmx_data.layers:
            layer_handlers[layer.name]()
        


    def update(self, dt):
        self.update_sprites.update(dt)
        self.exit_sprites.update(dt)
        self.camera.update(dt, self.target)
        self.transition.update(dt)  
        self.room.update(dt)
        
        
    def draw(self, screen):
        self.camera.draw(screen=screen, group=self.drawn_sprites)
        self.transition.draw(screen)
        self.player.draw(screen)
        
    

class ObjectGenerator:
    def __init__(self, scene):
        self.scene = scene
        self.tmx_data = scene.tmx_data
        
    def create_basic_entity(self, pos, image, layer, use_collision=False, shaped_collision=False, colorkey=None):
        
        groups = [self.scene.drawn_sprites]
        if use_collision:
            groups.append(self.scene.block_sprites)
            groups.append(self.scene.update_sprites)
            
        entity = Entity(groups)
        
        sprite = SpriteComponent(image, pos, layer, colorkey)
        entity.add_component(sprite)
        if use_collision:
            if shaped_collision:
                entity.add_component(ShapedCollisionComponent())
            else:
                entity.add_component(CollisionComponent())
        
        return entity
        
    def generate_background(self):
        for x, y, image in self.tmx_data.get_layer_by_name("background").tiles():
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'background')
    
    def generate_decorations(self):
        for x, y, image in self.tmx_data.get_layer_by_name("decorations").tiles():
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'decorations', colorkey=(255, 255, 255))
    
    def generate_objects(self):
        if "walls" in [layer.name for layer in self.tmx_data.layers]:
            for x, y, image in self.tmx_data.get_layer_by_name("walls").tiles():
                mask = pygame.mask.from_surface(image)
                if mask.count() > 0:
                    self.create_basic_entity(
                        (x*TILE_SIZE, y*TILE_SIZE), 
                        image, 
                        'objects',
                        use_collision=True,
                        shaped_collision=True
                    )
        
        if "objects" in [layer.name for layer in self.tmx_data.layers]:
            for x, y, image in self.tmx_data.get_layer_by_name("objects").tiles():
                mask = pygame.mask.from_surface(image)
                if mask.count() > 0:
                    self.create_basic_entity(
                        (x*TILE_SIZE, y*TILE_SIZE), 
                        image, 
                        'objects',
                        use_collision=True,
                        shaped_collision=True
                    )
    

    
    def generate_lighting(self):
        for x, y, image in self.tmx_data.get_layer_by_name("lighting").tiles():
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'lighting')
    
    def generate_windows(self):
        for x, y, image in self.tmx_data.get_layer_by_name("windows").tiles():
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'windows', colorkey=(0, 94, 162))
    
    
    def generate_foreground(self):
        for x, y, image in self.tmx_data.get_layer_by_name("foreground").tiles():
            mask = pygame.mask.from_surface(image)
            if mask.count() > 0:
                self.create_basic_entity(
                    (x*TILE_SIZE, y*TILE_SIZE),
                    image,
                    'foreground',
                    use_collision=True,
                    shaped_collision=True,
                    colorkey=(255, 255, 255)
                )
    
    
    
    def generate_enteries(self):
        for obj in self.tmx_data.get_layer_by_name("enteries"):
            if obj.name == self.scene.entry_point:
                self.scene.player.set_position((obj.x, obj.y))
                
    
    def generate_exits(self):
        for obj in self.tmx_data.get_layer_by_name("exits"):
            entity = Entity([self.scene.exit_sprites, self.scene.update_sprites])
            
            exit_surface = pygame.Surface((obj.width, obj.height))
            exit_surface.set_alpha(0)
            
            entity.add_component(SpriteComponent(exit_surface, (obj.x, obj.y)))
            entity.add_component(CollisionComponent(shrink_hitbox=False))
            entity.name = obj.name