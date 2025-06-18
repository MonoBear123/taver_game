import pygame
import pygame.freetype
from config import *

class Camera(pygame.sprite.Group):
    def __init__(self,scene):
        super().__init__()
        self.scene = scene
        self.game = scene.game
        self.offset = vec()
        self.visible_window = pygame.Rect(0,0,WIN_WIDTH,WIN_HEIGHT)
        self.scene_size = self.get_scene_size(scene)
    def get_scene_size(self, scene):
        map_width = scene.tmx_data.width * scene.tmx_data.tilewidth
        map_height = scene.tmx_data.height * scene.tmx_data.tileheight
        return map_height, map_width
    def update(self,dt,target):
        self.offset.x = target.rect.centerx - WIN_WIDTH / 2
        self.offset.y = target.rect.centery - WIN_HEIGHT / 2

        self.offset.y = max(0,min(self.offset.y ,self.scene_size[0] - WIN_HEIGHT))
        self.offset.x = max(0,min(self.offset.x,self.scene_size[1] - WIN_WIDTH)) 

        self.visible_window.x = self.offset.x
        self.visible_window.y = self.offset.y
    def hitbox_debugger(self,screen,sprite):
        
            pygame.draw.rect(screen, (0, 255, 0), 
            pygame.Rect(sprite.rect.x - self.offset.x,
                    sprite.rect.y - self.offset.y,
                    sprite.rect.width,
                    sprite.rect.height), 1)
        
            
            if sprite.hitbox.width > 0 and sprite.hitbox.height > 0:
                pygame.draw.rect(screen, (255, 0, 0), 
                pygame.Rect(sprite.hitbox.x - self.offset.x,
                            sprite.hitbox.y - self.offset.y,
                            sprite.hitbox.width,
                            sprite.hitbox.height), 1)
                        


        
    def draw(self,screen):
        screen.fill(COLOURS['dark_gray'])
        
        group = self.scene.drawn_sprites
        dynamic_layers = ['objects', 'characters', 'interactive', 'decorations','windows']
        
        layer_order_map = {layer: i for i, layer in enumerate(LAYERS)}
        
        dynamic_layer_index = min(layer_order_map[layer] for layer in dynamic_layers if layer in layer_order_map)

        def sort_key(sprite):
            y_coord = sprite.rect.centery
            
            if sprite.z in dynamic_layers:
                return (dynamic_layer_index, y_coord)
            
            layer_index = layer_order_map.get(sprite.z, -1)
            return (layer_index, y_coord)

        for sprite in sorted(list(group), key=sort_key):
            if self.visible_window.colliderect(sprite.rect):
                if callable(sprite.draw):
                    sprite.draw(screen, self.offset)
                else:
                    offset_pos = sprite.rect.topleft - self.offset
                    screen.blit(sprite.image, offset_pos)

                if self.game.debug and sprite.z in dynamic_layers:
                    if hasattr(sprite, 'hitbox'):
                         self.hitbox_debugger(screen,sprite)
                        
                if self.game.debug and  sprite.debug_target_pos:
                    target_pos = sprite.debug_target_pos - self.offset
                    pygame.draw.circle(screen, (255, 0, 0), target_pos, 10)
