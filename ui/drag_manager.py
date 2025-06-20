import pygame
from typing import List
from config import INPUTS
from items.item_manager import item_manager
from items.slot import InventorySlot


class DraggableUI:
    def pick_item(self, mouse_pos, right_click):  
        raise NotImplementedError
    def drop_item(self, slot, mouse_pos, right_click):
        raise NotImplementedError
    def is_hover(self, mouse_pos):
        raise NotImplementedError
    def finalize_pick(self, final_drag_slot, accepted, right_click):
        raise NotImplementedError


class DragManager:
    _instance = None

    def __init__(self):
        self.widgets: List[DraggableUI] = []
        self.drag_slot = None
        self.source_widget = None
        self.drag_started_with_right_click = False
        self.drag_slot_initial_amount = 0

    def register(self, widget):
        if widget not in self.widgets:
            self.widgets.append(widget)

    def unregister(self, widget):
        if widget in self.widgets:
            self.widgets.remove(widget)

    def update(self):
        mouse_pos = INPUTS.get('mouse_pos')
        if mouse_pos is None:
            return

        if self.drag_slot is None and (INPUTS['left_click'] or INPUTS['right_click']):
            right = INPUTS['right_click']
            drag_started = False
            for w in self.widgets:
                if w.is_hover(mouse_pos):
                    slot = w.pick_item(mouse_pos, right)
                    if slot is not None and not slot.is_empty():
                        self.drag_slot = slot
                        self.source_widget = w
                        self.drag_started_with_right_click = right
                        self.drag_slot_initial_amount = slot.amount
                        drag_started = True
                        break
                        
            
            if drag_started:
                INPUTS['left_click'] = False
                INPUTS['right_click'] = False
                return

        if self.drag_slot is not None:
            if not (pygame.mouse.get_pressed(num_buttons=3)[0] or pygame.mouse.get_pressed(num_buttons=3)[2]):
                right = self.drag_started_with_right_click
                accepted = False
                target_widget = None

                for w in self.widgets:
                    if w.is_hover(mouse_pos):
                        target_widget = w
                        break
                
                
                if target_widget:
                    if target_widget.drop_item(self.drag_slot, mouse_pos, right):
                        accepted = True

                    if self.source_widget:
                        self.source_widget.finalize_pick(self.drag_slot, accepted, right)

                if self.source_widget:
                    self.source_widget.save_to_state()

                self.drag_slot = None
                self.source_widget = None
                self.drag_started_with_right_click = False

    def draw_cursor(self, surface: pygame.Surface):
        if self.drag_slot is None or self.drag_slot.is_empty():
            return
        
        sprite = item_manager.get_sprite(self.drag_slot.item_id, (32, 32))
        if sprite is None:
            return

        x, y = pygame.mouse.get_pos()
        rect = sprite.get_rect(center=(x, y))
        surface.blit(sprite, rect)

        amount = self.drag_slot.amount
        if amount > 1:
            font = pygame.font.Font(None, 14)
            text = font.render(str(amount), True, (255,255,255))
            surface.blit(text, (rect.right - text.get_width(), rect.bottom - text.get_height()))

drag_manager = DragManager()