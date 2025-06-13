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

COLOURS = {'red':(255,100,100) ,'blue':(100,100,255),'black':(0,0,0),'white':(255,255,255),'green':(100,255,100),'gray':(50,50,50),'dark_gray':(30,30,30)}

LAYERS = ['background','objects','windows','decorations','lighting','characters','interactive','foreground']

SCENE_DATA = {
    'tavern':{'kitchen':'kitchen','toilet':'toilet','room1':'room1','room2':'room2','room3':'room3'},
    'kitchen':{'kitchen':'tavern'},
    'toilet':{'toilet':'tavern'},
    'room1':{'room1':'tavern'},
    'room2':{'room2':'tavern'},
    'room3':{'room3':'tavern'},
}

PLAYER_STATE = {
    'energy': 100,
    'max_energy': 100,
    'first_spawn': True,
    'inventory': None,
    'time_hours': 8,
    'time_minutes': 0,
    'day': 0
}