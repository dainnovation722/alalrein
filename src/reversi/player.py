from abc import ABC
from abc import abstractclassmethod
from reversi.board import ReversiBoard
import random
import numpy as np
from copy import deepcopy

class Player(ABC):

    """Abstract base class of Reversi Player.

    Each player class must be a subclass of this class.
    """

    def set_color(self, color):
        """Sets the player's stone color.

        Args:
            color(str): color must be ``ReversiBoard.BLACK`` or
                ``ReversiBoard.WHITE``.
        """
        if color not in (ReversiBoard.BLACK, ReversiBoard.WHITE):
            msg = "``color`` must be '{}' or '{}'.".format(
                ReversiBoard.BLACK, ReversiBoard.WHITE)
            raise ValueError(msg)
        self.color = color

    @abstractclassmethod
    def action(self, state, possible_hand):
        """Generates next action.

        Args:
            state(str): A string representing the game status.
                The state must be of the form:

                    '--------
                     --------
                     --------
                     ---wb---
                     ---bw---
                     --------
                     --------
                     --------,-_0,b,-'

                    - 'w': white stone.
                    - 'b': black stone.
                    - '-': blank space.

                The above example means that the board is in the initial state,
                the previous player's hand is None('-_0'), the next player is
                black('b'), and the winner has not been decided('-').
            possible_hand(str): Places where player can put the stone (comma
                separated).

        Returns:
            action (str): A string represention of the next action.
                The ``action`` must be of the form:

                    '{my color}_{place}'

                Each place on the board is represented as follows:

                    [[ 1  2  3  4  5  6  7  8]
                     [ 9 10 11 12 13 14 15 16]
                     [17 18 19 20 21 22 23 24]
                     [25 26 27 28 29 30 31 32]
                     [33 34 35 36 37 38 39 40]
                     [41 42 43 44 45 46 47 48]
                     [49 50 51 52 53 54 55 56]
                     [57 58 59 60 61 62 63 64]]

                * ``0`` means ``PASS``.

        """
        pass

    @abstractclassmethod
    def finalize(self, state, winner):
        """Finalizes the game.

        The final state and the winner of the game are told to the player using
        this method.
        """
        pass


class RandomPlayer(Player):

    """Revirsi Player acts randomly."""

    def __init__(self, name, reward_win=1., reward_draw=0., reward_lose=-1.):
        self.name = name
        self.reward_win = reward_win
        self.reward_draw = reward_draw
        self.reward_lose = reward_lose
        self.record = []
        
    def action(self, state, possible_hand, episode):
        hand = random.choice(possible_hand.split(',')) #listからrandomに位置(str型)を選択
        action = '{}_{}'.format(self.color, hand)
        return action

    def finalize(self, state, winner):
        if winner == self.color:
            r = self.reward_win
        elif winner == 'd':
            r = self.reward_draw
        else:
            r = self.reward_lose

        self.record.append(r)


class NNQPlayer(Player):

    def __init__(self, name, q_function, memory,
                 reward_win=1., reward_draw=0., reward_lose=-1.,
                 eps=0.05):
        self.name = name
        self.reward_win = reward_win
        self.reward_draw = reward_draw
        self.reward_lose = reward_lose
        self.eps = eps

        self.q_function = q_function
        self.memory = memory

        self.s_last = None
        self.a_last = None
   
        self.record = []


    def action(self, state, possible_hand, episode):
        state = state.split(',')[0]
        state = [i for i in state if i in ['b','w','-']]
        s = [(0 if i == '-' else (1 if i == self.color else -1)) for i in state]
        possible_hand = [int(i) for i in possible_hand.split(',')]
  
        matrix = np.array(s).reshape(8,8)
        me_location = deepcopy(matrix)
        opponent_location = -deepcopy(matrix)      
        
        me_location[me_location!=1] = 0 #自分のマスを1,それ以外のマスを0で埋める
        opponent_location[opponent_location!=1] = 0 #敵のマスを1,それ以外のマスを0で埋める 
        
        epsilon = 0.5 * (1 / (episode+1)) #徐々に最適行動のみをとるε-greedy法
        if np.random.random() < epsilon:
            hand = random.choice(possible_hand)
        else:
            x=np.array([me_location,opponent_location])[np.newaxis,:,:,:]
            q = self.q_function.model.predict(x).reshape(-1) #shape(64,)で返る(盤目64個分のq値)
            #できる限りパスしないための実装
            max_q = -np.inf
            if 0 in possible_hand: 
                possible_hand.remove(0)
            if possible_hand:
                for i in possible_hand:
                    if max_q < q[i-1]:
                        max_q = q[i-1]
                        hand = i
            else:
                hand = 0
        
        if hand == 0: #行動がパス(0)ならmemoryデータベースを更新しない
            return '{}_{}'.format(self.color, hand)

        if self.s_last is not None: #状態sと行動handを記憶
            self.memory.append(self.s_last, self.a_last, s, 0, 0)
        self.s_last = s
        self.a_last = hand
        action = '{}_{}'.format(self.color, hand)
        
        return action 
    
    def finalize(self, state, winner):
        state = state.split(',')[0]
        state = [i for i in state if i in ['b','w','-']]
        s = [(0 if i == '-' else (1 if i == self.color else -1)) for i in state]
        
        if winner == self.color:
            r = self.reward_win
        elif winner == 'd':
            r = self.reward_draw
        else:
            r = self.reward_lose

        self.memory.append(self.s_last, self.a_last, s, r, 1)

        self.s_last = None
        self.a_last = None

        self.record.append(r) 

