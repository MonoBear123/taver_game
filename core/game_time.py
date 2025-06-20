from config import PLAYER_STATE

class GameTimeManager:
    def __init__(self):
        self.hours = PLAYER_STATE.get('time_hours', 8)
        self.minutes = PLAYER_STATE.get('time_minutes', 0)
        self.day = PLAYER_STATE.get('day', 0) 
        self.days_of_week = [
            "Понедельник", "Вторник", "Среда", "Четверг",
            "Пятница", "Суббота", "Воскресенье"
        ]

    def update(self, dt):
        self.minutes += dt 
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

    def advance_to_next_day(self):
        self.day = (self.day + 1) % 7
        self.hours = 8
        self.minutes = 0
        self.save_state()

    def get_time_string(self):
        time_str = f"{int(self.hours):02}:{int(self.minutes):02}"
        return time_str, self.days_of_week[self.day]

game_time = GameTimeManager()