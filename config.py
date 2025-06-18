from pygame.math import Vector2 as vec

WIN_WIDTH = 640
WIN_HEIGHT = 480
CURSOR_SIZE = (16,16)
TILE_SIZE = 48
FONT = 'assets/homespun.ttf'

INPUTS = {'escape': False,'space': False,'up': False,'down': False,'left': False,'right': False,
          'left_click': False,'right_click': False,'scroll_up': False,'scroll_down': False,'tab':False,'interact':False,
          "1":False,"2": False, "3": False, "4": False, "5": False,
          'mouse_pos': (0, 0)}

COLOURS = {'red':(255,100,100) ,'blue':(100,100,255),'black':(0,0,0),'white':(255,255,255),'green':(100,255,100),'gray':(50,50,50),'dark_gray':(30,30,30),'dark_purple': (48, 25, 52)}

LAYERS = ['background','objects','windows','decorations','cosmetics','lighting','characters','interactive']

SCENE_DATA = {
    'tavern':{'kitchen':'kitchen','toilet':'toilet','room1':'room1','room2':'room2','room3':'room3'},
    'kitchen':{'kitchen':'tavern'},
    'toilet':{'toilet':'tavern'},
    'room1':{'room1':'tavern'},
    'room2':{'room2':'tavern'},
    'room3':{'room3':'tavern'},
}

PLAYER_STATE = {
    'last_scene': 'tavern',
    'first_spawn': True,
    'energy': 100,
    'max_energy': 100,
    'time_hours': 8,
    'time_minutes': 0,
    'day': 0,
    'inventory': {
        'slots': []
    }
}

PLAYER_SPEED = 200
PLAYER_FORCE = 25
PLAYER_FRICTION = -15
INTERACTION_DISTANCE_MULTIPLIER = 1.5
PLAYER_LOW_ENERGY_THRESHOLD = 20
PLAYER_EXHAUSTED_THRESHOLD = 5
PLAYER_LOW_ENERGY_MULTIPLIER = 0.6
PLAYER_EXHAUSTED_MULTIPLIER = 0.3
BED_REST_AMOUNT = 80
TOILET_REST_AMOUNT = 10

NPC_IDLE_MIN_TIME = 5
NPC_IDLE_MAX_TIME = 15
NPC_SIT_MIN_TIME = 10
NPC_SIT_MAX_TIME = 20
NPC_ORDERING_MIN_TIME = 2
NPC_ORDERING_MAX_TIME = 4
NPC_FIND_CHAIR_TIMEOUT = 5
NPC_EATING_TIME_MULTIPLIER = 1.5
NPC_SPAWN_INTERVAL = 10 
NPC_SPAWN_MIN_CUSTOMERS = 5

ANIMATION_SPEED_WALK = 10
ANIMATION_SPEED_IDLE = 5

CURSOR_SIZE = (24,24)
WIN_WIDTH, WIN_HEIGHT = 1280, 720