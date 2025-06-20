from items.item_manager import item_manager

class InventorySlot:
    def __init__(self, item_id=None, amount=0, max_stack=24):
        self.item_id = item_id
        self.amount = amount
        self.max_stack = max_stack
        self.is_ghost = False

    def is_empty(self):
        return self.item_id is None or self.amount <= 0

    def get_sprite(self, size=None):
        if self.is_empty():
            return None
        return item_manager.get_sprite(self.item_id, size)

    def add(self, amount_to_add):
        can_add = self.max_stack - self.amount
        to_add = min(amount_to_add, can_add)
        self.amount += to_add
        return amount_to_add - to_add

    def remove(self, amount_to_remove=1):
        self.amount -= amount_to_remove
        if self.amount <= 0:
            self.clear()

    def clear(self):
        self.item_id = None
        self.amount = 0

    def can_add(self, amount=1):
        return self.amount + amount <= self.max_stack

   

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "amount": self.amount,
            "max_stack": self.max_stack,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(
            item_id=data.get("item_id"),
            amount=data.get("amount", 0),
            max_stack=data.get("max_stack", 24),
        ) 