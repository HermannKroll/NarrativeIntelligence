from enum import Enum, auto

class JoinMode(Enum):
    INNER=auto()
    LEFT=auto()
    RIGHT=auto()
    OUTER=auto()

def join(query_left, query_right, on_left, on_right, mode:JoinMode):
    """
    takes two queries and returns an iterator that yields the joined table. queries have to be sorted by join columns.
    :param query_left: left query sorted by on_left.
    :param query_right: right query sorted by on_right.
    :param on_left: list of columns to join on left query ordered according to sorting order
    :param on_right: list of columns to join on right query ordered according to sorting order. on_left and on_right
        have to contain semantically identical columns
    :param mode: Join Mode, either INNER, LEFT, RIGHT or OUTER. Missing values will be filled with None.
    :return: iterator for joined table
    """

def inner_join(query_left)