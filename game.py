import pygame
from entities.room import room_manager
from config import WIN_WIDTH, WIN_HEIGHT, FONT, TILE_SIZE, INPUTS, PLAYER_STATE, reset_player_state
from core.game_time import game_time
from core.state import MainMenu,  load_pygame
import sys
from ui.drag_manager import drag_manager
from ui.ui_manager import ui_manager
import os
import shutil
import json


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
        self.debug = False
        
        self.states = []
        self._load_state()
        MainMenu(self).enter_state()

    def _load_state(self):
        if os.path.exists('save.json'):
            with open('save.json', 'r') as f:
                try:
                    save_data = json.load(f)
                    PLAYER_STATE.update(save_data)
                except json.JSONDecodeError:
                    reset_player_state()

    def new_game(self):
        reset_player_state()
        if os.path.exists('save.json'):
            os.remove('save.json')

        default_path = 'scenes/objects/defaults'
        target_path = 'scenes/objects'
        if os.path.exists(default_path):
            for filename in os.listdir(default_path):
                if filename.endswith('.json'):
                    shutil.copy(os.path.join(default_path, filename), os.path.join(target_path, filename))
        
        room_manager.rooms.clear()
        from core.state import Scene
        Scene(self, 'tavern', 'enter').enter_state()

    def load_game(self):
        if self.save_exists():
            last_scene = PLAYER_STATE.get('last_scene', 'tavern')
            last_entry = PLAYER_STATE.get('last_entry_point', 'enter')
            from core.state import Scene
            Scene(self, last_scene, last_entry).enter_state()

    def save_exists(self):
        return os.path.exists('save.json')

    def save_game(self):
        current_scene = self.get_current_state()
        from core.state import Scene
        if not isinstance(current_scene, Scene):
            return

        if hasattr(current_scene, 'player') and hasattr(current_scene.player, 'save_state'):
            current_scene.player.save_state()

        for room in room_manager.rooms.values():
            room.save_state()

        game_time.save_state()
        
        PLAYER_STATE['last_scene'] = current_scene.current_scene
        PLAYER_STATE['last_entry_point'] = current_scene.entry_point

        with open('save.json', 'w') as f:
            json.dump(PLAYER_STATE, f, indent=4)

    def load_tmx(self, scene_name: str):
        if scene_name not in self.tmx_cache:
            self.tmx_cache[scene_name] = load_pygame(f'scenes/maps/{scene_name}.tmx')
        return self.tmx_cache[scene_name]
    
    def render_text(self,text,colour,font,pos,centralised=True):
        surf = font.render(str(text),False,colour)
        rect = surf.get_rect(center = pos) if centralised else surf.get_rect(topleft = pos)
        self.screen.blit(surf,rect)

    def get_inputs(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()

            INPUTS['mouse_pos'] = pygame.mouse.get_pos()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    INPUTS['left_click'] = True
                if event.button == 3:
                    INPUTS['right_click'] = True

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
                

            
    def reset_inputs(self):
        for key in INPUTS:
            if key != 'mouse_pos':
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
            