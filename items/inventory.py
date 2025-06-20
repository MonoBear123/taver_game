import json
import pygame
from config import INPUTS, PLAYER_STATE
from items.slot import InventorySlot
from ui.drag_manager import drag_manager

class Inventory:
    SLOT_SIZE = 40
    PADDING = 4
    ITEM_SIZE = 32

    def __init__(self, size=(8, 4), inventory_type='player'):
        self.width, self.height = size
        self.slots = [InventorySlot() for _ in range(self.width * self.height)]
        self.visible = False
        self.tab_pressed = False
        self._pick_return_index = None
        self.inventory_type = inventory_type
        self.active_slot_index = 0

        if self.inventory_type == 'player':
            self.load_from_state()

        drag_manager.register(self)

    def get_slot(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.slots[y * self.width + x]
        return None

    def get_slot_position(self, index):
        if 0 <= index < len(self.slots):
            return index % self.width, index // self.width
        return None

    def find_item(self, item_id):
        result = []
        for i, slot in enumerate(self.slots):
            if slot.item_id == item_id:
                x, y = self.get_slot_position(i)
                result.append((x, y, slot))
        return result

    def has_item(self, item_id):
        has = any(slot.item_id == item_id and not slot.is_empty() for slot in self.slots)
        print(f"Has item {item_id}: {has}")
        return has

    def count_item(self, item_id):
        count = sum(slot.amount for slot in self.slots if slot.item_id == item_id)
        return count

    def add_item(self, slot_or_item_id, item_id=None, amount=1):
        result = amount
        if isinstance(slot_or_item_id, int):
            if 0 <= slot_or_item_id < len(self.slots):
                slot = self.slots[slot_or_item_id]
                if slot.is_empty():
                    slot.item_id = item_id
                    result = slot.add(amount)
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

    def remove_item(self, item_id, amount=1):
        to_remove = amount
        for slot in sorted(
            [s for s in self.slots if s.item_id == item_id and s.amount < s.max_stack],
            key=lambda s: s.amount
        ):
            if to_remove == 0:
                break
            removed_count = min(to_remove, slot.amount)
            slot.remove(removed_count)
            to_remove -= removed_count

        if to_remove > 0:
            for slot in [s for s in self.slots if s.item_id == item_id]:
                if to_remove == 0:
                    break
                removed_count = min(to_remove, slot.amount)
                slot.remove(removed_count)
                to_remove -= removed_count

        self.save_to_state()
        return to_remove == 0

    def update(self):
        if self.inventory_type == 'player':
            self.load_from_state()
            if INPUTS.get('tab', False) and not self.tab_pressed:
                self.visible = not self.visible
                self.tab_pressed = True
            elif not INPUTS.get('tab', False):
                self.tab_pressed = False

    def _get_inventory_positions(self, inv):
        self.screen = pygame.display.get_surface()
        screen_size = self.screen.get_size()
        if inv.inventory_type == 'player':
            hotbar_width = inv.width * (inv.SLOT_SIZE + inv.PADDING)
            hotbar_x = (screen_size[0] - hotbar_width) // 2
            hotbar_y = self.screen.get_height() - (inv.SLOT_SIZE + inv.PADDING + 20)
            
            inventory_width = hotbar_width
            inventory_height = (inv.height - 1) * (inv.SLOT_SIZE + inv.PADDING)

            inventory_x = (self.screen.get_width() - inventory_width) // 2
            inventory_y = (self.screen.get_height() - inventory_height - (inv.SLOT_SIZE + inv.PADDING + 20)) // 2
            return (inventory_x, inventory_y), (hotbar_x, hotbar_y)

        elif inv.inventory_type == 'storage':
            inventory_width = inv.width * (inv.SLOT_SIZE + inv.PADDING)
            inventory_height = inv.height * (inv.SLOT_SIZE + inv.PADDING)
            inventory_x = (self.screen.get_width() - inventory_width) // 2
            inventory_y = (self.screen.get_height() - inventory_height) // 2 - 50
            return (inventory_x, inventory_y), None
            
        return None, None

       

    def get_slot_at_pos(self, pos):
        main_pos, hotbar_pos = self._get_inventory_positions(self)

        if hotbar_pos and self.inventory_type == 'player':
            y = self.height - 1
            for x in range(self.width):
                slot_index = y * self.width + x
                slot_rect_x = hotbar_pos[0] + x * (self.SLOT_SIZE + self.PADDING)
                slot_rect_y = hotbar_pos[1]
                if (slot_rect_x <= pos[0] < slot_rect_x + self.SLOT_SIZE and
                    slot_rect_y <= pos[1] < slot_rect_y + self.SLOT_SIZE):
                    return slot_index

        if main_pos and (self.inventory_type != 'player' or self.visible):
            rows_to_check = self.height if self.inventory_type != 'player' else self.height - 1
            for y in range(rows_to_check):
                for x in range(self.width):
                    slot_index = y * self.width + x
                    slot_rect_x = main_pos[0] + x * (self.SLOT_SIZE + self.PADDING)
                    slot_rect_y = main_pos[1] + y * (self.SLOT_SIZE + self.PADDING)
                    if (slot_rect_x <= pos[0] < slot_rect_x + self.SLOT_SIZE and
                        slot_rect_y <= pos[1] < slot_rect_y + self.SLOT_SIZE):
                        return slot_index

        return None

    def to_dict(self):
        data = {
            'width': self.width,
            'height': self.height,
            'slots': [slot.to_dict() for slot in self.slots]
        }
        return data

    def from_dict(self, data):
        if data is None:
            return
        slots_data = data.get('slots', [])
        self.slots = [InventorySlot() for _ in range(self.width * self.height)]
        for i, slot_data in enumerate(slots_data):
            if i < len(self.slots):
                self.slots[i] = InventorySlot.from_dict(slot_data)

    def save_to_state(self):
        if self.inventory_type == 'player':
            PLAYER_STATE['inventory'] = self.to_dict()

    def load_from_state(self):
        if self.inventory_type == 'player' and 'inventory' in PLAYER_STATE:
            self.from_dict(PLAYER_STATE['inventory'])

    def is_hover(self, mouse_pos):
        if self.inventory_type == 'storage' and not self.visible:
            return False
        hover = self.get_slot_at_pos(mouse_pos) is not None
        return hover

    def pick_item(self, mouse_pos, right_click):
        idx = self.get_slot_at_pos(mouse_pos)
        if idx is None or self.slots[idx].is_empty():
            return None

        self._pick_return_index = idx
        source_slot = self.slots[idx]

        if right_click:
            picked_amount = (source_slot.amount + 1) // 2
            picked_slot = InventorySlot(source_slot.item_id, picked_amount)
            source_slot.remove(picked_amount)
        else:
            picked_slot = InventorySlot(source_slot.item_id, source_slot.amount)
            source_slot.clear()

        return picked_slot

    def drop_item(self, drag_slot, mouse_pos, right_click):
        idx = self.get_slot_at_pos(mouse_pos)
        if idx is None:
            return False

        target_slot = self.slots[idx]

        if target_slot.item_id == drag_slot.item_id and target_slot.can_add(drag_slot.amount):
            overflow = target_slot.add(drag_slot.amount)
            drag_slot.amount = overflow
        else:
            temp_id, temp_amount = target_slot.item_id, target_slot.amount
            target_slot.item_id, target_slot.amount = drag_slot.item_id, drag_slot.amount
            drag_slot.item_id, drag_slot.amount = temp_id, temp_amount

        self.save_to_state()
        return True

    def finalize_pick(self, final_drag_slot, accepted, right_click):
        source_idx = self._pick_return_index
        if source_idx is None or not (0 <= source_idx < len(self.slots)):
            self._pick_return_index = None
            return

        if final_drag_slot and not final_drag_slot.is_empty():
            source_slot = self.slots[source_idx]
            if source_slot.is_empty():
                source_slot.item_id = final_drag_slot.item_id
                source_slot.amount = final_drag_slot.amount

        self.save_to_state()
        self._pick_return_index = None

