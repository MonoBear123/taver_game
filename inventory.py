import json
from typing import Dict, List, Optional, Tuple, Union
import pygame
from config import INPUTS, PLAYER_STATE
class InventorySlot:
    def __init__(self, item_id: str = None, amount: int = 0, max_stack: int = 24):
        self.item_id = item_id
        self.amount = amount
        self.max_stack = max_stack
    
    def is_empty(self) -> bool:
        return self.item_id is None or self.amount == 0
    
    def can_add(self, amount: int = 1) -> bool:
        return self.amount + amount <= self.max_stack
    
    def add(self, amount: int = 1) -> int:
        if self.is_empty():
            self.amount = min(amount, self.max_stack)
            return amount - self.amount
        
        if not self.can_add(amount):
            overflow = (self.amount + amount) - self.max_stack
            self.amount = self.max_stack
            return overflow
        
        self.amount += amount
        return 0
    
    def remove(self, amount: int = 1) -> int:
        if self.is_empty() or amount <= 0:
            return 0
        
        if amount >= self.amount:
            removed = self.amount
            self.clear()
            return removed
        
        self.amount -= amount
        return amount
    
    def clear(self):
        self.item_id = None
        self.amount = 0
    
    def to_dict(self) -> dict:
        """Преобразует слот в словарь для сохранения"""
        return {
            'item_id': self.item_id,
            'amount': self.amount,
            'max_stack': self.max_stack
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InventorySlot':
        """Создает слот из словаря"""
        return cls(
            item_id=data.get('item_id'),
            amount=data.get('amount', 0),
            max_stack=data.get('max_stack', 64)
        )

class Inventory:
    SLOT_SIZE = 40          
    PADDING = 4     
    ITEM_SIZE = 32 
    
    def __init__(self, size: Tuple[int, int] = (8, 4)):
        self.width, self.height = size
        self.slots: List[InventorySlot] = [InventorySlot() for _ in range(self.width * self.height)]
        self.selected_slot = None
        self.visible = False
        self.tab_pressed = False
        
        self.dragging_slot: Optional[InventorySlot] = None
        self.dragging_from_index: Optional[int] = None
        self.mouse_pos: Tuple[int, int] = (0, 0)
        
        with open('assets/items/items_data.json', 'r') as f:
            self.items_data = json.load(f)
            
        with open('assets/items/recipes.json', 'r') as f:
            self.recipes_data = json.load(f)['recipes']
        
        self.item_sprites: Dict[str, pygame.Surface] = {}
        
        self.font = pygame.font.Font(None, 12)  
        
        self.load_from_state()
        
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
    
    def remove_item(self, item_id: str, amount: int = 1) -> int:
        removed = 0
        for slot in self.slots:
            if slot.item_id == item_id:
                removed += slot.remove(amount - removed)
                if removed >= amount:
                    break
        
        self.save_to_state()
        return removed
    
    
    
    def get_item_sprite(self, item_id: str) -> Optional[pygame.Surface]:
        if item_id in self.item_sprites:
            return self.item_sprites[item_id]
            
        sprite_path = None
        for category in self.items_data.values():
            if 'items' in category and item_id in category['items']:
                item_data = category['items'][item_id]
                sprite_name = item_data if isinstance(item_data, str) else item_data.get('sprite')
                if sprite_name:
                    if not sprite_name.endswith('.png'):
                        sprite_name += '.png'
                    sprite_path = f"assets/items/{sprite_name}"
                break
        
        if sprite_path:
            
            sprite = pygame.image.load(sprite_path).convert_alpha()
            if sprite.get_size() != (self.ITEM_SIZE, self.ITEM_SIZE):
                sprite = pygame.transform.scale(sprite, (self.ITEM_SIZE, self.ITEM_SIZE))
            self.item_sprites[item_id] = sprite
            return sprite
        
        return 

    def create_test_items(self):
        
        self.add_item((self.height - 1) * self.width + 0, "carrot", 5)  
        self.add_item((self.height - 1) * self.width + 1, "hot_pepper", 1) 
        self.add_item((self.height - 1) * self.width + 2, "sweet_pepper", 3)  
        self.add_item((self.height - 1) * self.width + 3, "pumpkin", 2)  
        self.add_item((self.height - 1) * self.width + 4, "garlik", 10) 
        

    def draw_partial(self, surface: pygame.Surface, pos: Tuple[int, int], start_row: int, end_row: int):
        for y in range(start_row, end_row):
            for x in range(self.width):
                slot_index = y * self.width + x
                if slot_index >= len(self.slots):
                    continue
                    
                slot = self.slots[slot_index]
                rect = pygame.Rect(
                    pos[0] + x * (self.SLOT_SIZE + self.PADDING),
                    pos[1] + (y - start_row) * (self.SLOT_SIZE + self.PADDING),
                    self.SLOT_SIZE,
                    self.SLOT_SIZE
                )
                
                is_hotbar = y == self.height - 1
                bg_color = (70, 70, 70)
                pygame.draw.rect(surface, bg_color, rect)
                
                if slot_index == self.selected_slot:
                    pygame.draw.rect(surface, (255,255,255), rect, 2)
                   
                    border_color = (120, 120, 120) if is_hotbar else (100, 100, 100)
                    pygame.draw.rect(surface, border_color, rect, 1)
                
                if not slot.is_empty():
                    sprite = self.get_item_sprite(slot.item_id)
                    if sprite:
                        scaled_sprite = pygame.transform.scale(sprite, (self.ITEM_SIZE, self.ITEM_SIZE))
                        sprite_x = rect.x + (self.SLOT_SIZE - self.ITEM_SIZE) // 2
                        sprite_y = rect.y + (self.SLOT_SIZE - self.ITEM_SIZE) // 2
                        surface.blit(scaled_sprite, (sprite_x, sprite_y))
                        
                        if slot.amount > 1:
                            text = self.font.render(str(slot.amount), True, (255, 255, 255))
                            text_x = rect.right - text.get_width() - 1
                            text_y = rect.bottom - text.get_height()
                            surface.blit(text, (text_x, text_y))

    def draw_all(self, screen):
        hotbar_width = self.width * (self.SLOT_SIZE + self.PADDING)
        hotbar_x = (screen.get_width() - hotbar_width) // 2
        hotbar_y = screen.get_height() - (self.SLOT_SIZE + self.PADDING + 20)
        self.draw_partial(screen, (hotbar_x, hotbar_y), self.height - 1, self.height)

        if self.visible:
            overlay = pygame.Surface(screen.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(128)
            screen.blit(overlay, (0, 0))
            
            inventory_width = self.width * (self.SLOT_SIZE + self.PADDING)
            inventory_height = (self.height - 1) * (self.SLOT_SIZE + self.PADDING)
            inventory_x = (screen.get_width() - inventory_width) // 2
            inventory_y = (screen.get_height() - inventory_height - (self.SLOT_SIZE + self.PADDING + 20)) // 2
            self.draw_partial(screen, (inventory_x, inventory_y), 0, self.height - 1)
            
        if self.dragging_slot and not self.dragging_slot.is_empty():
            sprite = self.get_item_sprite(self.dragging_slot.item_id)
            if sprite:
                sprite_x = self.mouse_pos[0] - self.ITEM_SIZE // 2
                sprite_y = self.mouse_pos[1] - self.ITEM_SIZE // 2
                screen.blit(sprite, (sprite_x, sprite_y))
                
                if self.dragging_slot.amount > 1:
                    text = self.font.render(str(self.dragging_slot.amount), True, (255, 255, 255))
                    text_x = sprite_x + self.ITEM_SIZE - text.get_width() - 1
                    text_y = sprite_y + self.ITEM_SIZE - text.get_height()
                    screen.blit(text, (text_x, text_y))

    def draw(self, surface: pygame.Surface, pos: Tuple[int, int]):
        self.draw_partial(surface, pos, 0, self.height)
    
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
            
        if INPUTS['mouse_pos']:
            self.mouse_pos = INPUTS['mouse_pos']
            
        if INPUTS['left_click']:
            if not self.dragging_slot:
                slot_index = self.get_slot_at_pos(self.mouse_pos)
                if slot_index is not None:
                    self.start_dragging(slot_index)
        elif self.dragging_slot:
            slot_index = self.get_slot_at_pos(self.mouse_pos)
            self.stop_dragging(slot_index)

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
                return True
        return False
    
    def stop_dragging(self, slot_index: int = None) -> bool:
        if not self.dragging_slot:
            return False
            
        if slot_index is None or slot_index < 0 or slot_index >= len(self.slots):
            self.slots[self.dragging_from_index].item_id = self.dragging_slot.item_id
            self.slots[self.dragging_from_index].amount = self.dragging_slot.amount
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
        
        self.save_to_state()
        return True

    def get_slot_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        hotbar_width = self.width * (self.SLOT_SIZE + self.PADDING)
        hotbar_x = (pygame.display.get_surface().get_width() - hotbar_width) // 2
        hotbar_y = pygame.display.get_surface().get_height() - (self.SLOT_SIZE + self.PADDING + 20)
        
        inventory_width = self.width * (self.SLOT_SIZE + self.PADDING)
        inventory_height = (self.height - 1) * (self.SLOT_SIZE + self.PADDING)
        inventory_x = (pygame.display.get_surface().get_width() - inventory_width) // 2
        inventory_y = (pygame.display.get_surface().get_height() - inventory_height - (self.SLOT_SIZE + self.PADDING + 20)) // 2
        
        for y in range(self.height):
            for x in range(self.width):
                slot_index = y * self.width + x
                
                if y == self.height - 1:  # Хотбар
                    slot_x = hotbar_x + x * (self.SLOT_SIZE + self.PADDING)
                    slot_y = hotbar_y
                else:  # Основной инвентарь
                    if not self.visible:
                        continue
                    slot_x = inventory_x + x * (self.SLOT_SIZE + self.PADDING)
                    slot_y = inventory_y + y * (self.SLOT_SIZE + self.PADDING)
                
                slot_rect = pygame.Rect(slot_x, slot_y, self.SLOT_SIZE, self.SLOT_SIZE)
                if slot_rect.collidepoint(pos):
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
        
        # Загружаем слоты
        slots_data = data.get('slots', [])
        self.slots = []
        for slot_data in slots_data:
            self.slots.append(InventorySlot.from_dict(slot_data))
        
        # Если количество слотов не совпадает, добавляем пустые
        while len(self.slots) < self.width * self.height:
            self.slots.append(InventorySlot())
    
    def save_to_state(self) -> None:
        """Сохраняет состояние инвентаря в PLAYER_STATE"""
        PLAYER_STATE['inventory'] = self.to_dict()
    
    def load_from_state(self) -> None:
        """Загружает состояние инвентаря из PLAYER_STATE"""
        if 'inventory' in PLAYER_STATE:
            self.from_dict(PLAYER_STATE['inventory']) 