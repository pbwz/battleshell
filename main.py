'''
BattleShell Kivy V1.0

This program creates a GUI with multiple menus, allowing creation of Battleship
games against an AI or another player on the same network. It has persistent
settings and allows easy creation of BattleShell games with different settings.

Author: Paul Belland
'''

# SETS WINDOW SIZES MUST BE AT BEGINNING
from kivy import Config
Config.set('graphics', 'width', '880')
Config.set('graphics', 'height', '650')
Config.set('graphics', 'minimum_width', '800')
Config.set('graphics', 'minimum_height', '600')
Config.set('input', 'mouse', 'mouse,disable_multitouch')

# BASIC IMPORTS
from kivy.lang import Builder
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivy.uix.button import Button
from kivymd.uix.dialog import MDDialog
from kivy.clock import Clock
from kivymd.uix.snackbar import Snackbar
from bshell import *  # game plug-in
from bs_server import *
from bs_client import *
import random

SETTINGS_FILE = 'settings.txt'
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
EMPTY_CELL = 'assets/empty.png'
CROSSHAIR_CELL = 'assets/crosshair.png'
SQUARE_CELL = 'assets/square.png'
CIRCLE_CELL = 'assets/circle.png'
AXIS_COLOUR = (0,0,0,0)

class GameScreen(Screen):
    
    ### GENERAL ###
    def on_pre_enter(self):
        '''
        On entering the board, attempts to populate
        '''
        Clock.schedule_once(self.game_settings)
        Clock.schedule_once(self.load_game)
        Clock.schedule_once(self.set_in_progress,1)
        self.start_keyboard()
        
    def on_leave(self):
        '''
        Ensures all graphics are set correctly upon exiting Game Screen
        '''
        self.ids.btn_fire.md_bg_color = "#fc5c65"
        self.ids.btn_fire.icon = "crosshairs-gps"
        
    def start_keyboard(self):
        '''
        Sets up keyboard movement

        Keyboard movement adapted from: toto_tico (stackoverflow)
        '''
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
    def _keyboard_closed(self):
        '''
        Stops listening for keyboard movement
        '''
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None
        
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        '''
        Keyboard movement logic
        '''
        game = self.game
        result = False
        if game.get_phase() == 1:   # only runs if game in placing phase
            if keycode[1] in ('w','up'):
                result = game.move_ship('up')
            elif keycode[1] in ('s','down'):
                result = game.move_ship('down')
            elif keycode[1] in ('left','a'):
                result = game.move_ship('left')
            elif keycode[1] in ('right','d'):
                result = game.move_ship('right')
            elif keycode[1] in ('r'):
                result = game.move_ship('rotate')
            elif keycode[1] == 'enter':
                result = game.place_ship()
                if game.get_phase() == 1:
                    game.start_place_ship()
            if result:
                self.notification_box(result)
            if game.get_phase() == 2:
                self.update_board(self.game.get_boards(0),'Loading...')
                self.start_game()
            else:
                self.update_board(game.get_boards(0),'Placing Phase')
            return True
        
    def check_ready(self):
        '''
        Checks if other player has placed all ships before
        fully starting the multiplayer game
        '''
        if self.ready:
            if self.opponent_ships != []:
                self.game.set_opponent_ships(self.opponent_ships)
                self.flip_coin()
            else:
                self.update_board(self.game.get_boards(0),'Waiting...')
                self.ids.helper_text.text = 'Opponent is placing'
        
    def start_game(self):
        '''
        Starts game once player has placed all ships
        '''
        app = App.get_running_app()
        self.ready = True
        
        # multiplayer mode
        if app.server_started:
            ships = self.game.get_own_ships()
            
            # handles host setup
            if self.manager.get_screen('sc_multi').server:
                self.game.set_turn(self.get_starter(1))
                
                # sends ships and starter
                if self.game.get_turn() == 0:
                    self.manager.get_screen('sc_multi').server.send('GAME_INFO',(ships,1))
                else:
                    self.manager.get_screen('sc_multi').server.send('GAME_INFO',(ships,0))
                    
            self.check_ready()
                    
            # handles client setup
            if self.manager.get_screen('sc_multi').client:
                self.manager.get_screen('sc_multi').client.send('GAME_INFO',(ships,None))
        
        # singleplayer
        else:
            if app.randomize == 0:
                self.game.set_turn = self.get_starter(0)
            else:
                self.game.set_turn = self.get_starter(1)
            self.flip_coin()
        
    def get_starter(self, randomize):
        '''
        Returns the starter for the current game
        '''
        if randomize == 0:
            return 0
        else:
            return random.randint(0,1)
            
    def flip_coin(self):
        '''
        Shows the coin flip along with result on the player's board
        '''
        app = App.get_running_app()
        boards = self.game.get_boards()
        
        # change messages
        self.update_board(boards[self.displayed_board],'Choosing Starter')
        if not app.randomize and not app.server_started:
            self.ids.helper_text.text = 'Starter locked!'
        else:
            self.ids.helper_text.text = 'Flipping coin...'
            
        Clock.schedule_once(self.flip_coin_2, 3)

    def flip_coin_2(self,dt):
        '''
        Announces the result of the coin flip after 2 seconds.
        Starts game afterwards
        '''
        self.turn = self.game.get_turn()
        
        if self.turn == 0:
            msg = 'You start!'
            win_loss_msg = 'You won the coin flip!'
        else:
            msg = f'Opponent starts!'
            win_loss_msg = 'You lost the coin flip!'
            
        self.notification_box(msg)
        self.ids.helper_text.text = win_loss_msg
            
        self.game_loop(1) 

    def set_in_progress(self,dt):
        '''
        Sets the games state to in progress
        '''
        app = App.get_running_app()
        app.in_progress = True
        
    def load_game(self, dt):
        '''
        Loads game with valid settings
        '''
        app = App.get_running_app()
        self.populate_board(0)
        
        if not app.in_progress:
            self.start_new = False
            self.last_press = None   # for double click firing
            self.current_not = None
            self.turn = None  # 0: player, 1: computer
            self.displayed_board = 1
            self.ready = False
            
            if app.custom_ships:
                ship_list = sorted(app.ships)
            else:
                ship_list = [2,3,3,4,5]
            
            if app.server_started:
                self.game = Game(1, 10, [2,3,3,4,5], app.ai_diff)
            else:
                self.game = Game(0, self.b_size, ship_list, app.ai_diff)

            self.game.set_starter(1)
            self.game.start_game()
            self.game.start_place_ship()
            self.update_board(self.game.get_boards(0),'Placing Phase')
            self.ids.helper_text.text = 'WASD / R / Enter'
            self.update_stats()
    
    def update_stats(self):
        '''
        Updates stat section of screen with newest info
        '''
        game = self.game
        
        try:
            hit_p, shots, ai_hit_p, ai_ships = game.get_stats()
        except:
            m = 'N/A'
            hit_p, shots, ai_hit_p, ai_ships = m, m, m, m
            
        self.ids.hit_p.text = hit_p
        self.ids.shot_count.text = shots
        self.ids.ai_hit_p.text = ai_hit_p
        self.ids.ai_ship_count.text = ai_ships
        
    def new_game(self):
        '''
        Starts new game
        '''
        self.ids.btn_fire.md_bg_color = "#fc5c65"
        self.ids.btn_fire.icon = "crosshairs-gps"
        Clock.schedule_once(self.game_settings)
        Clock.schedule_once(self.load_game)
        Clock.schedule_once(self.set_in_progress,1)
        self.start_keyboard()
        
        self.notification_box('New game starting!')
              
    def game_loop(self, wait=0):
        '''
        Main game loop
        '''
        app = App.get_running_app()
        if wait == 0:
            wait = app.game_delay
        Clock.schedule_once(self.handle_turns,wait + 0.25)
        
        if self.game.get_turn() == 1:
            if not app.server_started:
                Clock.schedule_once(self.ai_response,wait + 0.75)
                
    ### MULTIPLAYER ###
    def game_settings(self, dt):
        '''
        Changes current game settings between AI and
        Multiplayer mode based on input
        - 0 AI, 1 Multi
        '''
        app = App.get_running_app()
        
        # AI MODE
        if not app.in_progress:
            if not app.server_started:
                self.b_size = app.b_size
                if app.custom_ships:
                    self.ships = sorted(app.ships)
                else:
                    self.ships = [2,3,3,4,5]
                self.ai_diff = app.ai_diff
                self.randomize = app.randomize
                app.opp_name = 'AI'
            
            # MULTI MODE
            else:
                self.b_size = 10
                self.ships = [2,3,3,4,5]
                self.opponent_ships = []
                self.ai_diff = 1
                self.randomize = app.randomize

    ### GAME RELATED ###
    def ai_response(self,dt):
        '''
        Gets AI shot and displays to player
        '''
        app = App.get_running_app()
        
        result = self.game.get_ai_shot()
        self.displayed_board = 0
        self.update_board(self.game.get_boards(0),'AI')
        response = self.game.check_game_over()
        
        if response != False:
            self.game_over(0, response)
        else:
            self.ids.helper_text.text = result
            Clock.schedule_once(self.opp_done,app.game_delay + 0.5)

    def opp_response(self, cell):
        '''
        Fires opponent shot on players screen
        '''
        app = App.get_running_app()
        
        result = self.game.set_opponent_shot(cell)
        self.update_board(self.game.get_boards(0),f'{app.opp_name}')
        response = self.game.check_game_over()
        
        if response != False:
            self.game_over(0, response)
        else:
            self.ids.helper_text.text = result
            Clock.schedule_once(self.opp_done,app.game_delay + 0.5)

    def opp_done(self,dt):
        '''
        Handles reset back to player shot after AI shot
        '''
        self.update_board(self.game.get_boards(1),'Your Turn')
        self.ids.helper_text.text = 'Good luck!'
        self.displayed_board = 1
            
    def handle_turns(self,dt):
        '''
        Handles changing turns after each shot
        '''
        app = App.get_running_app()
        game = self.game
        turn = game.get_turn()
        board = game.get_curr_board()
        if turn == 0:
            self.update_board(board,'Your Turn')
        else:
            self.update_board(board,f'{app.opp_name}')
    
    def update_board(self,information,player):
        '''
        When called updates the entirety of the board cells with
        the information provided (ie. hits, missed, etc.) and changes
        turn text.
        '''
        app = App.get_running_app()
        self.active_board_message = player
        board_dict = self.board_dict
        for i in range(len(information)):
            for j in range(len(information[i])):
                value = information[i][j]
                if value == 0:
                    symbol = EMPTY_CELL
                else:
                    if app.game_icon == 0:
                        symbol = CROSSHAIR_CELL
                    elif app.game_icon == 1:
                        symbol = CIRCLE_CELL
                    else:
                        symbol = SQUARE_CELL
                    
                if value == 0:
                    colour = [1,1,1,1]
                if value == 1:
                    colour = [1,1,1,1]
                elif value == 2:
                    colour = [1,0,0,1]
                elif value == 3:
                    colour = [1, 0.812, 0.137, 1]
                elif value == 5:
                    colour = [0.067, 0.424, 1, 1]
                    
                board_dict[(i,j)].background_normal = symbol
                board_dict[(i,j)].background_color = colour
        self.turn_box(player)
        self.update_stats()
        
    ### GUI RELATED ###
    def dismiss_dialog(self):
        '''
        Closes open dialogs
        '''
        if self.dialog:
            self.dialog.dismiss(force=True)
        
    def resign(self):
        '''
        Resignation handling
        '''
        rsn = MDRaisedButton(
            text="RESIGN", md_bg_color='#fc5c65')
        cancel = MDRaisedButton(
            text="CANCEL", md_bg_color='orange')
        
        self.dialog = MDDialog(
        title="Are you sure you would like to resign?",
        text="This game will not be recoverable",
        md_bg_color='#263238',
        buttons=[
            rsn, cancel],
        )
        rsn.on_press = self.game_over
        rsn.on_release = self.dialog.dismiss
        cancel.on_press = self.dialog.dismiss
        self.dialog.open()
        
    def switch_view(self):
        '''
        Handles logic for switching between board views.
        '''
        app = App.get_running_app()
        game = self.game
        boards = game.get_boards()
        
        # cases
        single_player = game.get_turn() == 0 and game.get_phase() != 1
        ended = game.get_phase() == 3
        multi_player = app.server_started and game.get_phase() != 1

        # chance view based on case
        if single_player or multi_player or ended:
            if self.displayed_board == 1:
                self.displayed_board = 0
                self.notification_box('Now viewing your ships')
            else:
                self.displayed_board = 1
                self.notification_box('Now viewing your shots')
            if self.turn == 1:
                self.update_board(boards[self.displayed_board],'Your Turn')
            else:
                self.update_board(boards[self.displayed_board],f'{app.opp_name}')
        else:
            self.notification_box('Cannot view until your turn')
            
    def turn_box(self,text):
        '''
        Allows updates to the turn/information box
        '''
        self.ids.turn_text.title = text
    
    def notification_box(self,text):
        '''
        When called creates a small textbox (SnackBar) and
        displays whatever text is passed
        '''
        if not self.current_not:
            notification = Snackbar(
                text=text,
                radius=[10,10,10,10],
                snackbar_x="300dp",
                snackbar_y="30dp",
                )
            notification.size_hint_x = (
                self.width - (notification.snackbar_x * 2)
            ) / self.width
            notification.open()
            self.current_not = notification
            Clock.schedule_once(self.dismiss_notification, 1)
        
    def dismiss_notification(self, dt):
        '''
        Dismisses notification box
        '''
        if self.current_not:
            self.current_not.dismiss()
            self.current_not = None

    def refocus_box(self, *args):
        '''
        Refocuses coords box after pressing enter
        '''
        self.ids.coord_box.focus = True
        
    def get_box_text(self):
        '''
        Get coord input and empty box
        '''
        self.fire_btn()
        Clock.schedule_once(self.refocus_box)
            
    def populate_board(self, dt):
        '''
        Fills in Game Board based off of settings
        '''
        app = App.get_running_app()
        if not app.in_progress:
            self.remove_grid()
            self.board_dict = {}
            b_size = self.b_size
            
            grid_layout = self.ids.board_layout
            grid_layout.cols =  b_size + 1
            grid_layout.add_widget(Button(background_color=(0,0,0,0)))
            
            # build board
            for i in range(0,b_size):   # creates top numbers
                button = Button(text = f"{i+1}",background_color=(AXIS_COLOUR))
                grid_layout.add_widget(button)
            
            # creates each individual row
            for row in range(0,b_size):
                letter = ALPHABET[row]
                button = Button(text = letter,background_color=(AXIS_COLOUR))
                grid_layout.add_widget(button)
                for i in range(0,b_size):
                    display_str = f"{letter}{i+1}"
                    button = Button(background_normal = 'empty.png')
                    self.board_dict[(row,i)] = button
                    button.bind(on_release=lambda instance,  # makes box clickable
                                x=display_str: self.update_box_text(x))
                    grid_layout.add_widget(button)
            
    def update_box_text(self,string):
        '''
        Updates coord box text
        '''
        self.ids.coord_box.text = string
        if self.last_press and string != '':
            if self.last_press == string:
                self.fire_btn()
                self.update_box_text('')
                self.last_press = None
                return
        self.last_press = string
    
    def remove_grid(self):
        '''
        Clears entire board
        '''
        rows = [i for i in self.ids.board_layout.children]
        for row1 in rows:
            self.ids.board_layout.remove_widget(row1)
            
    def verify_coords(self,coords):
        '''
        Verifies input of entered coords
        '''
        if len(coords) > 3:
            return False
        if coords[0] not in ALPHABET:
            return False
        if not coords[1].isnumeric():
            return False
        if len(coords) > 2:
            if not coords[2].isnumeric():
                return False
        b_size = App.get_running_app().b_size
        if b_size < int(coords[1:]):
            return False
        if int(coords[1:]) <= 0:
            return False
        return True  

    def fire_btn(self):
        '''
        Handles all logic for fire button
        '''
        app = App.get_running_app()
        coords = self.ids.coord_box.text.upper()
        if self.start_new:
            return self.new_game()
        if coords == '':
            self.notification_box('No cell chosen!')
        elif self.game.get_turn() == 0 and self.displayed_board == 1 and self.game.get_phase() != 1:
            if self.verify_coords(coords):
                self.update_box_text('')
                self.notification_box(f'Firing at cell {coords}')
                result = self.game.set_shot(coords)
                
                ###
                if app.server_started:
                    if self.manager.get_screen('sc_multi').server:
                        self.manager.get_screen('sc_multi').server.send('SHOT',coords)
                    else:
                        self.manager.get_screen('sc_multi').client.send('SHOT',coords)
                ###
                
                game_result = self.game.check_game_over()
                
                if game_result != False:
                    self.update_board(self.game.get_boards(1),'Game over!')
                    self.game_over(0, game_result)
                else:
                    self.update_board(self.game.get_boards(1),'Switching...')
                    self.ids.helper_text.text = result
                    self.game_loop()
            else:
                self.notification_box('That is not a cell!')
        elif self.game.get_turn() != 0:
            self.notification_box('Not your turn!')
        elif self.game.get_phase() == 1:
            self.notification_box('Place your ships first!')
        else:
            self.notification_box('Wrong board!')
            
    def game_over(self, mode=0, result=None):
        '''
        Runs when the game ends, whether someone wins or
        whether someone resigns
        '''
        app = App.get_running_app()
        self.update_board(self.game.get_boards(self.displayed_board),'Game Over!')

        # resignation/winner result logic
        if mode == 0:
            if result != None:
                message = result
            else:
                if app.server_started:
                    if self.manager.get_screen('sc_multi').server:
                        self.manager.get_screen('sc_multi').server.send('RESIGN',1)
                    else:
                        self.manager.get_screen('sc_multi').client.send('RESIGN',1)
                message = 'You resigned!'
        else:
            message = f'{app.opp_name} resigned!'
            
        app.in_progress = False
        self.start_new = True
        self.ids.helper_text.text = message
        
        # changes the fire button to new game button
        self.ids.btn_fire.icon = 'autorenew'
        self.ids.btn_fire.md_bg_color = 'lime'


