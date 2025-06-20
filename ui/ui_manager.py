import pygame
from config import COLOURS, FONT, PLAYER_STATE, CURSOR_SIZE
from core.entity_component_system import StoveComponent, StorageComponent, PlayerStatsComponent, ThoughtBubbleComponent
from items.inventory import Inventory
from items.slot import InventorySlot
from core.game_time import game_time
from ui.drag_manager import drag_manager
from items.item_manager import item_manager


class UIManager:
    def __init__(self):
        self.screen = None 
        self.context = None
        self.time_font = None
        self.day_font = None
        self.item_font = None
        self.cursor_img = None
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            self.time_font = pygame.font.Font(FONT, 12)
            self.day_font = pygame.font.Font(FONT, 24)
            self.item_font = pygame.font.Font(None, 12)
            self.energy_font = pygame.font.Font(FONT, 16)
            self.cursor_img = pygame.image.load('assets/cursor.png').convert_alpha()
            self.cursor_img = pygame.transform.scale(self.cursor_img, CURSOR_SIZE)
            self.cursor_img.set_alpha(200)
            pygame.mouse.set_visible(False)
            self._initialized = True

    def set_context(self, screen, context):
        self.screen = screen
        self.context = context
        self._initialize()

    def draw(self):
        if not self.screen or not self.context or not hasattr(self.context, 'player'):
            return

        self._draw_time()
        self._draw_player_stats(self.context.player)
        self._draw_inventory(self.context.player.inventory)
        
        if hasattr(self.context, 'room'):
            self._draw_component_ui(self.context.room)
            self.draw_thought_bubbles(self.context.room.npcs)
            

        self._draw_custom_cursor()
        drag_manager.draw_cursor(self.screen)

    def _draw_custom_cursor(self):
        if self.cursor_img:
            cursor_rect = self.cursor_img.get_rect(center=pygame.mouse.get_pos())
            self.screen.blit(self.cursor_img, cursor_rect)

    def _draw_time(self):
        time_str, day_str = game_time.get_time_string()
        self.context.game.render_text(day_str, COLOURS['white'], self.day_font, (570, 20))
        self.context.game.render_text(time_str, COLOURS['white'], self.time_font, (570, 40))
    
    def _draw_player_stats(self, player):
        stats_comp = player.get_component(PlayerStatsComponent)
        if stats_comp:
            energy_text = f"Energy: {int(stats_comp.energy)}"
            self.context.game.render_text(energy_text, COLOURS['white'], self.energy_font, (570, 60))



    def _draw_inventory(self, inv):
        main_pos, hotbar_pos = inv._get_inventory_positions(inv)
        if inv.inventory_type == 'player' and hotbar_pos:
            self._draw_hotbar(inv, hotbar_pos)
        if main_pos and (inv.inventory_type != 'player' or inv.visible):
            self._draw_main_inventory(inv, main_pos)

        
    def _draw_hotbar(self, inv, pos):
        hotbar_row = inv.height - 1 
        for x in range(inv.width):
            slot_index = hotbar_row * inv.width + x
            if slot_index >= len(inv.slots):
                continue

            slot = inv.slots[slot_index]
            rect = pygame.Rect(
                pos[0] + x * (inv.SLOT_SIZE + inv.PADDING),
                pos[1],
                inv.SLOT_SIZE,
                inv.SLOT_SIZE

            )
            self._draw_slot(slot, rect, self.item_font)

    def _draw_main_inventory(self, inv, pos):
        rows_to_draw = inv.height - 1 if inv.inventory_type == 'player' else inv.height
        
        if inv.inventory_type == 'storage':
            bg_rect = pygame.Rect(
                pos[0] - 8, pos[1] - 8,
                inv.width * (inv.SLOT_SIZE + inv.PADDING) + 12,
                rows_to_draw * (inv.SLOT_SIZE + inv.PADDING) + 12
            )
            pygame.draw.rect(self.screen, COLOURS['gray'], bg_rect)
            pygame.draw.rect(self.screen, COLOURS['dark_gray'], bg_rect, 2)
        
        for y in range(rows_to_draw):
            for x in range(inv.width):
                slot_index = y * inv.width + x
                if slot_index >= len(inv.slots):
                    continue
                    
                slot = inv.slots[slot_index]
                rect = pygame.Rect(
                    pos[0] + x * (inv.SLOT_SIZE + inv.PADDING),
                    pos[1] + y * (inv.SLOT_SIZE + inv.PADDING),
                    inv.SLOT_SIZE,
                    inv.SLOT_SIZE
                )
                self._draw_slot(slot, rect, self.item_font)

    def _draw_slot(self, slot_obj, rect, font):
        pygame.draw.rect(self.screen, COLOURS['light_gray'], rect)
        pygame.draw.rect(self.screen, COLOURS['dark_gray'], rect, 1) # Border
        if slot_obj and not slot_obj.is_empty():
            self._draw_item(slot_obj, rect, font)
            
    def _centered_text(self, text_surf, rect):
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def _draw_item(self, item_slot, rect, font):
        if not item_slot or item_slot.is_empty():
            return

        sprite = item_manager.get_sprite(item_slot.item_id, (Inventory.ITEM_SIZE,Inventory.ITEM_SIZE))
        if not sprite:
            return

        is_ghost = getattr(item_slot, 'is_ghost', False)
        if is_ghost:
            sprite.set_alpha(100)
        else:
            sprite.set_alpha(255) 

        item_rect = sprite.get_rect(center=rect.center)
        self.screen.blit(sprite, item_rect)

        if item_slot.amount > 1:
            text_surf = font.render(str(item_slot.amount), True, COLOURS['white'])
            text_rect = text_surf.get_rect(bottomright=(rect.right - 2, rect.bottom - 2))
            self.screen.blit(text_surf, text_rect)

    def draw_text(self, text, pos, font_size=16, color=COLOURS['white']):
        font = pygame.font.Font(FONT, font_size)
        surf = font.render(text, True, color)
        self.screen.blit(surf, pos)

    def _draw_cooking_interface(self, cooking_interface):
        if not cooking_interface or not cooking_interface.is_open:
            return

        pygame.draw.rect(self.screen, COLOURS['gray'], cooking_interface.window_rect)

        for i, pos in enumerate(cooking_interface.slot_positions):
            rect = pygame.Rect(*pos, cooking_interface.slot_size, cooking_interface.slot_size)
            self._draw_slot(cooking_interface.ingredient_slots[i], rect, cooking_interface.font)

        result_rect = pygame.Rect(*cooking_interface.result_slot_pos, cooking_interface.slot_size, cooking_interface.slot_size)
        self._draw_slot(cooking_interface.result_item, result_rect, cooking_interface.font)

        fuel_rect = pygame.Rect(*cooking_interface.fuel_slot_pos, cooking_interface.slot_size, cooking_interface.slot_size)
        self._draw_slot(cooking_interface.stove.ingredient_slots[0], fuel_rect, cooking_interface.font)

        fuel_text = cooking_interface.font.render(
            f"Fuel: {cooking_interface.stove.fluid_amount}/{cooking_interface.stove.fluid_max_amount}",
            True, COLOURS['white']
        )
        self.screen.blit(fuel_text, (fuel_rect.x, fuel_rect.y + cooking_interface.slot_size + 5))

        if cooking_interface.stove.is_cooking and cooking_interface.stove.cooking_time > 0:
            pygame.draw.rect(self.screen, COLOURS['gray'], cooking_interface.progress_bar_rect)
            ratio = 1.0 - cooking_interface.stove.cooking_timer / cooking_interface.stove.cooking_time
            width = int(cooking_interface.progress_bar_rect.width * ratio)
            progress_rect = cooking_interface.progress_bar_rect.copy()
            progress_rect.width = width
            pygame.draw.rect(self.screen, COLOURS['green'], progress_rect)

        if cooking_interface.recipe_button_image:
            self.screen.blit(cooking_interface.recipe_button_image, cooking_interface.recipe_button_rect)
        else:
            pygame.draw.rect(self.screen, COLOURS['dark_gray'], cooking_interface.recipe_button_rect)

        if cooking_interface.show_recipes:
            self._draw_recipe_window(cooking_interface)

    def _draw_recipe_window(self, cooking_interface):
        pygame.draw.rect(self.screen, COLOURS['light_gray'], cooking_interface.recipe_window_rect)

        recipes = list(cooking_interface.recipes.values()) if isinstance(cooking_interface.recipes, dict) else cooking_interface.recipes
        visible_recipes = recipes[cooking_interface.recipe_page * cooking_interface.recipes_per_page : (cooking_interface.recipe_page + 1) * cooking_interface.recipes_per_page]

        cell_h = 30
        icon_size = 24  
        margin = 5
        spacing = 4

        for i, recipe in enumerate(visible_recipes):
            y = cooking_interface.recipe_window_rect.y + margin + i * cell_h

            res_x = cooking_interface.recipe_window_rect.x + margin
            res_rect = pygame.Rect(res_x, y + (cell_h - icon_size) // 2, icon_size, icon_size)
            self._draw_slot(InventorySlot(recipe['result'], recipe.get('amount', 1)), res_rect, cooking_interface.font)

            eq_text = cooking_interface.font.render('=', True, COLOURS['black'])
            eq_x = res_rect.right + spacing
            eq_y = y + (cell_h - eq_text.get_height()) // 2
            self.screen.blit(eq_text, (eq_x, eq_y))

            ing_start_x = eq_x + eq_text.get_width() + spacing
            for j, (ing_id, amount) in enumerate(recipe['ingredients'].items()):
                ing_x = ing_start_x + j * (icon_size + spacing)
                ing_y = y + (cell_h - icon_size) // 2
                ing_rect = pygame.Rect(ing_x, ing_y, icon_size, icon_size)
                self._draw_slot(InventorySlot(ing_id, amount), ing_rect, cooking_interface.font)


    def _draw_component_ui(self, room):
        if not hasattr(room, 'objects'):
            return
            
        for entity in room.objects:
            if not hasattr(entity, 'get_component'):
                continue
                
            stove_comp = entity.get_component(StoveComponent)
            if stove_comp and stove_comp.cooking_interface:
                self._draw_cooking_interface(stove_comp.cooking_interface)

            storage_comp = entity.get_component(StorageComponent)
            if storage_comp and storage_comp.is_open:
                self._draw_inventory(storage_comp.inventory)

    def draw_thought_bubbles(self, npcs):
        camera = self.context.camera
        for npc in npcs:
            if thought_bubble := npc.get_component(ThoughtBubbleComponent):
                if thought_bubble.visible and thought_bubble.item_image:
                    on_screen_npc_pos = pygame.Vector2(npc.rect.topleft) - camera.offset
                    
                    pos_x = on_screen_npc_pos.x + npc.rect.width / 2 + thought_bubble.offset[0]
                    pos_y = on_screen_npc_pos.y + thought_bubble.offset[1] + 30
                    
                    bubble_rect = thought_bubble.item_image.get_rect(center=(pos_x, pos_y))
                    
                    bg_rect = bubble_rect.inflate(10, 10)
                    pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, border_radius=5)
                    pygame.draw.rect(self.screen, (0, 0, 0), bg_rect, width=2, border_radius=5)
                    
                    self.screen.blit(thought_bubble.item_image, bubble_rect)

    

ui_manager = UIManager() 