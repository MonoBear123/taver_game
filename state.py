import pygame
from config import *
from camera import Camera
from player import Player
from pytmx.util_pygame import load_pygame
from transition import Transition
from room import room_manager, TavernRoom, KitchenRoom, ToiletRoom, RestRoom, Room
from entity_component_system import (
    Entity, SpriteComponent,
    CollisionComponent, ShapedCollisionComponent, StoveComponent,
    StorageComponent, ChairComponent
)
from object_factory import ObjectFactory

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
    

class MainMenu(State):
    def __init__(self, game):
        super().__init__(game)
        self.options = ["Продолжить", "Новая игра", "Выход"]
        self.selected_option = 0
        self.up_pressed = False
        self.down_pressed = False
        self.background_image = None
        try:
            self.background_image = pygame.image.load('assets/ui/main_menu_background.png').convert()
            self.background_image = pygame.transform.scale(self.background_image, (WIN_WIDTH, WIN_HEIGHT))
        except pygame.error:
            pass

    def update(self, dt):
        if INPUTS['up'] and not self.up_pressed:
            self.selected_option = (self.selected_option - 1) % len(self.options)
            self.up_pressed = True
        if not INPUTS['up']:
            self.up_pressed = False

        if INPUTS['down'] and not self.down_pressed:
            self.selected_option = (self.selected_option + 1) % len(self.options)
            self.down_pressed = True
        if not INPUTS['down']:
            self.down_pressed = False
            
        if INPUTS.get('interact') or INPUTS.get('space'):
            if self.selected_option == 0:
                pass
            elif self.selected_option == 1:
                Scene(self.game, 'tavern', 'enter').enter_state()
            elif self.selected_option == 2:
                self.game.running = False

    def draw(self, screen):
        if self.background_image:
            screen.blit(self.background_image, (0, 0))
        else:
            screen.fill(COLOURS['dark_purple'])

        for i, option in enumerate(self.options):
            color = COLOURS['green'] if i == self.selected_option else COLOURS['white']
            self.game.render_text(
                option,
                color,
                self.game.font,
                (WIN_WIDTH / 2, WIN_HEIGHT / 2 - 50 + i * 50)
            )

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
        self.factory = ObjectFactory(self)

        self.setup_player()
        self.room = self.setup_room()
        
        self.factory.create_from_tmx_layers()
        self.factory.create_from_room_data(self.room)
        
        self.adopt_room_npcs()
        print(self.room)

    def get_sprite_groups(self):
        return [self.update_sprites, self.drawn_sprites, self.block_sprites]

    def adopt_room_objects(self):
        if not self.room:
            return
        for obj in self.room.objects:
            if obj.has_component(ChairComponent):
                groups_to_add = [
                    self.interactive_sprites,
                    self.drawn_sprites,
                    self.update_sprites
                ]
            else:
                groups_to_add = [
                    self.interactive_sprites,
                    self.drawn_sprites,
                    self.update_sprites,
                    self.block_sprites
                ]
            obj.add(groups_to_add)

    def adopt_room_npcs(self):
        if hasattr(self.room, 'customers'):
            for npc in self.room.customers:
                npc.set_scene(self, [self.update_sprites, self.drawn_sprites, self.interactive_sprites])
        self.target = self.player
    def go_to_scene(self):
        
        self.player.save_state()
        for room in room_manager.rooms.values():
            room.save_state()
        Scene(self.game, self.next_scene, self.entry_point).enter_state()
        
    def setup_player(self):
        self.player = Player.get_instance(
            game=self.game,
            scene=self,
            groups=[self.update_sprites, self.drawn_sprites],
            pos=(0, 0), 
            z='characters',
            name='player'
        )
        self.player.set_scene(self, [self.update_sprites, self.drawn_sprites])
    def setup_room(self):
        room_classes = {
            "tavern": TavernRoom,
            "room1": RestRoom,
            "kitchen": KitchenRoom,
            "toilet": ToiletRoom
        }
        
        json_path = f'scenes/objects/{self.current_scene}.json'
        room_class = room_classes.get(self.current_scene, Room)
        
        return room_manager.get_room(
            json_path=json_path,
            scene=self,
            room_class=room_class
        )

    def recreate_room_objects(self):
        for sprite in self.interactive_sprites:
            sprite.kill()
        
        self.factory.create_from_room_data(self.room)

    def update(self, dt):
        self.update_sprites.update(dt)
        self.camera.update(dt, self.target)
        self.transition.update(dt)

        if self.room:
            self.room.update(dt)
        
          
        
        
    def draw(self, screen):
        self.camera.draw(screen=screen)
        self.transition.draw(screen)
        
    

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
    
    def generate_cosmetics(self):
        for x, y, image in self.tmx_data.get_layer_by_name("cosmetics").tiles():
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'objects', colorkey=(255, 255, 255))
    
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
            pixel_array = pygame.PixelArray(image)
            pixel_array.replace((255, 255, 255), (0, 94, 162))
            del pixel_array
            self.create_basic_entity((x*TILE_SIZE, y*TILE_SIZE), image, 'windows', colorkey=(0, 94, 162))
    
    
    def generate_decorations(self):
        for x, y, image in self.tmx_data.get_layer_by_name('decorations').tiles():
            mask = pygame.mask.from_surface(image)
            if mask.count() > 0:
                self.create_basic_entity(
                    (x*TILE_SIZE, y*TILE_SIZE),
                    image,
                    'decorations',
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