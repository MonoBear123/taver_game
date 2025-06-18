import pygame
from room import room_manager
from config import WIN_WIDTH, WIN_HEIGHT, FONT, TILE_SIZE, CURSOR_SIZE, INPUTS, COLOURS
from game_time import game_time
from state import SplashScreen, load_pygame, MainMenu
import sys
import os
from drag_manager import drag_manager
from ui_manager import ui_manager
from recipe_manager import recipe_manager
from item_manager import item_manager
from player import Player


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_WIDTH,WIN_HEIGHT),pygame.FULLSCREEN|pygame.SCALED)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(FONT,TILE_SIZE)
        self.running = True
        self.fps = 60
        self.states = []
        self.tmx_cache = {}
        self.debug = True

        self.states = []
        MainMenu(self).enter_state()

    def save_game(self):
        """Централизованная функция сохранения игры."""
        # Сохранение состояния игрока
        player = Player.get_instance()
        if player:
            player.save_state()

        # Сохранение состояния всех комнат
        for room in room_manager.rooms.values():
            room.save_state()

        # Сохранение игрового времени
        game_time.save_state()
        
        # Сохранение текущей сцены, чтобы знать, куда вернуться
        current_scene = self.get_current_state()
        if hasattr(current_scene, 'current_scene'):
            from config import PLAYER_STATE
            PLAYER_STATE['last_scene'] = current_scene.current_scene

        print("--- ИГРА СОХРАНЕНА ---")

    def load_tmx(self, scene_name: str):
        if scene_name not in self.tmx_cache:
            self.tmx_cache[scene_name] = load_pygame(f'scenes/maps/{scene_name}.tmx')
        return self.tmx_cache[scene_name]
    
    def render_text(self,text,colour,font,pos,centralised=True):
        surf = font.render(str(text),False,colour)
        rect = surf.get_rect(center = pos) if centralised else surf.get_rect(topleft = pos)
        self.screen.blit(surf,rect)

    def custom_cursor(self,screen):
        pygame.mouse.set_visible(False)
        cursor_img = pygame.image.load('assets/cursor.png') 
        cursor_img = pygame.transform.scale(cursor_img,CURSOR_SIZE)
        cursor_rect = cursor_img.get_rect(center=pygame.mouse.get_pos())
        cursor_img.set_alpha(200)
        screen.blit(cursor_img,cursor_rect.center)

    def get_images(self,path):
        images = []
        for file in os.listdir(path):
            full_path = os.path.join(path,file)
            img = pygame.image.load(full_path).convert_alpha()
            images.append(img)
        return images
    
    def get_animations(selt,path):
        animations = {}
        for file_name in os.listdir(path):
            animations.update({file_name:[]})
        return animations

    def get_inputs(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()

            INPUTS['mouse_pos'] = pygame.mouse.get_pos()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    INPUTS['escape'] = True
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    INPUTS['space'] = True
                elif event.key == pygame.K_TAB:
                    INPUTS['tab'] = True
                elif event.key in (pygame.K_LEFT,pygame.K_a):
                    INPUTS['left'] = True
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    INPUTS['right'] = True
                elif event.key in  (pygame.K_UP, pygame.K_w):
                    INPUTS['up'] = True
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    INPUTS['down'] = True
                elif event.key == pygame.K_e:
                    INPUTS['interact'] = True
                elif event.key == pygame.K_1:
                    INPUTS["1"] = True
                elif event.key == pygame.K_2:
                    INPUTS["2"] = True
                elif event.key == pygame.K_3:
                    INPUTS["3"] = True
                elif event.key == pygame.K_4:
                    INPUTS["4"] = True
                elif event.key == pygame.K_5:
                    INPUTS["5"] = True

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    INPUTS['space'] = False
                elif event.key == pygame.K_TAB:
                    INPUTS['tab'] = False
                elif event.key in (pygame.K_LEFT,pygame.K_a):
                    INPUTS['left'] = False
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    INPUTS['right'] = False
                elif event.key in  (pygame.K_UP, pygame.K_w):
                    INPUTS['up'] = False
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    INPUTS['down'] = False
                elif event.key == pygame.K_e:
                    INPUTS['interact'] = False
                elif event.key == pygame.K_1:
                    INPUTS["1"] = False
                elif event.key == pygame.K_2:
                    INPUTS["2"] = False
                elif event.key == pygame.K_3:
                    INPUTS["3"] = False
                elif event.key == pygame.K_4:
                    INPUTS["4"] = False
                elif event.key == pygame.K_5:
                    INPUTS["5"] = False

            if event.type == pygame.MOUSEWHEEL:
                if event.y == 1:
                    INPUTS['scroll_up'] = True
                if event.y == -1:
                    INPUTS['scroll_down'] = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    INPUTS['left_click'] = True
                if event.button == 2:
                    INPUTS['scroll_up'] = True
                if event.button == 3:
                    INPUTS['right_click'] = True
                if event.button == 4:
                    INPUTS['scroll_down'] = True

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    INPUTS['left_click'] = False
                if event.button == 2:
                    INPUTS['scroll_up'] = False    
                if event.button == 3:
                    INPUTS['right_click'] = False
                if event.button == 4:
                    INPUTS['scroll_down'] = False

    def reset_inputs(self):
        for key in INPUTS:
            INPUTS[key] = False

    def loop(self):
        while self.running:
            dt = self.clock.tick(self.fps)/1000
            game_time.update(dt)
            self.get_inputs()
            drag_manager.update()
            room_manager.update_all_rooms(dt)
            
            current_state = self.get_current_state()
            current_state.update(dt)
            
            self.screen.fill(COLOURS['black'])
            
            ui_manager.set_context(self.screen, current_state)
            
            current_state.draw(self.screen)
            ui_manager.draw()
            
            pygame.display.flip()

    def get_current_state(self):
        if not self.states:
            return None
        return self.states[-1]


if __name__ == "__main__":
    game = Game()
    game.loop()        
            