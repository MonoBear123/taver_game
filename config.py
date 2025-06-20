from pygame.math import Vector2 as vec

WIN_WIDTH = 640
WIN_HEIGHT = 480
CURSOR_SIZE = (16,16)
TILE_SIZE = 48
CHARACTER_SPRITE_SIZE = (TILE_SIZE*1.2,TILE_SIZE*1.2)
FONT = 'assets/homespun.ttf'

INPUTS = {'escape': False,'space': False,'up': False,'down': False,'left': False,'right': False,
          'left_click': False,'right_click': False,'scroll_up': False,'scroll_down': False,'tab':False,'interact':False,
          "1":False,"2": False, "3": False, "4": False, "5": False,
          'mouse_pos': (0, 0)}

COLOURS = {'red':(255,100,100) ,'blue':(100,100,255),'black':(0,0,0),'white':(255,255,255),'green':(100,255,100),'gray':(50,50,50),'dark_gray':(30,30,30),'dark_purple': (48, 25, 52),'light_gray':(100,100,100)}

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
    "inventory": None,
    "position": None,
    "last_scene": None,
    "last_entry_point": None,
    "energy": 100,
    "max_energy": 100
}

def reset_player_state():
    global PLAYER_STATE
    PLAYER_STATE = {
        "inventory": None,
        "position": None,
        "last_scene": None,
        "last_entry_point": None,
        "energy": 100,
        "max_energy": 100
    }

SPEED = 200
FORCE = 2000
FRICTION = 0.1

NPC_SPEED = 200
NPC_FORCE = 1100
NPC_FRICTION = 0.1

INTERACTION_DISTANCE = 1.1
LOW_ENERGY = 20
VERY_LOW_ENERGY = 5
SPEED_LOW_ENERGY = 0.6
SPEED_VERY_LOW_ENERGY = 0.3
BED_REST_AMOUNT = 100
TOILET_REST_AMOUNT = 10

NPC_IDLE_MIN_TIME = 10
NPC_IDLE_MAX_TIME = 10
NPC_SIT_MIN_TIME = 10
NPC_SIT_MAX_TIME = 20
NPC_ORDERING_MIN_TIME = 10
NPC_ORDERING_MAX_TIME = 15
NPC_FIND_CHAIR_TIMEOUT = 10
NPC_EATING_TIME = 1.5
NPC_SPAWN_INTERVAL = 2
NPC_SPAWN_MIN_CUSTOMERS = 2

ANIMATION_SPEED_WALK = 8
ANIMATION_SPEED_IDLE = 5
