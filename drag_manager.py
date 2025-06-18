import pygame
from typing import List, Optional, Tuple, TYPE_CHECKING
from config import INPUTS
from item_renderer import get_item_sprite
if TYPE_CHECKING:
    from slot import InventorySlot, is_empty, get_amount

class DraggableUI:
   
    def pick_item(self, mouse_pos: Tuple[int,int], right_click: bool):  
        raise NotImplementedError
    def drop_item(self, slot: 'InventorySlot', mouse_pos: Tuple[int,int], right_click: bool) -> bool:
        raise NotImplementedError
    def is_hover(self, mouse_pos: Tuple[int,int]) -> bool:
        raise NotImplementedError
    def finalize_pick(self, final_drag_slot: Optional['InventorySlot'], accepted: bool, right_click: bool):
        raise NotImplementedError

class DragManager:
    def __init__(self):
        self.widgets: List[DraggableUI] = []
        self.drag_slot: Optional['InventorySlot'] = None
        self.source_widget: Optional[DraggableUI] = None
        self.drag_started_with_right_click: bool = False
        self.drag_slot_initial_amount: int = 0

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
                    if slot is not None and not is_empty(slot):
                        self.drag_slot = slot
                        self.source_widget = w
                        self.drag_started_with_right_click = right
                        self.drag_slot_initial_amount = get_amount(slot)
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

                self.drag_slot = None
                self.source_widget = None
                self.drag_started_with_right_click = False

    def draw_cursor(self, surface: pygame.Surface):
        if self.drag_slot is None or is_empty(self.drag_slot):
            return
        
        sprite = get_item_sprite(self.drag_slot.item_id, 32)
        if sprite is None:
            return

        x, y = pygame.mouse.get_pos()
        rect = sprite.get_rect(center=(x, y))
        surface.blit(sprite, rect)

        amount = get_amount(self.drag_slot)
        if amount > 1:
            font = pygame.font.Font(None, 14)
            text = font.render(str(amount), True, (255,255,255))
            surface.blit(text, (rect.right - text.get_width(), rect.bottom - text.get_height()))

drag_manager = DragManager() 