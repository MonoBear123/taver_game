import json
from typing import Dict, List, Optional, Tuple, Union
import pygame
from config import INPUTS, PLAYER_STATE
from slot import InventorySlot
from drag_manager import drag_manager

class Inventory:
    SLOT_SIZE = 40          
    PADDING = 4     
    ITEM_SIZE = 32 
    
    def __init__(self, size: Tuple[int, int] = (8, 4), inventory_type: str = 'player'):
        self.width, self.height = size
        self.slots: List[InventorySlot] = [InventorySlot() for _ in range(self.width * self.height)]
        self.selected_slot = None
        self.visible = False
        self.tab_pressed = False
        
        self.dragging_slot: Optional[InventorySlot] = None
        self.dragging_from_index: Optional[int] = None
        self._pick_return_index: Optional[int] = None
        
        self.external_drop_target = None

        self.inventory_type = inventory_type
        
        if self.inventory_type == 'player':
            self.load_from_state()
        
        drag_manager.register(self)
        
        self.active_slot_index = 0
        self.is_visible = False
        
    def get_slot(self, x: int, y: int) -> Optional[InventorySlot]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.slots[y * self.width + x]
        return None
    
    def get_slot_position(self, index: int) -> Tuple[int, int]:
        return index % self.width, index // self.width
    
    def find_item(self, item_id: str) -> List[Tuple[int, int, InventorySlot]]:
        result = []
        for i, slot in enumerate(self.slots):
            if slot.item_id == item_id:
                x, y = self.get_slot_position(i)
                result.append((x, y, slot))
        return result
    
    def has_item(self, item_id: str) -> bool:
        return any(slot.item_id == item_id and not slot.is_empty() for slot in self.slots)
    
    def count_item(self, item_id: str) -> int:
        return sum(slot.amount for slot in self.slots if slot.item_id == item_id)
    
    def add_item(self, slot_or_item_id: Union[int, str], item_id: str = None, amount: int = 1) -> int:
        result = 0
        if isinstance(slot_or_item_id, int):
            if 0 <= slot_or_item_id < len(self.slots):
                slot = self.slots[slot_or_item_id]
                if slot.is_empty():
                    slot.item_id = item_id
                    result = slot.add(amount)
                else:
                    result = amount
            else:
                result = amount
        else:
            item_id = slot_or_item_id
            for slot in self.slots:
                if slot.item_id == item_id and not slot.is_empty() and slot.can_add():
                    amount = slot.add(amount)
                    if amount == 0:
                        break
            
            if amount > 0:
                for slot in self.slots:
                    if slot.is_empty():
                        slot.item_id = item_id
                        amount = slot.add(amount)
                        if amount == 0:
                            break
            result = amount
        
        self.save_to_state()
        return result
    
    def remove_item(self, item_id: str, amount: int = 1) -> bool:
        to_remove = amount
        # Сначала пытаемся удалить из неполных стаков
        for slot in sorted([s for s in self.slots if s.item_id == item_id and s.amount < s.max_amount], key=lambda s: s.amount):
            if to_remove == 0: break
            removed_count = min(to_remove, slot.amount)
            slot.remove(removed_count)
            to_remove -= removed_count

        # Затем из полных стаков
        if to_remove > 0:
            for slot in [s for s in self.slots if s.item_id == item_id]:
                if to_remove == 0: break
                removed_count = min(to_remove, slot.amount)
                slot.remove(removed_count)
                to_remove -= removed_count
        
        self.save_to_state()
        return to_remove == 0
    
    def get_item_sprite(self, item_id: str) -> Optional[pygame.Surface]:
        from item_renderer import get_item_sprite  
        sprite = get_item_sprite(item_id, self.ITEM_SIZE)
        return sprite

    def create_test_items(self):
        
        self.add_item((self.height - 1) * self.width + 0, "egg", 5)  
        self.add_item((self.height - 1) * self.width + 1, "hot_pepper", 1) 
        self.add_item((self.height - 1) * self.width + 2, "sweet_pepper", 3)  
        self.add_item((self.height - 1) * self.width + 3, "pumpkin", 2)  
        self.add_item((self.height - 1) * self.width + 4, "garlik", 10) 
        

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        for i in range(len(self.slots)):
            x, y = self.get_slot_position(i)
            rect = pygame.Rect(
                x * (self.SLOT_SIZE + self.PADDING),
                y * (self.SLOT_SIZE + self.PADDING),
                self.SLOT_SIZE,
                self.SLOT_SIZE
            )
            
            if rect.collidepoint(pos):
                self.selected_slot = i
                return (x, y)
        
        return None 

    def update(self):
        if self.inventory_type == 'player':
            if INPUTS['tab'] and not self.tab_pressed:
                self.visible = not self.visible
                self.tab_pressed = True
            elif not INPUTS['tab']:
                self.tab_pressed = False

            for i in range(1, 6):
                if INPUTS[str(i)]:
                    self.selected_slot = (self.height - 1) * self.width + (i - 1)

            if INPUTS['scroll_up']:
                current_slot = self.selected_slot if self.selected_slot is not None else self.width * (self.height - 1)
                if current_slot >= self.width * (self.height - 1):
                    self.selected_slot = ((current_slot - self.width * (self.height - 1) - 1) % self.width) + self.width * (self.height - 1)
                INPUTS['scroll_up'] = False

            if INPUTS['scroll_down']:
                current_slot = self.selected_slot if self.selected_slot is not None else self.width * (self.height - 1)
                if current_slot >= self.width * (self.height - 1):
                    self.selected_slot = ((current_slot - self.width * (self.height - 1) + 1) % self.width) + self.width * (self.height - 1)
                INPUTS['scroll_down'] = False
            

    def get_selected_item(self) -> Optional[InventorySlot]:
        if self.selected_slot is not None:
            return self.slots[self.selected_slot]
        return None 

    def start_dragging(self, slot_index: int):
        if slot_index >= 0 and slot_index < len(self.slots):
            slot = self.slots[slot_index]
            if not slot.is_empty():
                self.dragging_slot = InventorySlot(slot.item_id, slot.amount)
                self.dragging_from_index = slot_index
                slot.clear()
                self.drag_started_with_left = True
                return True
        return False
    
    def stop_dragging(self, slot_index: int = None) -> bool:
        if not self.dragging_slot:
            return False
            
        mouse_pos = INPUTS.get('mouse_pos', (0, 0))

        if slot_index is None or slot_index < 0 or slot_index >= len(self.slots):
            accepted = False
            if callable(self.external_drop_target):
                accepted = self.external_drop_target(self.dragging_slot, mouse_pos)

            if not accepted:
                self.slots[self.dragging_from_index].item_id = self.dragging_slot.item_id
                self.slots[self.dragging_from_index].amount = self.dragging_slot.amount
            else:
                self.dragging_slot = None
                self.dragging_from_index = None
                self.drag_started_with_left = False
                self.save_to_state()
                return True
        else:
            target_slot = self.slots[slot_index]
            if target_slot.is_empty():
                target_slot.item_id = self.dragging_slot.item_id
                target_slot.amount = self.dragging_slot.amount
            elif target_slot.item_id == self.dragging_slot.item_id:
                overflow = target_slot.add(self.dragging_slot.amount)
                if overflow > 0:
                    self.slots[self.dragging_from_index].item_id = self.dragging_slot.item_id
                    self.slots[self.dragging_from_index].amount = overflow
            else:
                old_item_id = target_slot.item_id
                old_amount = target_slot.amount
                target_slot.item_id = self.dragging_slot.item_id
                target_slot.amount = self.dragging_slot.amount
                self.slots[self.dragging_from_index].item_id = old_item_id
                self.slots[self.dragging_from_index].amount = old_amount
                
        self.dragging_slot = None
        self.dragging_from_index = None
        self.drag_started_with_left = False
        
        self.save_to_state()
        return True

    def _get_base_positions(self) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        try:
            screen = pygame.display.get_surface()
            if not screen:
                return None, None
            screen_width, screen_height = screen.get_size()
        except ImportError:
            screen_width, screen_height = 640, 480 


        if self.inventory_type == 'player':
            hotbar_width = self.width * (self.SLOT_SIZE + self.PADDING)
            hotbar_x = (screen_width - hotbar_width) // 2
            hotbar_y = screen_height - (self.SLOT_SIZE + self.PADDING + 20)
            
            inventory_width = self.width * (self.SLOT_SIZE + self.PADDING)
            inventory_height = (self.height - 1) * (self.SLOT_SIZE + self.PADDING)
            inventory_x = (screen_width - inventory_width) // 2
            inventory_y = (screen_height - inventory_height - (self.SLOT_SIZE + self.PADDING + 20)) // 2
            return (inventory_x, inventory_y), (hotbar_x, hotbar_y)
        
        elif self.inventory_type == 'storage':
            inventory_width = self.width * (self.SLOT_SIZE + self.PADDING)
            inventory_height = self.height * (self.SLOT_SIZE + self.PADDING)
            inventory_x = (screen_width - inventory_width) // 2
            inventory_y = (screen_height - inventory_height) // 2 - 50
            return (inventory_x, inventory_y), None
        
        return None, None


    def get_slot_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        main_pos, hotbar_pos = self._get_base_positions()
        
        if main_pos:
            rows_to_check = self.height
            is_main_inventory_visible = self.inventory_type != 'player' or self.visible
            
            if is_main_inventory_visible:
                if self.inventory_type == 'player':
                    rows_to_check = self.height - 1

                for y in range(rows_to_check):
                    for x in range(self.width):
                        slot_index = y * self.width + x
                        slot_rect_x = main_pos[0] + x * (self.SLOT_SIZE + self.PADDING)
                        slot_rect_y = main_pos[1] + y * (self.SLOT_SIZE + self.PADDING)
                        if (slot_rect_x <= pos[0] < slot_rect_x + self.SLOT_SIZE and
                            slot_rect_y <= pos[1] < slot_rect_y + self.SLOT_SIZE):
                            return slot_index
        
        if hotbar_pos and self.inventory_type == 'player':
            y = self.height - 1
            for x in range(self.width):
                slot_index = y * self.width + x
                slot_rect_x = hotbar_pos[0] + x * (self.SLOT_SIZE + self.PADDING)
                slot_rect_y = hotbar_pos[1] + (y - (self.height-1)) * (self.SLOT_SIZE + self.PADDING)
                if (slot_rect_x <= pos[0] < slot_rect_x + self.SLOT_SIZE and
                    slot_rect_y <= pos[1] < slot_rect_y + self.SLOT_SIZE):
                    return slot_index

        return None

    def to_dict(self) -> dict:
        return {
            'width': self.width,
            'height': self.height,
            'selected_slot': self.selected_slot,
            'slots': [slot.to_dict() for slot in self.slots]
        }
    
    def from_dict(self, data: dict) -> None:
        if data is None:
            return 
       
        self.width = data.get('width', self.width)
        self.height = data.get('height', self.height)
        self.selected_slot = data.get('selected_slot')
        
        slots_data = data.get('slots', [])
        self.slots = []
        for slot_data in slots_data:
            self.slots.append(InventorySlot.from_dict(slot_data))
        
        while len(self.slots) < self.width * self.height:
            self.slots.append(InventorySlot())
    
    def save_to_state(self) -> None:
        if self.inventory_type == 'player':
            PLAYER_STATE['inventory'] = self.to_dict()
    
    def load_from_state(self) -> None:
        if self.inventory_type == 'player' and 'inventory' in PLAYER_STATE:
            self.from_dict(PLAYER_STATE['inventory']) 

    def is_hover(self, mouse_pos):  
        if self.inventory_type == 'storage' and not self.visible:
            return False
        return self.get_slot_at_pos(mouse_pos) is not None

    def pick_item(self, mouse_pos, right_click):  
        idx = self.get_slot_at_pos(mouse_pos)
        if idx is None:
            return None
        slot = self.slots[idx]
        if slot.is_empty() or slot.is_ghost: 
            return None

        self._pick_return_index = idx
        
        slot.is_ghost = True

        if right_click:
            picked = InventorySlot(slot.item_id, 1)
            return picked
        else:
            picked = InventorySlot(slot.item_id, slot.amount)
            return picked

    def drop_item(self, drag_slot, mouse_pos, right_click):  
        idx = self.get_slot_at_pos(mouse_pos)
        source_idx = self._pick_return_index
        if source_idx is not None and 0 <= source_idx < len(self.slots):
            self.slots[source_idx].is_ghost = False

        if idx is None:
            return False
        
        target = self.slots[idx]

        if right_click:
            if source_idx == idx:
                drag_slot.amount = 0 
                return True

            placed_one = False
            if target.is_empty():
                target.item_id = drag_slot.item_id
                target.add(1)
                placed_one = True
            elif target.item_id == drag_slot.item_id and target.can_add(1):
                target.add(1)
                placed_one = True
            
            if placed_one:
                drag_slot.remove(1)
            else:
                return False
        else:
            if source_idx == idx:
                return True

            if target.is_empty():
                target.item_id = drag_slot.item_id
                target.amount = drag_slot.amount
                drag_slot.amount = 0
            elif target.item_id == drag_slot.item_id:
                overflow = target.add(drag_slot.amount)
                drag_slot.amount = overflow
            else:
                target_item_id, target_amount = target.item_id, target.amount
                target.item_id, target.amount = drag_slot.item_id, drag_slot.amount
                drag_slot.item_id, drag_slot.amount = target_item_id, target_amount

        self.save_to_state()
        return True

    def finalize_pick(self, final_drag_slot: Optional['InventorySlot'], accepted: bool, right_click: bool):
        source_idx = self._pick_return_index
        if source_idx is None or not (0 <= source_idx < len(self.slots)):
            self._pick_return_index = None
            return

        source_slot = self.slots[source_idx]
        source_slot.is_ghost = False

        if not accepted:
            pass
        elif right_click:
            source_slot.remove(1)
        else:
            if final_drag_slot and final_drag_slot.amount > 0:
                source_slot.item_id = final_drag_slot.item_id
                source_slot.amount = final_drag_slot.amount
            else:
                source_slot.clear()
        
        self.save_to_state()
        self._pick_return_index = None

    def return_item(self, drag_slot):  
        if self._pick_return_index is not None:
            target = self.slots[self._pick_return_index]
            if target.is_empty():
                target.item_id = drag_slot.item_id
                target.amount = drag_slot.amount
                drag_slot.amount = 0
            elif target.item_id == drag_slot.item_id and target.can_add(drag_slot.amount):
                overflow = target.add(drag_slot.amount)
                drag_slot.amount = overflow

        if getattr(drag_slot, 'amount', 0) > 0:
            overflow = self.add_item(drag_slot.item_id, drag_slot.item_id, drag_slot.amount)
            drag_slot.amount = overflow

        self.save_to_state() 

    def get_active_slot(self):
        return self.slots[self.active_slot_index] 