class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        '''
        Sets settings properly on open
        '''
        app = App.get_running_app()
        self.ids.ship_list.clear_widgets()

        # build custom ship list cells
        for ship in app.ships:
            line_item = OneLineAvatarIconListItem(
                        IconLeftWidget(icon="sail-boat"))
            
            self.ids.ship_list.add_widget(line_item)
            line_item.text = str(ship)
            line_item.bind(on_release=lambda instance, x=line_item: self.pop_list(x))

        # fill in rest of settings with up-to-date info
        self.ids.b_size.text = str(app.b_size)
        self.ids.ai_diff.text = str(app.ai_diff)
        if app.randomize:
            self.ids.randomize.active = True
        else:
            self.ids.randomize.active = False
        if app.custom_ships:
            self.ids.custom_ships.active = True
        else:
            self.ids.custom_ships.active = False
            
        self.ids.delay.value = app.game_delay
        self.clicked_icon(app.game_icon)
            
    def pop_list(self, line_item):
        '''
        Shows dialog when removing ship from game settings
        '''
        confirm = MDRaisedButton(
            text="YES", md_bg_color='limegreen', font_size='20dp')
        
        ask = MDDialog(
        title="Are you sure you want to remove that ship?",
        size_hint=(0.4,0.2),
        md_bg_color='#263238',
        buttons=[
            confirm],
        )
        confirm.bind(on_press=lambda instance, x=line_item:
            self.ids.ship_list.remove_widget(x))
        confirm.bind(on_release=lambda x: ask.dismiss())
        
        ask.open()
        
    def add_list(self):
        '''
        Adds new ship to list based on size
        '''
        size = self.ids.ship_size.text
        line_item = OneLineAvatarIconListItem(
                IconLeftWidget(icon="sail-boat"))
        try:
            size = int(size)
        except:
            size = size
        if size not in ('',0) and isinstance(size, int):
            self.ids.ship_list.add_widget(line_item)
            line_item.text= str(size)
        self.ids.ship_size.text = ''
        line_item.bind(on_release=lambda instance, x=line_item: self.pop_list(x))
        
    def ok_dialog(self, title, message):
        '''
        Creates a dialog that does nothing. Confirmation dialog.
        Title and message can be given.
        '''
        confirm = MDRaisedButton(
            text="OK", md_bg_color='limegreen', font_size='20dp')
        
        ask = MDDialog(
        title=title,
        text=f'{message}',
        size_hint=(0.4,0.2),
        md_bg_color='#263238',
        buttons=[
            confirm],
        )
        confirm.bind(on_release=lambda x: ask.dismiss())
        ask.open()
        
    def set_settings(self,b_size,ai_diff):
        '''
        Globally sets all valid settings to the settings
        '''
        app = App.get_running_app()
        
        # sets other variables and values
        randomize, custom_ships = 0, 0
        if self.ids.randomize.active:
            randomize = 1
        if self.ids.custom_ships.active:
            custom_ships = 1
        app.b_size, app.ai_diff = b_size, ai_diff
        app.randomize, app.custom_ships = randomize, custom_ships
        
        # sets new ship list
        new_list = []
        for ship in self.ids.ship_list.children:
            ship = int(ship.text)
            new_list.append(ship)
        app.ships = new_list
        delay = app.game_delay
        icon = app.game_icon
        self.write_settings(b_size,ai_diff,randomize,custom_ships,new_list,delay,icon)

        # ends game if not multiplayer
        if app.server_started:
            self.ok_dialog('Settings applied!','Your game was not ended')
        else:
            app.in_progress = False
            self.ok_dialog('Settings applied!','Your game was ended')

        
    def write_settings(self,b_size,ai_diff,rand,cust,ships,delay,icon):
        '''
        Writes all the valid settings to the settings.txt file
        '''
        with open(SETTINGS_FILE, 'w') as settings:
            settings.write(f'B_SIZE: {b_size}\n')
            settings.write(f'RANDOMIZE: {rand}\n')
            settings.write(f'CUSTOM_SHIPS: {cust}\n')
            settings.write(f'AI_DIFFICULTY: {ai_diff}\n')
            settings.write(f'GAME DELAY: {delay}\n')
            settings.write(f'GAME ICON: {icon}\n\nSHIPS:\n')
            settings.write(','.join(str(i) for i in ships))
            
    def clicked_icon(self, number):
        '''
        For selecting which icon is clicked in settings
        '''
        app = App.get_running_app()
        selected = app.theme_cls.primary_color

        # resets all icons to white
        self.ids.icon_0.background_color = (1, 1, 1, 1)
        self.ids.icon_1.background_color = (1, 1, 1, 1)
        self.ids.icon_2.background_color = (1, 1, 1, 1)

        # highlights chosen icon
        if number == 0:
            self.ids.icon_0.background_color = selected
        elif number == 1:
            self.ids.icon_1.background_color = selected
        else:
            self.ids.icon_2.background_color = selected
    
    def apply_extra_settings(self):
        '''
        Applies the extra game (quality of life) settings
        '''
        app = App.get_running_app()
        delay = int(self.ids.delay.value)
        app.game_delay = delay

        # find which icon is highlighted
        if self.ids.icon_0.background_color == app.theme_cls.primary_color:
            icon = 0
        elif self.ids.icon_1.background_color == app.theme_cls.primary_color:
            icon = 1
        else:
            icon = 2

        # write to settings
        app.game_icon = icon
        self.write_settings(app.b_size, app.ai_diff, app.randomize, app.custom_ships, app.ships, delay, icon)
        self.ok_dialog('Settings applied!','Icon changes will apply next move')
        
    def verify_settings(self):
        '''
        Checks if all new settings values are valid
        '''
        problem = ''  # assumtes no problem
        
        new_bsize = self.ids.b_size.text
        try:   # validates board size
            new_bsize = int(new_bsize)
            if len(self.ids.ship_list.children) >= int(new_bsize):
                problem += f' Too many ships '
            if len(self.ids.ship_list.children) == 0:
                problem += f' No ships entered '
            if new_bsize not in range(2,27):
                problem += ' Board Size '
        except: 
            problem = 'Board Size'
        ai_diff = self.ids.ai_diff.text
        
        try:   # validates AI difficulty
            ai_diff = int(ai_diff)
            if ai_diff not in range(1,4):
                problem += ' AI Difficulty '
        except:
            problem += ' AI Difficulty '
        for ship in self.ids.ship_list.children:
            ship = int(ship.text)
            if ship not in range(1,new_bsize):
                problem += f' Ship ({ship}) bad size '
            
        if problem == '':
            self.set_settings(new_bsize,ai_diff)
        else:
            message = 'There was a problem applying\nthe following setting(s):'
            self.ok_dialog(message,problem)


