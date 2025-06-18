import pygame
from pygame.sprite import Group
from config import *
import random
from entity_component_system import ChairComponent
from pathfinding import astar
from config import TILE_SIZE, COLOURS
from item_renderer import get_item_sprite
from recipe_manager import recipe_manager

class BaseCharacter(pygame.sprite.Sprite):
    def __init__(self, game, scene, groups, pos, z, name):
        super().__init__(groups)
        self.groups = groups
        self.game = game
        self.scene = scene
        self.z = z
        self.name = name
        self.frame_index = 0
        self.animations = {}
        self.import_images(f'assets/characters/{self.name}/')
        
        self.image = self.animations.get('walk_left', [pygame.Surface((TILE_SIZE, TILE_SIZE))])[self.frame_index].convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.copy().inflate(-self.rect.width * 0.5, -self.rect.height * 0.5)
        self.speed = PLAYER_SPEED
        self.force = PLAYER_FORCE
        self.acc = vec()
        self.vel = vec()
        self.fric = PLAYER_FRICTION
        self.move = {'left': False, 'right': False, 'up': False, 'down': False}
        self.sit_down_trigger = False
        self.chair = None
        self.target = None
        self.state = None
        self.debug_target_pos = None

    def draw(self, screen, offset):
        screen.blit(self.image, self.rect.topleft - offset)
        if self.game.debug:
            if hasattr(self, 'hitbox'):
                offset_hitbox = self.hitbox.copy()
                offset_hitbox.topleft -= offset
                pygame.draw.rect(screen, (255, 0, 0), offset_hitbox, 2)
            if hasattr(self, 'debug_target_pos') and self.debug_target_pos:
                offset_target_pos = self.debug_target_pos - offset
                pygame.draw.circle(screen, (255, 0, 255), offset_target_pos, 5)

    def set_state(self, new_state_instance):
        if not self.state or self.state.__class__ != new_state_instance.__class__:
            self.state = new_state_instance

    def set_position(self, pos):
        self.rect.topleft = pos
        self.hitbox.center = self.rect.center

    def set_scene(self, scene, groups):
        self.scene = scene
        for group in self.groups:
            group.remove(self)
        self.groups = groups
        for group in groups:
            group.add(self)

    def import_images(self, path):
        self.animations = self.game.get_animations(path)
        for animation in self.animations.keys():
            full_path = path + animation
            original_images = self.game.get_images(full_path)
            self.animations[animation] = [
                pygame.transform.scale(img, (64, 64))
                for img in original_images
            ]

    def animate(self, state, fps, loop=True):
        animation_list = self.animations.get(state)
        if not animation_list:
            return

        self.frame_index += fps
        if self.frame_index >= len(animation_list):
            if loop:
                self.frame_index = 0
            else:
                self.frame_index = len(animation_list) - 1
        self.image = animation_list[int(self.frame_index)]

    def get_direction(self):
        if self.vel.magnitude() == 0:
            return getattr(self, '_last_direction', 'down')
            
        angle = self.vel.angle_to(vec(0, 1))
        angle = (angle + 360) % 360
        
        if 45 <= angle < 135: self._last_direction = 'right'
        elif 135 <= angle < 225: self._last_direction = 'up'
        elif 225 <= angle < 315: self._last_direction = 'left'
        else: self._last_direction = 'down'
        return self._last_direction


    def movement(self):
        if hasattr(self, 'state') and isinstance(self.state, Sitting):
            self.acc.x = 0
            self.acc.y = 0
            return
        
        if self.move['left']: self.acc.x = -self.force
        elif self.move['right']: self.acc.x = self.force
        else: self.acc.x = 0

        if self.move['up']: self.acc.y = -self.force
        elif self.move['down']: self.acc.y = self.force
        else: self.acc.y = 0

    def get_collide_list(self, group):
        return [sprite for sprite in group if self.hitbox.colliderect(sprite.hitbox)]

    def collisions(self, axis, group):
        for sprite in self.get_collide_list(group):
            if axis == 'x':
                if self.vel.x > 0: self.hitbox.right = sprite.hitbox.left
                if self.vel.x < 0: self.hitbox.left = sprite.hitbox.right
                self.rect.centerx = self.hitbox.centerx
            if axis == 'y':
                if self.vel.y > 0: self.hitbox.bottom = sprite.hitbox.top
                if self.vel.y < 0: self.hitbox.top = sprite.hitbox.bottom
                self.rect.centery = self.hitbox.centery

    def physics(self, dt, fric):
        self.acc.x += self.vel.x * fric
        self.vel.x += self.acc.x * dt
        self.hitbox.centerx += self.vel.x * dt
        self.rect.centerx = self.hitbox.centerx
        self.collisions('x', self.scene.block_sprites)

        self.acc.y += self.vel.y * fric
        self.vel.y += self.acc.y * dt
        self.hitbox.centery += self.vel.y * dt
        self.rect.centery = self.hitbox.centery
        self.collisions('y', self.scene.block_sprites)

        if self.vel.magnitude() > self.speed:
            self.vel = self.vel.normalize() * self.speed
            
    def sit(self, chair_entity):
        if not isinstance(self.state, Sitting):
            chair_comp = chair_entity.get_component(ChairComponent)
            if chair_comp and chair_comp.occupy(self):
                self.sit_down_trigger = True
                self.chair = chair_entity

    def update(self, dt):
        self.get_direction()
        
        new_state = self.state.update(self, dt)
        if new_state:
            self.set_state(new_state)


