'''
WaveWatch Bot V1.1

This bot can generate Battleship moves at multiple difficulty
levels and at it's highest attempts to play like a human. This file only
provides moves based on given ship locations and board sizes. 

   - Encapsulated version of Battleshell V1.6 AI
   - Meant to integrate into kiv_bshell
   - Allows for much easier updates

Author: Paul Belland
'''

import random
from collections import Counter
from bshell import *
VERSION = 1.1

# to humanize adv. search, a number between 0 and seed
# is randomly chosen and represents the number of random
# shots the computer will take before using adv. search
ADV_SEARCH_SEED = 3

class WaveWatch:
   def __init__(self,difficulty,b_size,ship_sizes):
      # basic info
      self.difficulty = difficulty
      self.b_size = b_size
      self.ship_sizes = ship_sizes
      
      # important
      self.ship_cells = []
      self.individual_ships = []
      self.shots = []
      self.good_shots = []
      self.state = 0   # 0 search, 1 sink, 2 stuck
      self.player_ships = None
      self.player_cells = None
      self.adv_seed = random.randint(0,ADV_SEARCH_SEED)
      
      # sink ship
      self.sink_ship_root = None
      self.sink_hits = []   # all cells known for ship
      self.sink_orientation = None
      self.sink_max = None
      self.sink_min = None
      
      # error correction
      self.last_shot_result = None  # 0 miss, 1 hit
      self.state_info = None  # information about fault search

      
   '''
   BASIC AI FUNCTIONS - START
   '''
      
   def start(self):
      '''
      Starts up AI and calls necessary methods
      '''
      self.build_positions()
      
   def set_player_pos(self, player_ships, player_cells):
      '''
      Keeps track of players positions for future hits. AI cannot
      use this information to cheat, only checks against to save time
      '''
      self.player_ships = player_ships
      self.player_cells = player_cells
      
   def get_ai_ships(self):
      '''
      Returns AI ship cells chosen after starting
      '''
      return self.ship_cells, self.individual_ships
      
   def get_shot(self):
      '''
      When called, based on difficulty, calculates
      firing solution against player. Returns chosen cell.
      '''
      diff = self.difficulty
      state = self.state
      if diff == 1:
         return self.random_shot()
      elif diff == 2:
         if state == 0:   # regular shot
            return self.random_shot()
         elif state == 1:   # attempt to sink ship
            return self.sink_ship()
         elif state == 2:
            return self.handle_faults()
      elif diff == 3:
         if state == 0:  # advanced shot (statistical)
            if self.adv_seed > 0:
               self.adv_seed -= 1
               return self.random_shot()
            return self.adv_search()
         elif state == 1:
            return self.sink_ship()
         elif state == 2:
            return self.handle_faults()
      
   def is_ship_overlap(self,indiv_ship,group_ships):
      '''
      Checks if the cells of an individual ship are inside of
      a larger group of ship cells. If overlap, return True
      '''
      for cell in indiv_ship:
         if cell in group_ships:
               return True
      return False
   
   def get_ship_cells(self,row,col,orientation,length):
         '''
         Returns all occupied ship cells based on ships data
         '''
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
      
   def matrix_to_num(self,row:int,col:int) -> int:
      '''
      Converts matrix positions into actual grid cells from
      1 to the size of the actual board
      '''
      row_num = row * self.b_size
      decoded_number = row_num + col
      return decoded_number
   
   def num_to_matrix(self,position:int) -> tuple:
      '''
      Converts grid cells to matrix rows and columns
      based on the size of the board
      '''
      row = (position)//self.b_size
      column = (position)%self.b_size
      return row, column
         
   def build_positions(self):
      '''
      Randomly populates ship positions for AI
      '''
      for ship in sorted(self.ship_sizes, reverse=True):
         found = 0  # 0 found, 100 unable to place
         while found < 100:
               orientation = random.choice(('v','h'))
               if orientation == 'v':
                  row_lim, col_lim = ship, 0
               else:
                  row_lim, col_lim = 0, ship
               row = random.choice((range(0,self.b_size-row_lim)))
               col = random.choice((range(0,self.b_size-col_lim)))
               cells = self.get_ship_cells(row,col,orientation,ship)
               if self.is_ship_overlap(cells,self.ship_cells):
                  found += 1
               else:
                  self.individual_ships.append(cells)
                  self.ship_cells = self.ship_cells + cells
                  found = 101
               if found == 100:
                  raise Exception('Error: No space for remaining ships!')
               
   '''
   AI SEARCHING FUNCTIONS
   '''
   
   def random_shot(self):
      '''
      Fires a shot randomly around the board, makes sure
      shot is on a fresh cell
      '''
      searching = True
      while searching:
         shot = random.choice(range(self.b_size**2))
         if shot not in self.shots:
            self.shots.append(shot)
            searching = False
         
            # activates sink mode
            if shot in self.player_cells and [shot] not in self.player_ships:
               self.sink_ship_root = shot
               self.sink_hits.append(shot)
               self.state = 1
               
            return shot
   
   def sink_ship(self):
      '''
      When in sink mode, attempts to sink the located ship
      as fast as possible by extending in a line
      '''
      # choose mode
      if self.sink_orientation == None:
         shot = self.sink_ship_orient()
      else:
         shot = self.sink_ship_extend()
      self.shots.append(shot)
      
      # check sunk
      if shot in self.player_cells:
         self.sink_hits.append(shot)
         
      for i in range(len(self.player_ships)):
         if set(self.player_ships[i]).issubset(set(self.shots)):
            self.good_shots = self.good_shots + self.sink_hits
            self.check_sink_fault(self.player_ships[i])   # CHANGE THIS
            self.sink_ship_reset()
            
      return shot
   
   def sink_ship_reset(self):
      '''
      When a ship has been sunk, resets the parameters of
      sink ship in preparation for next search round
      '''
      self.sink_hits = []
      self.sink_max = None
      self.sink_min = None
      self.sink_orientation = None
      self.sink_ship_root = None
      self.state = 0
   
   def sink_ship_extend(self):
      '''
      When in sink mode, this function is called to extend the line
      after an orientation has been found
      '''
      possibilities = []
      
      # get lower bound
      if self.sink_min == None:
         if self.sink_orientation == 'v':   # vertical
            lower_cell = min(self.sink_hits) - self.b_size
         else:
            lower_cell = min(self.sink_hits) - 1
         if self.sink_check_valid(lower_cell):
            possibilities.append(lower_cell)
            
      # get upper bound
      if self.sink_max == None:
         if self.sink_orientation == 'v':   # vertical
            upper_cell = max(self.sink_hits) + self.b_size
         else:
            upper_cell = max(self.sink_hits) + 1
         if self.sink_check_valid(upper_cell):
            possibilities.append(upper_cell)
            
      # trigger error correction, hitting multiple ships
      if not possibilities:
         self.state = 2
         self.state_info = ['EXTENSION',self.sink_hits]
         return self.handle_faults()  # logic handled there
         
      cell = random.choice(possibilities)
            
      # check if new limit hit
      if cell not in self.player_cells:
         if cell > self.sink_ship_root:
            self.sink_max = cell
         else:
            self.sink_min = cell
      return cell
      
   def sink_ship_orient(self):
      '''
      Attempts to find orientation of last hit ship
      '''
      possibilities = []
      root = self.sink_ship_root
      left,right = (root - 1), (root + 1)
      up,down = (root - self.b_size), (root + self.b_size)
      
      # checks if valid
      for pos in (left,right,up,down):
         if self.sink_check_valid(pos):
            possibilities.append(pos)
            
      # pick a possible cell, update orientation
      cell = random.choice(possibilities)
      if cell in self.player_cells:   # if good hit
         if cell == right or cell == left:
            self.sink_orientation = 'h'
         elif cell == up or cell == down:
            self.sink_orientation = 'v'
      
      return cell
      
   def sink_check_valid(self,cell):
      '''
      Based on the position of the root, checks if
      new possible firing positions are valid
      '''
      root = self.sink_ship_root
      
      # in board check
      upper_lim = (self.b_size ** 2) - 1
      if cell not in range(0,upper_lim):
         return False
      
      # same row check
      if self.num_to_matrix(root)[0] != self.num_to_matrix(cell)[0]:
         if root == (cell + 1) or root == (cell - 1):
            return False
      
      # existing shot check
      if cell in self.shots:
         return False
      return True
   
   def adv_search(self):
      '''
      Statistically checks most likely positions for player's longest ship
      around the board and reduces as fast as possible
      '''
      max_len = max(len(x) for x in self.player_ships)  # gets longest ship length
      hori_cells, vert_cells = self.adv_assemble_cells(max_len)  # assembles cells
      ship_list = self.adv_assemble_ships(hori_cells,vert_cells,max_len)  # assembles ships
      trimmed_ship_list = self.adv_trim(ship_list)
      ship_list = sum(trimmed_ship_list, [])  # flatten REMOVE / IMPROVE
      
      # choose statistically best shot
      possible = []
      c=Counter(ship_list)
      max_occurence=c.most_common(1)[0][1]
      for ele in c.most_common():
         if ele[1] == max_occurence:
               possible.append(ele[0])
      if possible:
         shot = random.choice(possible)
         self.shots.append(shot)
      else:
         return self.random_shot()
         
      # activates sink mode
      if shot in self.player_cells and [shot] not in self.player_ships:
         self.sink_ship_root = shot
         self.sink_hits.append(shot)
         self.state = 1
         
      return shot
      
   def adv_matrix(self):
      '''
      Creates a matrix to be used for the advanced search
      algorithm
      '''
      cell_number = 0
      matrix = []
      for row_ind in range(self.b_size):
         row = []
         for col_ind in range(self.b_size):
            row.append(cell_number)
            cell_number += 1
         matrix.append(row)
      return matrix
   
   def adv_assemble_cells(self, ship_len):
      '''
      Generates list of all possible h/v cells for next
      step in probability search
      '''
      # creates matrix replaced with cell values
      matrix_h = self.adv_matrix()
      matrix_v = self.adv_matrix()
      
      # trims matrix of non-possible horizontal cells, flattens
      for row in range(len(matrix_h)):
         for i in range(ship_len-1):
               matrix_h[row].pop(-1)
      matrix_h = sum(matrix_h, [])   # CHANGE
               
      # trims matrix of non-possible vertical cells, flattens
      for i in range(ship_len-1):
         matrix_v.pop(-1)
      matrix_v = sum(matrix_v, [])
               
      return matrix_h,matrix_v
   
   def adv_assemble_ships(self, hori_cells, vert_cells, ship_len):
      '''
      Given a list of valid cells, finds all possible ship locations
      '''
      pos_ship_locations = []
      for orient in (vert_cells,hori_cells):
         for i in range(len(orient)):
            temp_list = []
            temp_list.append(orient[i])
            
            # assemble hori
            if orient == hori_cells:
               for j in range(ship_len-1):
                  temp_list.append(orient[i]+j+1)
               pos_ship_locations.append(temp_list)
               
            # assemble vert
            if orient == vert_cells:
               for j in range(ship_len-1):
                  temp_list.append(vert_cells[i]+((j+1)*self.b_size))
               pos_ship_locations.append(temp_list)
      
      return pos_ship_locations
               
   def adv_trim(self, ship_list):
      '''
      Given list of ships, removes any that have
      been shot already
      '''
      temp_list = ship_list[:]  # copy to allow removal
      for i in range(len(ship_list)):
         for cell in self.shots:
            
               # if ship cell already shot, removes
               if ship_list[i].count(cell) != 0:
                  if ship_list[i] in temp_list:
                     temp_list.remove(ship_list[i])
                     
      return temp_list
   
   def check_sink_fault(self, ship_cells):
      '''
      Checks to make sure last player ship sunk matches the displayed
      length of the ship. If not, must change search to make sure ship other ships
      are sunk
      '''
      if len(self.sink_hits) != len(ship_cells):
         self.state = 2
         self.state_info = ['SINK_MISMATCH',None]
   
   '''
   FAULT HANDLING - START
   '''
   def handle_faults(self):
      '''
      Called when AI is in stuck state, handles all logic for
      finding ships until stuck state is resolved
      Returns attempted solution
      '''
      fault_type = self.state_info[0]
      if fault_type not in ('EXTENSION','SINK_MISMATCH'):
         raise Exception('Error: That type of fault does not exist')
      
      fault_info = self.state_info[1]
      
      # call correct type of fault correction
      if fault_type == 'EXTENSION':
         return self.handle_extension_fault(fault_info)
      elif fault_type == 'SINK_MISMATCH':
         return self.handle_mismatch_fault(fault_info)
      
   def handle_extension_fault(self, info):
      '''
      Called when line has been extended to max in both directions
      but ship has not been sunk. (hitting more than 1 ship)
      '''
      self.sink_ship_root
      
   def handle_mismatch_fault(self, info):
      '''
      Called when ship length of a sunk ship does not match the
      length of good hits on the attempted ship (hit more than one ship
      but only sunk one)
      '''