class MultiplayerScreen(Screen):
    def validate_name(self):
        '''
        Checks if user entered a name
        '''
        if self.ids.multi_name.text == '':
            return 'Enter a name first!'
        return True

    def host(self):
        '''
        Controls host button logic
        '''
        app = App.get_running_app()
        display_text = self.ids.host.text
        if display_text == 'Host Game':
            
            if self.validate_name() != True:
                self.ids.multi_helper.text = self.validate_name()
            else:
                # start server
                self.server = Server(self.ids.multi_name.text)
                self.client = None
                self.ids.multi_disp.title = self.server.run()
                self.ids.multi_helper.text = 'You are now hosting a server'
                self.ids.connected_self.text = self.ids.multi_name.text
                self.ids.host.text = 'Stop hosting'
                self.ids.host.md_bg_color = 'red'
                app.my_name = self.ids.multi_name.text
                
                # check for opponent connection and response
                self.host_clock = Clock.schedule_interval(self.update_host, 1)
        
        else:
            
            self.reset_multi()
            
    def reset_multi(self):
        '''
        Resets multiplayer for client and server
        '''
        app = App.get_running_app()
        
        # reset graphics
        self.ids.host.text = 'Host Game'
        self.ids.host.md_bg_color = app.theme_cls.primary_color
        self.ids.connect.text = 'Connect to Game'
        self.ids.connect.md_bg_color = app.theme_cls.primary_color
        self.ids.multi_disp.title = "You're Offline"
        self.ids.multi_helper.text = 'Please enter your name then select an option!'
        self.ids.connected_self.text = ''
        self.ids.connected_opp.text = ''
        app.my_name = None
        app.root.ids.icon_opponent.icon = 'desktop-tower'
        
        # server reset
        if self.server:
            self.server.close()
            self.server = None
            self.host_clock.cancel()
        if self.client:
            self.client.close()
            self.client = None
            self.client_clock.cancel()
            
        app = App.get_running_app()
        app.server_started = False
        app.opp_name = None
        
    def update_host(self, dt):
        '''
        Handles all information received from connected client
        '''
        app = App.get_running_app()
        
        # wait for connection
        if app.server_started == False:
            response = self.server.search()
            if response != False:
                self.ids.multi_disp.title = response
                app.server_started = True
                app.root.ids.icon_opponent.icon = 'account-multiple'
                self.manager.get_screen('sc_game').new_game()
                app.in_progress = False   
                
        # opponent response
        if app.server_started == True:
            ident, data = self.server.refresh()
            if data:
                if ident == 'Name':
                    app.opp_name = data
                    self.ids.connected_opp.text = data
                elif ident == 'Status':
                    self.handle_status(data)
                else:
                    self.handle_received(ident, data)
                    
    def handle_received(self,ident,data):
        '''
        Handles any received response from opponent
        '''
        if ident == 'B_SIZE':
            self.ids.multi_b_size.text = data
        if ident == 'GAME_INFO':
            self.manager.get_screen('sc_game').opponent_ships = data[0]
            if data[1] != None:
                self.manager.get_screen('sc_game').game.set_turn(data[1])
            self.manager.get_screen('sc_game').check_ready()
        if ident == 'SHOT':
            self.manager.get_screen('sc_game').opp_response(data)
        if ident == 'NOTIF':
            self.manager.get_screen('sc_game').notification_box(data)
        if ident == 'RESIGN':
            self.manager.get_screen('sc_game').game_over(1)
        
    def start_client(self):
        '''
        Starts clients connection to host
        '''
        app = App.get_running_app()
        display_text = self.ids.connect.text
        if display_text == 'Connect to Game':
            if self.validate_name() != True:
                self.ids.multi_helper.text = self.validate_name()
            else:
                # start client and connect to main server
                self.client = Client(self.ids.multi_name.text)
                self.server = None
                app.server_started = True
                response = self.client.run()
                self.ids.multi_disp.title = response
                app.my_name = self.ids.multi_name.text
                
                # check for opponent response
                if response == 'Connected to host!':
                    self.ids.connect.text = 'Disconnect'
                    self.ids.connect.md_bg_color = 'red'
                    self.ids.connected_self.text = self.ids.multi_name.text
                    self.client_clock = Clock.schedule_interval(self.update_client, 1)
                    app.root.ids.icon_opponent.icon = 'account-multiple'
                    self.manager.get_screen('sc_game').new_game()
                    self.manager.get_screen('sc_game').notification_box('P2 Connected!')
                    app.in_progress = False  
                
        else:
            self.reset_multi()
        
    def update_client(self, dt):    
        '''
        Handles all information received from host
        '''
        app = App.get_running_app() 
        
        # opponent response
        if app.server_started == True:
            ident, data = self.client.refresh()
            if data:
                if ident == 'Name':
                    app.opp_name = data
                    self.ids.connected_opp.text = data
                    self.client.send('Name',app.my_name)
                elif ident == 'Status':
                    self.handle_status(data)
                else:
                    self.handle_received(ident, data)
                    
    def handle_status(self, data):
        '''
        Handles status data sent through socket
        '''
        if data == 'Disconnected':
            self.manager.get_screen('sc_game').notification_box('P2 Disconnected')
            self.manager.get_screen('sc_game').game_over(1)
            self.reset_multi()
        
class AboutScreen(Screen):
    pass

class BattleShell(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.material_style = 'M3'
        Window.size = (880, 650)
        self.root = Builder.load_file('BattleShell.kv')
        return self.root
    
    def on_start(self):
        '''Reads settings file'''
        self.in_progress = False
        self.server_started = False
        self.opp_name = None
        self.my_name = None

        # reads file and gets data
        with open(SETTINGS_FILE, 'r') as settings:
            data = settings.readlines()
            for i in range(len(data)):
                data[i] = data[i].strip().split(': ')
            try:
                self.b_size = int(data[0][1])
                self.randomize = int(data[1][1])
                self.custom_ships = int(data[2][1])
                self.ai_diff = int(data[3][1])
                self.game_delay = int(data[4][1])
                self.game_icon = int(data[5][1])
                self.ships = []
                for ship in data[-1][0].split(','):
                    self.ships.append(int(ship))
            except:
                raise Exception('Settings file formatted incorrectly!')


if __name__ == '__main__':
    BattleShell().run()
