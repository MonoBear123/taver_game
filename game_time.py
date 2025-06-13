import pygame
from config import PLAYER_STATE

class GameTimeManager:
    def __init__(self):
        self.hours = PLAYER_STATE.get('time_hours', 8)
        self.minutes = PLAYER_STATE.get('time_minutes', 0)
        self.day = PLAYER_STATE.get('day', 0) 
        self.time_scale = 2
        self.days_of_week = [
            "Понедельник", "Вторник", "Среда", "Четверг",
            "Пятница", "Суббота", "Воскресенье"
        ]

    def update(self, dt):
        self.minutes += dt * self.time_scale
        while self.minutes >= 60:
            self.minutes -= 60
            self.hours += 1
        while self.hours >= 24:
            self.hours -= 24
            self.day = (self.day + 1) % 7
        self.save_state()

    def save_state(self):
        PLAYER_STATE['time_hours'] = self.hours
        PLAYER_STATE['time_minutes'] = self.minutes
        PLAYER_STATE['day'] = self.day

    def get_time_string(self):
        return f'{self.hours}:{int(self.minutes):02d}', self.days_of_week[self.day]