class InventorySlot:
    def __init__(self, item_id: str | None = None, amount: int = 0, max_stack: int = 24):
        self.item_id = item_id
        self.amount = amount
        self.max_stack = max_stack
        self.is_ghost: bool = False

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
        return {
            'item_id': self.item_id,
            'amount': self.amount,
            'max_stack': self.max_stack
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'InventorySlot':
        return cls(
            item_id=data.get('item_id'),
            amount=data.get('amount', 0),
            max_stack=data.get('max_stack', 64)
        ) 