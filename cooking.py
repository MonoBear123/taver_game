from typing import Dict, List, Optional, Any
import pygame
from game_time import GameTimeManager
from asset_loader import get_asset

class CookingInterface:
    def __init__(self, stove_component, player, screen, recipes, items):
        self.stove = stove_component
        self.player = player
        self.screen = screen
        self.recipes = recipes
        self.items = items.values()
        self.is_open = True
        self.show_recipes = False

        # Позиции и размеры
        self.window_rect = pygame.Rect(300, 100, 600, 400)
        self.slot_size = 64
        self.slot_positions = [
            (350, 150), (450, 150), (550, 150)  # Слоты для ингредиентов
        ]
        self.result_slot = (650, 150)  # Слот результата
        self.fuel_slot = (350, 250)  # Слот для топлива
        self.arrow_rect = pygame.Rect(600, 150, 40, 40)
        self.recipe_button_rect = pygame.Rect(310, 110, 100, 30)

        # Состояние
        self.ingredient_slots = [None, None, None]  # ID ингредиентов
        self.result_item = None  # ID результата
        self.fuel_item = None  # ID топлива (например, "wood")
        self.current_recipe = None
        self.font = pygame.font.Font(None, 24)

    def draw(self):
        # Фон окна
        pygame.draw.rect(self.screen, (100, 100, 100), self.window_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), self.window_rect, 2)

        # Слоты ингредиентов
        for i, pos in enumerate(self.slot_positions):
            pygame.draw.rect(self.screen, (200, 200, 200), (pos[0], pos[1], self.slot_size, self.slot_size))
            if self.ingredient_slots[i]:
                for category in self.items:
                    if 'items' in category and self.ingredient_slots[i] in category['items']:
                        item_data = category['items'][self.ingredient_slots[i]]
                        sprite = get_asset(item_data)
                        if sprite:
                            sprite = pygame.transform.scale(sprite, (self.slot_size, self.slot_size))
                            self.screen.blit(sprite, pos)
                            pygame.draw.rect(self.screen, (0, 0, 0), (pos[0], pos[1], self.slot_size, self.slot_size), 2)

        # Слот результата
        pygame.draw.rect(self.screen, (200, 200, 200), (self.result_slot[0], self.result_slot[1], self.slot_size, self.slot_size))
        if self.result_item:
            sprite = get_asset(self.items[self.result_item]["sprite"])
            if sprite:
                sprite = pygame.transform.scale(sprite, (self.slot_size, self.slot_size))
                self.screen.blit(sprite, self.result_slot)
        pygame.draw.rect(self.screen, (0, 0, 0), (self.result_slot[0], self.result_slot[1], self.slot_size, self.slot_size), 2)

        # Слот топлива
        pygame.draw.rect(self.screen, (200, 200, 200), (self.fuel_slot[0], self.fuel_slot[1], self.slot_size, self.slot_size))
        if self.fuel_item:
            sprite = get_asset(self.items[self.fuel_item]["sprite"])
            if sprite:
                sprite = pygame.transform.scale(sprite, (self.slot_size, self.slot_size))
                self.screen.blit(sprite, self.fuel_slot)
        pygame.draw.rect(self.screen, (0, 0, 0), (self.fuel_slot[0], self.fuel_slot[1], self.slot_size, self.slot_size), 2)
        fuel_text = self.font.render(f"Fuel: {self.stove.fluid_amount}/{self.stove.fluid_max_amount}", True, (0, 0, 0))
        self.screen.blit(fuel_text, (self.fuel_slot[0], self.fuel_slot[1] + self.slot_size + 5))

        # Стрелка
        pygame.draw.polygon(self.screen, (0, 200, 0), [
            (self.arrow_rect.left, self.arrow_rect.centery),
            (self.arrow_rect.right, self.arrow_rect.top),
            (self.arrow_rect.right, self.arrow_rect.bottom)
        ])

        # Кнопка рецептов
        pygame.draw.rect(self.screen, (0, 0, 200), self.recipe_button_rect)
        recipe_text = self.font.render("Recipes", True, (255, 255, 255))
        self.screen.blit(recipe_text, (self.recipe_button_rect.x + 10, self.recipe_button_rect.y + 5))

        # Окно рецептов
        if self.show_recipes:
            recipe_window = pygame.Rect(310, 150, 200, 200)
            pygame.draw.rect(self.screen, (150, 150, 150), recipe_window)
            for i, recipe in enumerate(self.recipes):
                text = self.font.render(f"{recipe['result']} ({', '.join(recipe['ingredients'])})", True, (0, 0, 0))
                self.screen.blit(text, (recipe_window.x + 10, recipe_window.y + 10 + i * 30))
            pygame.draw.rect(self.screen, (0, 0, 0), recipe_window, 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Кнопка рецептов
            if self.recipe_button_rect.collidepoint(mouse_pos):
                self.show_recipes = not self.show_recipes
                return
            # Стрелка (запустить готовку)
            if self.arrow_rect.collidepoint(mouse_pos) and not self.stove.is_cooking:
                self.start_cooking()
            # Слоты ингредиентов
            for i, pos in enumerate(self.slot_positions):
                slot_rect = pygame.Rect(pos[0], pos[1], self.slot_size, self.slot_size)
                if slot_rect.collidepoint(mouse_pos):
                    self.handle_slot_click(i)
            # Слот топлива
            fuel_rect = pygame.Rect(self.fuel_slot[0], self.fuel_slot[1], self.slot_size, self.slot_size)
            if fuel_rect.collidepoint(mouse_pos):
                self.handle_fuel_slot()
            # Слот результата
            result_rect = pygame.Rect(self.result_slot[0], self.result_slot[1], self.slot_size, self.slot_size)
            if result_rect.collidepoint(mouse_pos):
                self.take_result()

    def handle_slot_click(self, slot_index):
        # Добавляем ингредиент из инвентаря (заглушка)
        selected_item = self.get_selected_item()  # Нужно реализовать выбор предмета
        if selected_item and selected_item in self.items:
            if self.player.inventory.remove_item(selected_item):
                self.ingredient_slots[slot_index] = selected_item
                print(f"Добавлен {selected_item} в слот {slot_index}")

    def handle_fuel_slot(self):
        # Добавляем топливо
        selected_item = self.get_selected_item()
        if selected_item == "wood":
            if self.player.remove_item("wood"):
                self.stove.add_fuel(self.items["wood"]["fuel_value"])
                self.fuel_item = "wood"
                print("Добавлено топливо: wood")

    def take_result(self):
        if self.result_item:
            if self.player.inventory.add_item(self.result_item):
                self.result_item = None
                print(f"Получен результат: {self.result_item}")

    def start_cooking(self):
        ingredients = [slot for slot in self.ingredient_slots if slot]
        if not ingredients or len(ingredients) < 1:
            print("Нет ингредиентов для готовки")
            return
        if not self.stove.is_lit:
            print("Печка не зажжена")
            return
        if self.stove.fluid_amount < self.stove.cooking_cost:
            print("Недостаточно топлива")
            return

        # Проверяем рецепт
        for recipe in self.recipes:
            if sorted(ingredients) == sorted(recipe["ingredients"]):
                self.stove.is_cooking = True
                self.stove.cooking_timer = recipe["cooking_time"]
                self.stove.cooking_cost = self.stove.cooking_cost
                self.current_recipe = recipe
                self.ingredient_slots = [None] * len(self.ingredient_slots)
                print(f"Начата готовка: {recipe['result']}")
                return
        print("Рецепт не найден")

    def get_selected_item(self):
        # Заглушка: нужно реализовать выбор предмета из инвентаря
        return None  # Замените на реальную логику

    def update(self, dt, game_time):
        if self.stove.is_cooking and self.current_recipe and self.stove.cooking_timer <= 0:
            self.result_item = self.current_recipe["result"]
            self.current_recipe = None