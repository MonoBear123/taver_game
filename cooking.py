from typing import Dict, List, Optional, Any, Tuple
from slot import InventorySlot
import pygame
from game_time import GameTimeManager
from item_renderer import draw_item
from config import INPUTS
from drag_manager import DragManager
from asset_loader import get_asset
from recipe_manager import recipe_manager
from item_manager import item_manager


class CookingInterface:
    def __init__(self, stove_component, player, screen, *, pos=(210, 100), scale=1):
        self.stove = stove_component
        self.player = player
        self.screen = screen
        self.recipes = recipe_manager.get_all_recipes()

        self.is_open = True
        self.show_recipes = False
        self.recipes_per_page = 4
        self.recipe_page = 0
        self._pick_source_info: Optional[Tuple[str, Optional[int]]] = None

        self.base_x, self.base_y = pos
        self.scale = scale

        def _x(val): return int(val * self.scale) + self.base_x
        def _y(val): return int(val * self.scale) + self.base_y
        def _s(val): return int(val * self.scale)

        self.window_rect = pygame.Rect(_x(0), _y(0), _s(220), _s(200))
        self.slot_size = _s(40)
        self.slot_positions = [
            (_x(10), _y(10)), (_x(55), _y(10)), (_x(100), _y(10)),
            (_x(10), _y(55)), (_x(55), _y(55)), (_x(100), _y(55))
        ]
        self.result_slot_pos = (_x(170), _y(32))
        self.fuel_slot_pos = (_x(55), _y(135))
        self.progress_bar_rect = pygame.Rect(_x(142), _y(37), _s(25), _s(15))
        self.recipe_button_rect = pygame.Rect(_x(170), _y(135), _s(40), _s(40))
        
        self.recipe_button_image = get_asset('assets/ui/recipe_book.png')
        self.recipe_button_image = pygame.transform.scale(self.recipe_button_image, (self.recipe_button_rect.width, self.recipe_button_rect.height))

        self.recipe_window_rect = pygame.Rect(self.window_rect.left - 195, self.window_rect.y, _s(190), _s(200))
        self.prev_button_rect = pygame.Rect(self.recipe_window_rect.x + _s(10), self.recipe_window_rect.bottom - _s(35), _s(30), _s(30))
        self.next_button_rect = pygame.Rect(self.recipe_window_rect.right - _s(40), self.recipe_window_rect.bottom - _s(35), _s(30), _s(30))

        self.ingredient_slots = self.stove.ingredient_slots
        self.result_item = self.stove.result_slot

        self.font = pygame.font.Font(None, _s(24))
        self.small_font = pygame.font.Font(None, _s(14))

    def update(self, dt, game_time):
        if not self.is_open:
            return
        mouse_pos = INPUTS.get('mouse_pos')
        if mouse_pos is None:
            return

        if INPUTS.get('left_click'):
            if self.recipe_button_rect.collidepoint(mouse_pos):
                self.show_recipes = not self.show_recipes
                INPUTS['left_click'] = False
            elif self.show_recipes and self.prev_button_rect.collidepoint(mouse_pos):
                if self.recipe_page > 0:
                    self.recipe_page -= 1
                INPUTS['left_click'] = False
            elif self.show_recipes and self.next_button_rect.collidepoint(mouse_pos):
                # Преобразуем в список для проверки длины
                recipes_list = self.recipes
                if isinstance(recipes_list, dict):
                    recipes_list = list(recipes_list.values())
                max_page = max(0, (len(recipes_list) - 1) // self.recipes_per_page)
                if self.recipe_page < max_page:
                    self.recipe_page += 1
                INPUTS['left_click'] = False
        
    def is_hover(self, mouse_pos):
        return self.window_rect.collidepoint(mouse_pos)

    def _slot_under_cursor(self, mouse_pos):
        for i, pos in enumerate(self.slot_positions):
            if pygame.Rect(pos[0], pos[1], self.slot_size, self.slot_size).collidepoint(mouse_pos):
                return 'ingredient', i
        if pygame.Rect(self.fuel_slot_pos[0], self.fuel_slot_pos[1], self.slot_size, self.slot_size).collidepoint(mouse_pos):
            return 'fuel', None
        if pygame.Rect(self.result_slot_pos[0], self.result_slot_pos[1], self.slot_size, self.slot_size).collidepoint(mouse_pos):
            return 'result', None
        return None

    def pick_item(self, mouse_pos, right_click):
        info = self._slot_under_cursor(mouse_pos)
        if not info: return None
        slot_type, idx = info
        
        slot_to_pick = None
        if slot_type == 'ingredient': slot_to_pick = self.ingredient_slots[idx]
        elif slot_type == 'result': slot_to_pick = self.result_item
        
        if slot_to_pick and not slot_to_pick.is_empty() and not slot_to_pick.is_ghost:
            slot_to_pick.is_ghost = True
            self._pick_source_info = (slot_type, idx)
            return InventorySlot(slot_to_pick.item_id, 1 if right_click else slot_to_pick.amount)
        return None

    def drop_item(self, drag_slot, mouse_pos, right_click):
        info = self._slot_under_cursor(mouse_pos)
        if not info: return False
        slot_type, idx = info

        # Если бросаем предмет обратно в тот же слот, считаем это успехом, но ничего не делаем.
        # finalize_pick корректно обработает эту ситуацию.
        if self._pick_source_info == (slot_type, idx):
            return True

        if slot_type == 'ingredient':
            target_slot = self.ingredient_slots[idx]
            amount_to_move = 1 if right_click else drag_slot.amount
            if target_slot.is_empty():
                target_slot.item_id = drag_slot.item_id
                target_slot.add(amount_to_move)
                drag_slot.remove(amount_to_move)
                self.stove._sync_state()
                return True
            elif target_slot.item_id == drag_slot.item_id and target_slot.can_add(amount_to_move):
                target_slot.add(amount_to_move)
                drag_slot.remove(amount_to_move)
                self.stove._sync_state()
                return True
        
        elif slot_type == 'fuel':
            item_info = item_manager.get_item_data(drag_slot.item_id)
            is_fuel = drag_slot.item_id == 'wood' or (item_info and item_info.get('type') == 'fuel')
            if is_fuel:
                fuel_amount = item_info.get('fuel_amount', 10) if item_info else 10
                if self.stove.add_fuel(fuel_amount, fuel_type='wood'):
                    self.stove.fuel_slot_item_id = drag_slot.item_id
                    drag_slot.remove(1)
                    self.stove._sync_state()
                    return True
        
        return False

    def finalize_pick(self, final_drag_slot: Optional[InventorySlot], accepted: bool, right_click: bool):
        source_info = self._pick_source_info
        if not source_info:
            return
        
        slot_type, idx = source_info
        source_slot = None
        if slot_type == 'ingredient':
            source_slot = self.ingredient_slots[idx]
        elif slot_type == 'result':
            source_slot = self.result_item

        if source_slot:
            source_slot.is_ghost = False
            if not accepted:
                # Если перетаскивание не было принято (напр. бросили в пустое место), ничего не меняем.
                pass
            elif right_click:
                # Правый клик: уменьшаем источник, только если предмет был успешно помещен (слот курсора опустел).
                if final_drag_slot and final_drag_slot.amount == 0:
                    source_slot.remove(1)
            else:
                # Левый клик: обновляем источник тем, что осталось в слоте курсора.
                if final_drag_slot and final_drag_slot.amount > 0:
                    source_slot.item_id = final_drag_slot.item_id
                    source_slot.amount = final_drag_slot.amount
                else:
                    source_slot.clear()

        self._pick_source_info = None
        self.stove._sync_state()