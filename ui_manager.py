import pygame
from config import COLOURS, FONT, PLAYER_STATE
from entity_component_system import StoveComponent, StorageComponent
from inventory import Inventory
from item_renderer import get_item_sprite, draw_item
from slot import InventorySlot
from game_time import game_time
from drag_manager import drag_manager


class UIManager:
    def __init__(self):
        self.screen = None 
        self.game_state = None
        self.time_font = None
        self.day_font = None
        self.item_font = None
        self._fonts_initialized = False

    def _initialize_fonts(self):
        if not self._fonts_initialized:
            self.time_font = pygame.font.Font(FONT, 12)
            self.day_font = pygame.font.Font(FONT, 24)
            self.item_font = pygame.font.Font(None, 12)
            self._fonts_initialized = True

    def set_context(self, screen, game_state):
        self.screen = screen
        self.game_state = game_state
        self._initialize_fonts()

    def draw(self):
        if not self.screen or not self.game_state or not hasattr(self.game_state, 'player'):
            return

        self._draw_time()
        self._draw_player_stats(self.game_state.player)
        
        self._draw_inventory(self.game_state.player.inventory)
        
        self._draw_component_uis(self.game_state)
        
        drag_manager.draw_cursor(self.screen)

    def _draw_time(self):
        time_str, day_str = game_time.get_time_string()
        self.game_state.game.render_text(day_str, COLOURS['white'], self.day_font, (570, 20), centralised=True)
        self.game_state.game.render_text(time_str, COLOURS['white'], self.time_font, (570, 40), centralised=True)
    
    def _draw_player_stats(self, player):
        energy_text = f"Energy: {int(player.energy)}"
        font = pygame.font.Font(FONT, 16)
        self.game_state.game.render_text(energy_text, COLOURS['white'], font, (570, 60), centralised=True)

    def _get_inventory_positions(self, inv: Inventory):
        if not self.screen: return None, None
        screen = self.screen
        
        if inv.inventory_type == 'player':
            hotbar_width = inv.width * (inv.SLOT_SIZE + inv.PADDING)
            hotbar_x = (screen.get_width() - hotbar_width) // 2
            hotbar_y = screen.get_height() - (inv.SLOT_SIZE + inv.PADDING + 20)
            
            inventory_width = inv.width * (inv.SLOT_SIZE + inv.PADDING)
            inventory_height = (inv.height - 1) * (inv.SLOT_SIZE + inv.PADDING)
            inventory_x = (screen.get_width() - inventory_width) // 2
            inventory_y = (screen.get_height() - inventory_height - (inv.SLOT_SIZE + inv.PADDING + 20)) // 2
            return (inventory_x, inventory_y), (hotbar_x, hotbar_y)

        elif inv.inventory_type == 'storage':
            inventory_width = inv.width * (inv.SLOT_SIZE + inv.PADDING)
            inventory_height = inv.height * (inv.SLOT_SIZE + inv.PADDING)
            inventory_x = (screen.get_width() - inventory_width) // 2
            inventory_y = (screen.get_height() - inventory_height) // 2 - 50
            return (inventory_x, inventory_y), None
            
        return None, None

    def _draw_inventory(self, inv: Inventory):
        main_pos, hotbar_pos = self._get_inventory_positions(inv)

        if main_pos and inv.visible:
            start_row, end_row = 0, inv.height
            if inv.inventory_type == 'player':
                end_row = inv.height - 1
            
            if inv.inventory_type == 'storage':
                bg_rect = pygame.Rect(
                    main_pos[0] - 10, main_pos[1] - 10, 
                    inv.width * (inv.SLOT_SIZE + inv.PADDING) + 12, 
                    inv.height * (inv.SLOT_SIZE + inv.PADDING) + 12
                )
                pygame.draw.rect(self.screen, (50, 50, 50), bg_rect)
                pygame.draw.rect(self.screen, (150, 150, 150), bg_rect, 2)
            
            self._draw_inventory_grid(inv, main_pos, start_row, end_row)

        if hotbar_pos and inv.inventory_type == 'player':
            self._draw_inventory_grid(inv, hotbar_pos, inv.height - 1, inv.height)


    def _draw_inventory_grid(self, inv: Inventory, pos: tuple, start_row: int, end_row: int):
        for y in range(start_row, end_row):
            for x in range(inv.width):
                slot_index = y * inv.width + x
                if slot_index >= len(inv.slots):
                    continue
                
                slot = inv.slots[slot_index]
                rect = pygame.Rect(
                    pos[0] + x * (inv.SLOT_SIZE + inv.PADDING),
                    pos[1] + (y - start_row) * (inv.SLOT_SIZE + inv.PADDING),
                    inv.SLOT_SIZE,
                    inv.SLOT_SIZE
                )
                
                is_hotbar = y == inv.height - 1
                bg_color = (70, 70, 70)
                pygame.draw.rect(self.screen, bg_color, rect)
                
                if slot_index == inv.selected_slot and inv.inventory_type == 'player':
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
                
                border_color = (120, 120, 120) if is_hotbar else (100, 100, 100)
                pygame.draw.rect(self.screen, border_color, rect, 1)
                
                if not slot.is_empty():
                    sprite = get_item_sprite(slot.item_id, inv.ITEM_SIZE)
                    if sprite:
                        scaled_sprite = pygame.transform.scale(sprite, (inv.ITEM_SIZE, inv.ITEM_SIZE))
                        
                        if slot.is_ghost:
                            scaled_sprite.set_alpha(100)
                        else:
                            scaled_sprite.set_alpha(255)

                        sprite_x = rect.x + (inv.SLOT_SIZE - inv.ITEM_SIZE) // 2
                        sprite_y = rect.y + (inv.SLOT_SIZE - inv.ITEM_SIZE) // 2
                        self.screen.blit(scaled_sprite, (sprite_x, sprite_y))
                        
                        if slot.amount > 1:
                            text = self.item_font.render(str(slot.amount), True, (255, 255, 255))
                            text_x = rect.right - text.get_width() - 1
                            text_y = rect.bottom - text.get_height()
                            self.screen.blit(text, (text_x, text_y))

    def _draw_cooking_interface(self, cooking_interface):
        if not cooking_interface or not cooking_interface.is_open:
            return
            
        pygame.draw.rect(self.screen, (100, 100, 100), cooking_interface.window_rect)

        for i, pos in enumerate(cooking_interface.slot_positions):
            rect = pygame.Rect(pos[0], pos[1], cooking_interface.slot_size, cooking_interface.slot_size)
            pygame.draw.rect(self.screen, (200, 200, 200), rect)
            slot_obj = cooking_interface.ingredient_slots[i]
            if not slot_obj.is_empty():
                draw_item(self.screen, slot_obj, rect, cooking_interface.font, is_ghost=slot_obj.is_ghost)

        rect = pygame.Rect(cooking_interface.result_slot_pos[0], cooking_interface.result_slot_pos[1], cooking_interface.slot_size, cooking_interface.slot_size)
        pygame.draw.rect(self.screen, (200, 200, 200), rect)
        if cooking_interface.result_item and not cooking_interface.result_item.is_empty():
            draw_item(self.screen, cooking_interface.result_item, rect, cooking_interface.font, is_ghost=cooking_interface.result_item.is_ghost)

        rect = pygame.Rect(cooking_interface.fuel_slot_pos[0], cooking_interface.fuel_slot_pos[1], cooking_interface.slot_size, cooking_interface.slot_size)
        pygame.draw.rect(self.screen, (200, 200, 200), rect)
        if cooking_interface.stove.fuel_slot_item_id:
            fuel_display_slot = cooking_interface.stove.ingredient_slots[0] # Re-use slot for display
            fuel_display_slot.item_id = cooking_interface.stove.fuel_slot_item_id
            fuel_display_slot.amount = 1
            draw_item(self.screen, fuel_display_slot, rect, cooking_interface.font)

        fuel_text = cooking_interface.font.render(f"Fuel: {cooking_interface.stove.fluid_amount}/{cooking_interface.stove.fluid_max_amount}", True, (255, 255, 255))
        self.screen.blit(fuel_text, (rect.x, rect.y + cooking_interface.slot_size + 5))

        if cooking_interface.stove.is_cooking:
            bg_color = (50, 50, 50)
            pygame.draw.rect(self.screen, bg_color, cooking_interface.progress_bar_rect)
            if cooking_interface.stove.cooking_time > 0:
                progress_ratio = 1.0 - (cooking_interface.stove.cooking_timer / cooking_interface.stove.cooking_time)
                fill_color = (0, 200, 0)
                progress_width = int(cooking_interface.progress_bar_rect.width * progress_ratio)
                progress_rect = pygame.Rect(cooking_interface.progress_bar_rect.x, cooking_interface.progress_bar_rect.y, progress_width, cooking_interface.progress_bar_rect.height)
                pygame.draw.rect(self.screen, fill_color, progress_rect)
            
            remaining_time = max(0, int(cooking_interface.stove.cooking_timer))
            time_text = cooking_interface.small_font.render(f"{remaining_time}", True, (255, 255, 255))
            text_rect = time_text.get_rect(center=cooking_interface.progress_bar_rect.center)
            self.screen.blit(time_text, text_rect)

        if cooking_interface.recipe_button_image:
            self.screen.blit(cooking_interface.recipe_button_image, cooking_interface.recipe_button_rect)
        else:
            pygame.draw.rect(self.screen, (0, 0, 200), cooking_interface.recipe_button_rect)
        
        if cooking_interface.show_recipes:
            self._draw_recipe_window(cooking_interface)

    def _draw_recipe_window(self, cooking_interface):
        pygame.draw.rect(self.screen, (150, 150, 150), cooking_interface.recipe_window_rect)
        recipes_list = list(cooking_interface.recipes.values()) if isinstance(cooking_interface.recipes, dict) else cooking_interface.recipes
        start_idx = cooking_interface.recipe_page * cooking_interface.recipes_per_page
        end_idx = start_idx + cooking_interface.recipes_per_page
        visible_recipes = recipes_list[start_idx:end_idx]

        cell_h = int(30 * cooking_interface.scale)
        icon_size = int(24 * cooking_interface.scale)

        for i, rec in enumerate(visible_recipes):
            y = cooking_interface.recipe_window_rect.y + int(5 * cooking_interface.scale) + i * cell_h
            res_x = cooking_interface.recipe_window_rect.x + int(5 * cooking_interface.scale)
            res_y = y + (cell_h - icon_size) // 2
            res_rect = pygame.Rect(res_x, res_y, icon_size, icon_size)
            draw_item(self.screen, InventorySlot(rec['result'], rec.get('amount', 1)), res_rect, cooking_interface.font)
            
            eq_text = cooking_interface.font.render('=', True, (0,0,0))
            eq_x = res_rect.right + int(5 * cooking_interface.scale)
            eq_y = y + (cell_h - eq_text.get_height()) // 2
            self.screen.blit(eq_text, (eq_x, eq_y))
            
            ing_start_x = eq_x + eq_text.get_width() + int(5 * cooking_interface.scale)
            for j, (ing_id, amount) in enumerate(rec['ingredients'].items()):
                ing_x = ing_start_x + j * (icon_size + int(4 * cooking_interface.scale))
                ing_y = y + (cell_h - icon_size) // 2
                ing_rect = pygame.Rect(ing_x, ing_y, icon_size, icon_size)
                draw_item(self.screen, InventorySlot(ing_id, amount), ing_rect, cooking_interface.font)
        
        pygame.draw.rect(self.screen, (100,100,220), cooking_interface.prev_button_rect)
        pygame.draw.rect(self.screen, (100,100,220), cooking_interface.next_button_rect)
        prev_text = cooking_interface.font.render('<', True, (0,0,0))
        next_text = cooking_interface.font.render('>', True, (0,0,0))
        self.screen.blit(prev_text, (cooking_interface.prev_button_rect.centerx - prev_text.get_width()//2, cooking_interface.prev_button_rect.centery - prev_text.get_height()//2))
        self.screen.blit(next_text, (cooking_interface.next_button_rect.centerx - next_text.get_width()//2, cooking_interface.next_button_rect.centery - next_text.get_height()//2))


    def _draw_component_uis(self, scene):
        if not hasattr(scene, 'update_sprites'):
            return
            
        for entity in scene.update_sprites:
            if not hasattr(entity, 'get_component'):
                continue
                
            stove_comp = entity.get_component(StoveComponent)
            if stove_comp and stove_comp.cooking_interface:
                self._draw_cooking_interface(stove_comp.cooking_interface)

            storage_comp = entity.get_component(StorageComponent)
            if storage_comp and storage_comp.is_open:
                self._draw_inventory(storage_comp.inventory) 

ui_manager = UIManager() 