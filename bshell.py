'''
BattleShell V1.8 Standalone

This program can be used to play Battleship in either multiplayer
or against a computer algorithm. This file only handles the game logic
and does not include the AI or any display.

CHANGELOG (1.8):
   - ADDED MULTIPLAYER MODE

Author: Paul Belland
'''

### BASIC SETUP ###
from ai import *
import random
from collections import Counter
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
OOB_MSG = 'Out of bounds!'
VERSION = 1.8

### CELL VALUES ###
EMPTY = 0
MISS = 1
HIT = 2
PLACING = 3
FRIENDLY = 5

class Game:
    def __init__(self,opp,b_size,ship_list,ai_diff=1) -> None:
        # MAIN GAME SETTINGS
        self.ship_sizes = []
        self.ships_to_place = 0
        self.verify_settings(opp,b_size,ship_list,ai_diff)
        self.opponent = opp   # 0 AI, 1 MULTIPLAYER
        self.b_size = b_size   # 2-26
        self.ai_diff = ai_diff   # 1-3
        for ship in ship_list:
            self.ship_sizes.append(ship)
            self.ships_to_place += 1
        
        # PLAYER AND GAME LOOP
        self.starter = None
        self.phase = 0   # 0: start, 1: placing, 2: battle, 3: ended
        self.turn = 1  # 0 is player, 1 is opponent
        self.own_board = None
        self.shot_board = None
        self.player_cells = []
        self.last_placement = []
        self.individual_locations = []
        self.player_shots = []
        
        # OPPONENT SETUP
        self.ai = None
        self.opp_ship_cells = None
        self.opp_indiv_ships = None
        self.opp_shots = []
        if opp == 0:
            self.opp_name = 'The AI'
        else:
            self.opp_name = 'Other player'
        
        # GAME STATISTICS
        self.shot_count = 0
        self.hit_count = 0
        self.opp_shot_count = 0
        self.opp_hit_count = 0

    ### REGULAR METHODS ###
        
    def verify_settings(self,opp,b_size,ship_list,ai_diff):
        '''Makes sure the settings entered for the game are valid'''
        # opponent check
        if opp not in (0,1):
            raise Exception('Game Error: Opponent not set')
        
        # board size check
        if b_size not in range(2,27):
            raise Exception('Game Error: Tried to set board size outside of 2-26')
        
        # ship check
        self.verify_ships(ship_list, b_size)
        
        # ai difficulty check
        if ai_diff not in range(1,4):
            raise Exception('Game Error: AI Difficulty not set')
        
        
    def verify_ships(self, ship_list, b_size):
        '''
        Verifies that ship list is valid
        '''
        if not ship_list:
            raise Exception('Game Error: No ship list provided')
        
        if max(ship_list) > (b_size - 1):
            raise Exception(f'Game Error: At least one ship is too long')
            
        if len(ship_list) > b_size:   # checks for total ships
            raise Exception('Game Error: Too many ships for this board size')
        
        
    def start_game(self):
        '''
        Starts the game and needed portions
        '''
        # starts game
        self.build_matrix()
        
        # checks if starter set
        if self.starter == None:
            raise Exception('Game Error: Starter not set!')
        else:
            self.turn = self.starter
        
        if self.opponent == 0:
            self.start_ai()
            return 'Game starting!'
        else:
            return 'Waiting for opponent!'
        
        
    def update_board(self,board,cells,cell_type):
        '''
        Updates the given board with cells of a certain type
        '''
        for cell in cells:
            row,col = self.num_to_matrix(cell)
            board[row][col] = cell_type


    def get_curr_board(self):
        '''
        Returns the board corresponding to the current turn
        Player (shot board), AI (player board)
        '''
        if self.turn == 0:
            return self.shot_board
        return self.own_board

    
    def set_opponent_shot(self, shot):
        '''
        Fires opponents shot, converts if possible
        '''
        shot = self.shot_input_verify(shot)
        return self.opponent_fire(shot)
    
    
    def set_opponent_ships(self, ship_list):
        '''
        Sets opponent ships up if playing in multiplayer mode
        '''
        # check if in right mode
        if self.opponent == 0:
            raise Exception('Game Error: Game is in AI mode, cannot change ships')
        #if self.phase != 1:
        #    raise Exception('Game Error: Cannot change ships after placing phase')
        
        check_list = []
        for ship in ship_list:
            check_list.append(len(ship))
        self.verify_ships(check_list, self.b_size)   # check if valid
        
        self.opp_indiv_ships = []
        self.opp_ship_cells = []
        for ship in ship_list:
            self.opp_indiv_ships.append(ship)
            for cell in ship:
                self.opp_ship_cells.append(cell)
        
    
    def get_ai_shot(self):
        '''
        Returns cell chosen by the AI based on current game settings
        '''
        # check if in wrong game mode
        if self.opponent == 1:
            raise Exception('Game Error: Game is set to Multiplayer mode, AI cannot shoot')
        
        # check if turn is right
        if self.turn == 0:
            raise Exception('Game Error: AI cannot shoot, wrong turn')
        
        shot = self.ai.get_shot()
        return self.opponent_fire(shot)   # shoots

        
    def opponent_fire(self, cell):
        '''
        Given a cell, checks if the opponents shot is a hit or miss,
        then updates the board and statistics
        '''
        self.opp_shot_count = self.opp_shot_count + 1   # updates stats
        
        # already shot
        if cell in self.opp_shots:
            self.turn = 0
            return 'Your opponent wasted a turn!'
        self.opp_shots.append(cell)
        
        # hit case
        if cell in self.player_cells:
            self.opp_hit_count = self.opp_hit_count + 1   # updates stats
            self.update_board(self.own_board,[cell],HIT)
            was_sunk = self.check_sunk()
            if was_sunk != False:
                result = was_sunk
            else:
                result = 'Your ship was hit!'
                
        # miss case
        else:
            self.update_board(self.own_board,[cell],MISS)
            result = f'{self.opp_name} missed!'
        self.turn = 0
        return result 

    
    def check_sunk(self):
        '''Checks if any ship was sunk when called, must be called
        after a player has shot but still in the same turn.'''
        # determines last shooter info
        if self.turn == 0:   # player
            ships = self.opp_indiv_ships
            shots = self.player_shots
        else:  # opponent
            ships = self.individual_locations
            shots = self.opp_shots
            
        # checks each individual ship
        index = None
        for i in range(len(ships)):
            if set(ships[i]).issubset(set(shots)):   # checks if all cells are hit
                index = i
        
        # removal and announce
        if index != None:
            sunk_len = len(ships.pop(index))
            if self.turn == 0:
                return f'You sunk a ship! ({sunk_len})'
            return f'Your ship was sunk! ({sunk_len})'
        return False
    
    
    def check_game_over(self):
        '''Checks if anyone won the game off of the last move
        0 - no winner
        1 - player wins
        2 - ai wins'''
        if self.phase == 2:
            if len(self.individual_locations) == 0:
                self.phase = 3
                self.reveal_ship()
                return f'{self.opp_name} won the game!'
            if len(self.opp_indiv_ships) == 0:
                self.phase = 3
                return 'You won the game!'
        return False
    
    
    def start_ai(self):
        '''Starts AI with all needed game info'''
        try:
            self.ai = WaveWatch(self.ai_diff,self.b_size,self.ship_sizes)
            self.ai.start()
            self.opp_ship_cells, self.opp_indiv_ships = self.ai.get_ai_ships()
        except:
            raise Exception('Game Error: AI object failed to start')
        
        
    def get_phase(self):
        '''
        Returns the games current phase value
        '''
        return self.phase
    
        
    def get_turn(self):
        '''
        Returns the games current turn
        '''
        return self.turn
    
    
    def set_turn(self, turn):
        '''
        Sets the turn
        '''
        # check if valid
        if turn not in (0,1):
            raise Exception('Game Error: Tried setting illegal turn (not in 0,1)')
        self.turn = turn
        
        
    def get_own_ships(self):
        '''
        Returns a list containg all of the player's ships
        '''
        return self.individual_locations
        
        
    def set_starter(self, starter):
        '''Sets who starts the game'''
        # check if valid
        if starter not in (0,1):
            raise Exception('Game Error: Tried setting illegal starter (not in 0,1)')
        self.starter = starter
        
    
    def get_boards(self, choice=2):
        '''
        Returns both boards
        '''
        if choice == 2:   # if no argument, return both
            return self.own_board, self.shot_board
        elif choice == 1:   # return shot board
            return self.shot_board
        return self.own_board   # return player board
    
        
    def build_matrix(self):
        '''
        Creates the players ship matrix and shot matrix
        '''
        for board in range(2):
            matrix = []
            for row in range(self.b_size):
                row = []
                for col in range(self.b_size):
                    row.append(EMPTY)
                matrix.append(row)
            if board == 0:
                self.own_board = matrix
            else:
                self.shot_board = matrix
                
            
    def matrix_to_num(self,row:int,col:int) -> int:
        '''Converts matrix positions into actual grid cells from
        1 to the size of the actual board'''
        row_num = row * self.b_size
        decoded_number = row_num + col
        return decoded_number
    
    
    def num_to_matrix(self,position:int) -> tuple:
        '''Converts grid cells to matrix rows and columns
        based on the size of the board'''
        row = (position)//self.b_size
        column = (position)%self.b_size
        return row, column
    
    
    def let_num_to_num(self,str_let_num):
        '''Accepts a letter and number only! Converts to a number
        position somewhere on the grid.'''
        for letter in ALPHABET:
            if str_let_num[0] == letter:
                index = ALPHABET.index(letter)*self.b_size
        decoded_number = index + int(str_let_num[1:])-1
        return decoded_number
    
    
    def shot_input_verify(self, shot):
        '''
        Verify that shot input is correct
        '''
        board_msg = 'Game Error: Given cell is outside of board'
        format_msg = 'Game Error: Given cell format was not supported'
        shot = shot.capitalize()
        
        # try to convert A26 to cell
        if shot[0] in ALPHABET:
            try:
                shot = self.let_num_to_num(shot)   # valid
            except IndexError:
                raise Exception(board_msg)
            except ValueError:
                raise Exception(format_msg)
            
        # check if in board
        if str(shot).isnumeric():
            if int(shot) not in range(0, self.b_size ** 2):
                raise Exception(board_msg)
            else:
                return shot   # valid
            
        raise Exception(format_msg)
    
    
    def set_shot(self, shot):
        '''
        Fires player's shot, converts if possible
        '''
        shot = self.shot_input_verify(shot)
        return self.fire(shot)
    
    
    def reveal_ship(self):
        '''
        When called, reveals all unhit ship cells on the opponent's board
        '''
        if self.opp_ship_cells:
            for cell in self.opp_ship_cells:
                row, col = self.num_to_matrix(cell)
                if self.shot_board[row][col] != 2:
                    self.shot_board[row][col] = 3
    
    
    def fire(self, cell):
        '''
        Fires player's sho
        '''
        self.shot_count = self.shot_count + 1   # updates stats
        
        # already shot case
        if cell in self.player_shots:
            self.turn = 1
            return 'You shot at that cell already! (wasted turn)'
        self.player_shots.append(cell)
        
        # hit case
        if cell in self.opp_ship_cells:
            self.hit_count = self.hit_count + 1   # updates stats
            self.update_board(self.shot_board,[cell],HIT)
            was_sunk = self.check_sunk()
            if was_sunk != False:
                result = was_sunk
            else:
                result = 'You hit a ship!'

        # miss case
        else:
            self.update_board(self.shot_board,[cell],MISS)
            result = 'You missed!'
        self.turn = 1
        return result
        
    
    def get_stats(self):
        '''
        Returns the statistics that the Game class keeps track of
        '''
        opp_hits = self.opp_hit_count
        opp_shots = self.opp_shot_count
        opp_ships = str(len(self.opp_indiv_ships))
        
        # calculate hit %
        try:
            hit_perc = round((self.hit_count / self.shot_count) * 100,2)
        except ZeroDivisionError:
            hit_perc = '-'
            
        # calculate opponent hit %
        try:
            opp_hit_perc = round((opp_hits / opp_shots) * 100,2)
        except ZeroDivisionError:
            opp_hit_perc = '-'
            
        return str(hit_perc), str(self.shot_count), str(opp_hit_perc), opp_ships
            
            
    ### SHIP PLACEMENT METHODS ###
            
            
    def randomize_placement(self,ship_len):
        '''
        Returns a randomly selected legal set of cells to place
        the ship around the board
        '''
        found = 0  # 0 found, 100 unable to place
        while found != 100:
            orientation = random.choice(('v','h'))
            if orientation == 'v':
                row_lim, col_lim = ship_len, 0
            else:
                row_lim, col_lim = 0, ship_len
            row = random.choice((range(0,self.b_size-row_lim)))
            col = random.choice((range(0,self.b_size-col_lim)))
            cells = self.get_ship_cells(row,col,orientation,ship_len)
            if self.is_ship_overlap(cells,self.player_cells):
                found += 1
            else:
                return cells
        raise Exception('Error: No space for remaining ships!')
    
    
    def get_ship_cells(self,row,col,orientation,length):
        '''Returns all occupied ship cells based on ships data'''
        cells = [self.matrix_to_num(row,col)]   # adds first cell
        
        # sets data for placement loop
        if orientation == 'v':
            static, dynamic = col, row
        else:
            static, dynamic = row, col
            
        # placement loop
        for cell in range(length-1):
            dynamic += 1
            if orientation == 'v':
                cells.append(self.matrix_to_num(dynamic,static))
            else:
                cells.append(self.matrix_to_num(static,dynamic))
        return cells
            
        
    def start_place_ship(self):
        '''
        Grabs a ship and begins placement process
        '''
        board = self.own_board
        ships = self.ship_sizes
        self.phase = 1
        if len(ships) == 0:
            raise Exception('Game Error: No more ships to place')
        
        # places ship and updates board
        ship = ships[self.ships_to_place - 1]  # selects individual ship
        cells = self.randomize_placement(ship)
        self.update_board(board,cells,PLACING)
        self.last_placement = cells[:]
        
        
    def place_ship(self):
        '''
        Places the ship on the board when Player is happy with
        the position. Returns message if unable to place
        '''
        ship_cells = self.last_placement
        player_cells = self.player_cells
        if not self.is_ship_overlap(ship_cells,player_cells):
            self.ships_to_place -= 1
            self.update_board(self.own_board, ship_cells, FRIENDLY)
            self.individual_locations.append(ship_cells)
            self.player_cells = player_cells + ship_cells
            if self.ships_to_place == 0:
                if self.ai:
                    self.ai.set_player_pos(self.individual_locations,self.player_cells)
                self.phase = 2
                return 'Done placing!'
            return 'Ship placed successfully!'
        else:
            self.update_board(self.own_board, self.last_placement, EMPTY)
            self.update_board(self.own_board, self.player_cells, FRIENDLY)
            return 'Ships cannot overlap!'
        
        
    def check_out_of_bounds(self,cell_list):
        '''
        Checks if player placement moves are illegal
        Returns True of OOB, False if legal
        '''
        # converts to matrix values for analysis
        orientation = self.check_orientation(cell_list)
        rows, cols = [], []
        for pos in cell_list:
            row, col = self.num_to_matrix(pos)
            rows.append(row), cols.append(col)
            
        # checks all in same file
        if orientation == 'h':
            if rows.count(rows[0]) != len(rows):
                return True
        elif orientation == 'v':
            if cols.count(cols[0]) != len(cols):
                return True
            
        # checks violating borders
        for row in rows:
            if row >= self.b_size or 0 > row:
                return True
        for col in cols:
            if col >= self.b_size or 0 > col:
                return True
        return False
    
        
    def check_orientation(self,cell_list):
        '''
        Gets ship (v/h) orientation of cell list
        '''
        # accounts for 1 long ships
        if len(cell_list) == 1:
            return 'v'
        
        # all other cases
        if (cell_list[0] + 1) != cell_list[1]:
            return 'v'
        else:
            return 'h'
        
        
    def move_ship(self,command):
        '''Moves ship based on direction or places ship'''
        attempted_pos = self.last_placement[:]   # copy in case illegal
        if command == 'rotate':
            response = self.rotate(attempted_pos)
            return response
        elif command == 'left':
            change = -1
        elif command == 'right':
            change = 1
        elif command == 'up':
            change = -self.b_size
        elif command == 'down':
            change = self.b_size
        
        # executes move and checks if valid
        for i in range(len(attempted_pos)):
            attempted_pos[i] = attempted_pos[i] + change
        illegal = self.check_out_of_bounds(attempted_pos)
        if not illegal:
            self.execute_move(attempted_pos)
        else:
            return OOB_MSG
        
        
    def is_ship_overlap(self,indiv_ship,group_ships):
        '''Checks if the cells of an individual ship are inside of
        a larger group of ship cells. If overlap, return True'''
        for cell in indiv_ship:
            if cell in group_ships:
                return True
        return False
        
            
    def execute_move(self,new_pos):
        '''Now that move has been processed and verified,
        updates board'''
        board = self.own_board
        self.update_board(board,self.last_placement,EMPTY)
        self.update_board(board,new_pos,PLACING)
        self.update_board(self.own_board, self.player_cells, FRIENDLY)
        self.last_placement = new_pos   # keeps track of this as last move
        
        
    def rotate(self,cell_list):
        '''Rotates ship currently being placed'''
        orientation = self.check_orientation(cell_list)
        rows, cols = [], []
        for pos in cell_list:
            row, col = self.num_to_matrix(pos)
            rows.append(row), cols.append(col)
            
        if orientation == 'v':
            for i in range(len(rows)):
                cols[i] = cols[0] + i
                rows[i] = rows[0]
        else:
            for i in range(len(rows)):
                rows[i] = rows[0] + i
                cols[i] = cols[0]  
                
        new_cells = []
        for i in range(len(cell_list)):
            cell = self.matrix_to_num(rows[i],cols[i])
            new_cells.append(cell)
        
        if not self.check_out_of_bounds(new_cells):
            self.execute_move(new_cells)