class NPC(BaseCharacter):
    def __init__(self, game, scene, groups, pos, z, name):
        super().__init__(game, scene, groups, pos, z, name)
        self.set_state(Idle(self))
        
class Guest(NPC):
    def __init__(self, game, scene, groups, pos, z, name='guest'):
        super().__init__(game, scene, groups, pos, z, name)
        self.order = None

    def draw(self, screen, offset):
        super().draw(screen, offset)

        if isinstance(self.state, WaitingForFood) and self.order:
            bubble_rect = pygame.Rect(0, 0, 36, 36)
            bubble_rect.centerx = self.rect.centerx
            bubble_rect.bottom = self.rect.top - 5

            offset_bubble_rect = bubble_rect.copy()
            offset_bubble_rect.topleft -= offset

            pygame.draw.ellipse(screen, COLOURS['white'], offset_bubble_rect)
            pygame.draw.ellipse(screen, COLOURS['black'], offset_bubble_rect, 2)

            item_sprite = get_item_sprite(self.order.item_id, size=32)
            if item_sprite:
                sprite_rect = item_sprite.get_rect(center=offset_bubble_rect.center)
                screen.blit(item_sprite, sprite_rect)

    def receive_food(self, item_id):
        if isinstance(self.state, WaitingForFood) and self.order and self.order.item_id == item_id:
            if hasattr(self.scene, 'room') and hasattr(self.scene.room, 'remove_order'):
                self.scene.room.remove_order(self)

            self.set_state(Eating(self, item_id))
            return True
        return False

    def interact(self, player):
        if isinstance(self.state, WaitingForFood) and self.order:
            ordered_item_id = self.order.item_id
            if player.inventory.has_item(ordered_item_id):
                if self.receive_food(ordered_item_id):
                    player.inventory.remove_item(ordered_item_id, 1)


class Idle:
    def __init__(self, character):
        character.frame_index = 0
        self.decision_timer = random.uniform(NPC_IDLE_MIN_TIME, NPC_IDLE_MAX_TIME)
        if hasattr(character, 'debug_target_pos'):
            character.debug_target_pos = None

    def update(self, character, dt):
        if character.sit_down_trigger:
            character.sit_down_trigger = False
            return Sitting(character)
        if character.vel.magnitude() > 2:
            return Walk(character)

        self.decision_timer -= dt
        if self.decision_timer <= 0:
            return FindingChair(character)

        character.animate(f'idle_{character.get_direction()}', ANIMATION_SPEED_IDLE * dt)
        character.movement()
        character.physics(dt, character.fric)
        return None

class Walk:
    def __init__(self, character):
        character.frame_index = 0

    def update(self, character, dt):
        if character.sit_down_trigger:
            character.sit_down_trigger = False
            return Sitting(character)
        if character.vel.magnitude() < 0.5:
            return Idle(character)

        character.animate(f'walk_{character.get_direction()}', ANIMATION_SPEED_WALK * dt)
        character.movement()
        character.physics(dt, character.fric)
        return None

class Sitting:
    def __init__(self, character):
        character.frame_index = 0
        self.sit_timer = random.uniform(NPC_SIT_MIN_TIME, NPC_SIT_MAX_TIME)
        
        if character.chair:
            character.rect.center = character.chair.rect.center
            character.hitbox.center = character.rect.center

            chair_comp = character.chair.get_component(ChairComponent)
            if chair_comp and chair_comp.table_id:
                table = next((obj for obj in character.scene.room.objects if hasattr(obj, 'id') and obj.id == chair_comp.table_id), None)
                if table:
                    direction_vec = pygame.math.Vector2(table.rect.center) - pygame.math.Vector2(character.rect.center)
                    if direction_vec.magnitude() > 0:
                        angle = direction_vec.angle_to(vec(0, 1))
                        angle = (angle + 360) % 360
                        
                        if 45 <= angle < 135: self._last_direction = 'right'
                        elif 135 <= angle < 225: self._last_direction = 'up'
                        elif 225 <= angle < 315: self._last_direction = 'left'
                        else: self._last_direction = 'down'

        if hasattr(character, 'debug_target_pos'):
            character.debug_target_pos = None

    def update(self, character, dt):
        self.sit_timer -= dt
        if self.sit_timer <= 0:
            return Ordering(character)

        direction = character.get_direction()
        character.animate(f'idle_{direction}', ANIMATION_SPEED_IDLE * dt, loop=False)
        return None

