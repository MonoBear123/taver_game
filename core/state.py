import pygame
from config import *
from core.camera import Camera
from pytmx.util_pygame import load_pygame
from core.transition import Transition
from entities.room import room_manager, TavernRoom, KitchenRoom, ToiletRoom, RestRoom, Room
from entities.object_factory import ObjectFactory

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

class MainMenu(State):
    def __init__(self, game):
        super().__init__(game)
        self.background_image = pygame.image.load('assets/ui/main_menu_background.png').convert()
        self.background_image = pygame.transform.scale(self.background_image, (WIN_WIDTH, WIN_HEIGHT))

        self.button_font = pygame.font.Font(FONT, 32)
        self.button_texts = ["Продолжить", "Новая Игра", "Выход"]
        self.button_enabled = [True, True, True]
        
        self.selected_button_index = 0
        if not self.game.save_exists():
            self.button_enabled[0] = False
            self.selected_button_index = 1

    def update(self, dt):
        if INPUTS.get('down'):
            next_index = self.selected_button_index + 1
            while next_index < len(self.button_texts) and not self.button_enabled[next_index]:
                next_index += 1
            
            if next_index < len(self.button_texts):
                self.selected_button_index = next_index
            self.game.reset_inputs()

        if INPUTS.get('up'):
            prev_index = self.selected_button_index - 1
            while prev_index >= 0 and not self.button_enabled[prev_index]:
                prev_index -= 1
            
            if prev_index >= 0:
                self.selected_button_index = prev_index
            self.game.reset_inputs()

        if INPUTS.get('space') or INPUTS.get('interact'):
            selected_text = self.button_texts[self.selected_button_index]
            self.handle_button_press(selected_text)
            self.game.reset_inputs()

    def handle_button_press(self, text):
        if text == "Продолжить":
            if self.game.save_exists():
                self.game.load_game()
        elif text == "Новая Игра":
            self.game.new_game()
        elif text == "Выход":
            self.game.running = False

    def draw(self, screen):
        screen.blit(self.background_image, (0, 0))

        total_height = len(self.button_texts) * 60
        start_y = (WIN_HEIGHT - total_height) / 2

        for i, text in enumerate(self.button_texts):
            color = COLOURS['white']
            if not self.button_enabled[i]:
                color = COLOURS['dark_gray']
            elif i == self.selected_button_index:
                color = COLOURS['green']

            pos = (WIN_WIDTH / 2, start_y + i * 60)
            self.game.render_text(text, color, self.button_font, pos)


class Scene(State):
    def __init__(self, game, current_scene, entry_point):
        State.__init__(self, game)
        self.current_scene = current_scene
        self.entry_point = entry_point
        self.tmx_data = self.game.load_tmx(self.current_scene)

        self.drawn_sprites = pygame.sprite.Group()
        self.exit_sprites = pygame.sprite.Group()
        self.block_sprites = pygame.sprite.Group()
        
        self.camera = Camera(self)
        self.transition = Transition(self)
        self.factory = ObjectFactory(self)

        self.room = self.setup_room()
        self.player = self.factory.create_player()
        self.target = self.player
        self.drawn_sprites.add(self.player)
        
        self.factory.create_from_tmx_layers()
        self.factory.create_from_room_data()
        
    def get_sprite_groups(self):
        return [self.drawn_sprites, self.block_sprites]

    def go_to_scene(self):
        
        self.player.save_state()
        for room in room_manager.rooms.values():
            room.save_state()
        Scene(self.game, self.next_scene, self.entry_point).enter_state()
        
    

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
        self.room.objects.clear()
        self.factory.create_from_room_data()

    def update(self, dt):
        self.player.inventory.update()
        self.drawn_sprites.update(dt)
        self.camera.update(dt, self.target)
        self.transition.update(dt)

        if self.room:
            self.room.update(dt)
        
            self.block_sprites.empty()
            self.block_sprites.add(self.room.get_blocking_sprites())
            self.block_sprites.add(self.player)
            
        
    def draw(self, screen):
        all_sprites = list(self.drawn_sprites) + self.room.get_drawable_sprites()
        self.camera.draw(screen, all_sprites)
        self.transition.draw(screen)
        
 