class Ordering:
    def __init__(self, character):
        character.frame_index = 0
        self.decision_timer = random.uniform(NPC_ORDERING_MIN_TIME, NPC_ORDERING_MAX_TIME)

    def update(self, character, dt):
        self.decision_timer -= dt
        if self.decision_timer <= 0:
            orderable_recipes = recipe_manager.get_orderable_recipes()
            if not orderable_recipes:
                return Idle(character)

            ordered_recipe_id = random.choice(list(orderable_recipes.keys()))
            recipe_details = orderable_recipes[ordered_recipe_id]
            ordered_item_id = recipe_details.get('result', ordered_recipe_id)

            if hasattr(character.scene, 'room') and hasattr(character.scene.room, 'add_order'):
                character.scene.room.add_order(character, ordered_item_id, ordered_recipe_id)
            
            return WaitingForFood(character)
        
        direction = character.get_direction()
        character.animate(f'idle_{direction}', ANIMATION_SPEED_IDLE * dt)
        return None

class WaitingForFood:
    def __init__(self, character):
        character.frame_index = 0

    def update(self, character, dt):
        direction = character.get_direction()
        character.animate(f'idle_{direction}', ANIMATION_SPEED_IDLE * dt)
        return None

class Eating:
    def __init__(self, character, food_item_id):
        character.frame_index = 0
        
        recipe = None
        if character.order and character.order.recipe_id:
            recipe = recipe_manager.get_recipe(character.order.recipe_id)

        cooking_time = recipe.get('cooking_time', 5) if recipe else 5
        self.eating_timer = cooking_time * NPC_EATING_TIME_MULTIPLIER
        
    def update(self, character, dt):
        self.eating_timer -= dt
        if self.eating_timer <= 0:
            if character.chair:
                chair_comp = character.chair.get_component(ChairComponent)
                if chair_comp:
                    chair_comp.vacate()
            character.chair = None
            return Leaving(character)

        direction = character.get_direction()
        character.animate(f'idle_{direction}', ANIMATION_SPEED_IDLE * dt, loop=False)
        return None

class Leaving:
    def __init__(self, character):
        character.target = None
        
    def update(self, character, dt):
        character.animate(f'idle_{character.get_direction()}', ANIMATION_SPEED_IDLE * dt)
        return None

class FindingChair:
    def __init__(self, character):
        character.frame_index = 0
        self.timer = NPC_FIND_CHAIR_TIMEOUT

    def update(self, character, dt):
        free_chair = character.scene.room.get_random_free_chair()
        if free_chair:
            character.target = free_chair
            return MovingToTarget(character)

        self.timer -= dt
        if self.timer <= 0:
            return Idle(character)
        return None
class MovingToTarget:
    def __init__(self, character):
        character.frame_index = 0
        self.path = []
        character.debug_target_pos = None

        if not hasattr(character, 'target') or not character.target:
            character.set_state(Idle(character)) 
            return

        
        grid = character.scene.room.grid
        sub_tile_size = character.scene.room.sub_tile_size
        
        start_pos_grid = (character.rect.centerx // sub_tile_size, character.rect.centery // sub_tile_size)
        
        target_center_pos = character.target.rect.center
        end_pos_grid = (target_center_pos[0] // sub_tile_size, target_center_pos[1] // sub_tile_size)
        
        character.debug_target_pos = pygame.math.Vector2(
            end_pos_grid[0] * sub_tile_size + sub_tile_size // 2,
            end_pos_grid[1] * sub_tile_size + sub_tile_size // 2
        )

        original_grid_value = grid[end_pos_grid[1]][end_pos_grid[0]]
        grid[end_pos_grid[1]][end_pos_grid[0]] = 0
        
        path_grid = astar(grid, start_pos_grid, end_pos_grid)

        grid[end_pos_grid[1]][end_pos_grid[0]] = original_grid_value
        
        if path_grid:
            if len(path_grid) > 1:
                path_grid.pop()

            self.path = [(x * sub_tile_size + sub_tile_size // 2, y * sub_tile_size + sub_tile_size // 2) for x, y in path_grid]

    def update(self, character, dt):
        if not character.target:
            return Idle(character)

        if self.path:
            target_pos = self.path[0]
            direction_vec = pygame.math.Vector2(target_pos) - pygame.math.Vector2(character.rect.center)

            sub_tile_size = character.scene.room.sub_tile_size
            if direction_vec.length() < sub_tile_size * 0.8:
                self.path.pop(0)
                if not self.path:
                    character.vel = vec(0, 0)
                    return None
            
            if self.path:
                character.acc = direction_vec.normalize() * character.force
                character.animate(f'walk_{character.get_direction()}', ANIMATION_SPEED_WALK * dt)
                character.physics(dt, character.fric)

                return None
        
        distance_to_target = (pygame.math.Vector2(character.target.rect.center) - pygame.math.Vector2(character.rect.center)).length()
        if distance_to_target < TILE_SIZE * 1.25:
            chair_comp = character.target.get_component(ChairComponent)
            if chair_comp and chair_comp.occupy(character):
                character.chair = character.target
                return Sitting(character)
            else:
                return Idle(character)
        else:
            return Idle(character)