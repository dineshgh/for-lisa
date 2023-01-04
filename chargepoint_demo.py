#!/usr/bin/env python
"""
ChargePoint demo Game of Life

The game is played on a rectangular grid of cells. A cell
can be live or dead. An initial pattern of live cells is
zapped on the board, and then the game proceeds time tick 
by time tick. Moves are made by rules, not by any players.
In that sense, the game is deterministic.

To support this game, we use
- GameOfLife class. It instantiates game board, runs the
ticks, and shows the board
- Grid class. Over ticks, the pattern changes and so does 
the grid size necessary to hold the pattern. We have 
implemented an infinite grid. (other choices in grid design 
such as endless, fixed, etc.) 
- GridCell and GridPoint classes, represent a cell in grid with 
live/dead state and a point to represent any grid cell.
- Pattern is a helper class, to translate a shorthand 
notation of a pattern of a rectangular grid into a set of 
live points. We got a bunch of test patterns from wikipedia.
"""

print("Hello, chargepoint!")
gPatternDict = { "block": "XX/XX", 
                "blink": "XXX", 
                "bounce": "XX/XX/..XX/..XX", 
                "glider": ".X/..X/XXX", 
                "spaceship": ".XXXX/X...X/....X/X..X",
                "expanding": "......X/....X.XX/....X.X/....X/..X/X.X"
                }

#
###########################################################
# GridCell and GridPoint
# atom level repr of a cell in a rectangular grid.
# Cell - describes a point in a grid. It can be alive or dead
# Point - encodes a point for a grid, at (row,col) location
###########################################################
#
class GridCell:
    def __init__(self, isAlive=False):
        self._state = isAlive
    @staticmethod
    def fromChar(ch):
        return GridCell(ch != '.' and ch != ' ')
    def isAlive(self):
        return not not self._state
    def set(self, isAlive=False):
        self._state = isAlive
    def toHTML(self):
        return "&nbsp;"
    def __str__(self):
        return 'X' if self.isAlive() else '.'
    def __repr__(self):
        return self.__str__()


class GridPoint:
    def __init__(self, row, col, isAlive=False):
        self.row = row
        self.col = col
        self.state = GridCell(isAlive)
    def isAlive(self):
        return self.state.isAlive()
    def moveBy(self, howmuch):
        self.row += howmuch[0]
        self.col += howmuch[1]
    def __str__(self):
        return f"({self.row},{self.col},{'T' if self.isAlive() else 'F'})"
    def __repr__(self):
        return self.__str__()

#
###########################################################
# Pattern
# takes a "/"-joined set of row descriptions of a rect grid
# where each row is described as a seq of dead (space,dot)
# or alive (any other char) cells.
# In essence it translates the pattern into a set of Points
# that are alive
###########################################################
#
import itertools
class Pattern:
    def __init__(self, pattern=""):
        def _mkPoint(r,c,val):
            return GridPoint(r,c,GridCell.fromChar(val).isAlive())
        rows = pattern.strip("/").split("/")
        all_points = ((map( lambda val,col: _mkPoint(r,col,val), rows[r], range(len(rows[r])) )) for r in range(len(rows)))
        self.points = list(itertools.chain.from_iterable( all_points ))
        # print("Pattern points -- ", len(self.points), self.points)


    def getPoints(self):
        return self.points


    def getExtent(self):
        maxrow, maxcol = 0,0
        for p in self.points:
            maxrow = max(maxrow, p.row)
            maxcol = max(maxcol, p.col)
        return maxrow, maxcol


    def moveBy(self, howmuch=[0,0]):
        for p in self.points:
            p.moveBy(howmuch)
#
###########################################################
# Grid
# grid is a R x C grid of points on which Game is played.
# WIth each play (called tick), a new pattern of live/dead
# cells is computed and grid updated
#
# The "live area" of the grid can move over plays, and even
# touch and attempt to cross the boundary. Different grid
# designs can handle this even differently. In some, the
# cells could "wraparound" or simply stonewall. Ours is an
# INF grid - it expands as needed. To keep resources under
# control for long running games, it also trims any excess
# margins or empty rows/columns on edges.
#
# Grid takes an initial pattern, locates it at grid "center"
###########################################################
#
class Grid:
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    def __init__(self, gridType, extent, margins):
        if gridType != "inf":
            raise BaseException(f"bad grid type, only inf is allowed.")
        if any(map(lambda x: x < 1, margins)):
            raise BaseException(f"bad grid margins, minimum 1 on each side needed!")
        if extent[0] < (margins[0]+margins[2]) or extent[1] < (margins[1]+margins[3]):
            raise BaseException(f"bad grid extents, must be larger than margins!!")
        self.extent = extent
        self.margins = margins
        # an empty set of rows of cells
        self.rows = [ [GridCell()] * self.extent[1] for i in range(self.extent[0]) ]


    def seedPattern(self, initialPattern, initialLocation="center"):
        if initialLocation != "center":
            raise BaseException(f"bad pattern location!")
        p = Pattern(initialPattern)        
        pextent = p.getExtent()
        moveBy = list( (self.extent[x] - pextent[x]) // 2 for x in range(2) )
        p.moveBy(moveBy)
        self.applyPoints(p.getPoints(), trim_now=False)


    # produce a plane vanilla displayable grid
    def __str__(self):
        x = "\n".join( 
                    "".join(repr(self.rows[r][c])  for c in range(len(self.rows[r]))) 
                    for r in range(len(self.rows)) )
        y = ",".join((str(n) for n in self.extent))
        return f"{x}\nsize=({y})"


    # superimpose the state from given set of points to the grid
    # then, maintain the margins
    def applyPoints(self, points, trim_now=True):
        # update the grid
        for x in points:
            self.rows[x.row][x.col] = x.state
        self._maintainMargin(trim_now)


    # test and apply margin requirements by
    # - counting the current "dead" rows and columns at extremes
    def _maintainMargin(self, trim_now=True):
        def __testRowIsDead(r):
            return not list(filter(lambda c: self.isCellAlive(r,c), range(self.extent[1])))
        def __testColumnIsDead(c):
            return not list(filter(lambda r: self.isCellAlive(r,c), range(self.extent[0])))
        def __computeDeficits():
            # - what are the bounds of living cells?
            top, bottom = 0, self.extent[0] - 1 # index where first live row
            left, right = 0, self.extent[1] - 1 # index where first live column
            while (top < self.extent[0]) and __testRowIsDead(top):
                top += 1 # move towards south
            while (bottom < self.extent[0]) and (bottom > top) and __testRowIsDead(bottom):
                bottom -= 1 # move north
            while (left < self.extent[1]) and __testColumnIsDead(left):
                left += 1 # move east
            while (right < self.extent[1]) and (right > left) and __testColumnIsDead(right):
                right -= 1 # move west
            # print(f"margin test - starting bounds {top}, {right}, {bottom}, {left}")
            # - what's the deficiency/excess w.r.t. desired margins?
            # (staying with N S E W metaphors)
            deficit_N = self.margins[0] - top
            deficit_E = self.margins[1] - (self.extent[1] - right - 1)
            deficit_S = self.margins[2] - (self.extent[0] - bottom - 1)
            deficit_W = self.margins[3] - left
            # print(f" - calculated deficits N E S W {deficit_N} {deficit_E} {deficit_S} {deficit_W}")
            return deficit_N, deficit_E, deficit_S, deficit_W

        # helpers in add/trim action. deficit when -ve means drop row/column; when +ve means add row/column
        def __addARow(i): 
            self.rows.insert(i, [GridCell()] * self.extent[1])
        def __trimARow(i): 
            self.rows.pop(i) 
        def __addAColumn(i):
            for r in range(self.extent[0]):
                self.rows[r].insert(i, GridCell())
        def __trimAColumn(i):
            for r in range(self.extent[0]):
                self.rows[r].pop(i)

        # - what are the bounds of living cells? what's the gap vis a vis margin requirements
        deficit_N, deficit_E, deficit_S, deficit_W = __computeDeficits()
        # remedying the deficits...
        # -- working on Rows - north end
        for i in range(abs(deficit_N)):
            if deficit_N > 0:
                __addARow(0)
            elif trim_now:
                __trimARow(0)
        self.extent[0] = len(self.rows) # update live bounds
        # -- rows, south end
        for i in range(abs(deficit_S)):
            if deficit_S > 0:
                __addARow(len(self.rows))
            elif trim_now:
                self.rows.pop(len(self.rows)-1)
        self.extent[0] = len(self.rows) # update live bounds
        # -- working on Columns, west end first
        for i in range(abs(deficit_W)):
            if deficit_W > 0:
                __addAColumn(0)
            elif trim_now:
                __trimAColumn(0)
        self.extent[1] = len(self.rows[0]) # update live bounds
        # -- columns, east end
        for i in range(abs(deficit_E)):
            if deficit_E > 0:
                __addAColumn(len(self.rows[0]))
            elif trim_now:
                __trimAColumn(len(self.rows[0])-1)
        self.extent[1] = len(self.rows[0]) # update live bounds


    # tell if a cell is alive or dead
    def isCellAlive(self, r, c):
        return self.rows[r][c].isAlive()


    # return a row vector with count of alive neighbors for a specific row in the grid 
    def countNeighborsForRow(self, row):
        n = list(map( lambda col: self._countNeighborsCell(row,col), range(self.extent[1]) ))
        return n


    # return a count of alive neighbors for a speific cell in the grid
    def _countNeighborsCell(self, r0, c0):
        livings = list(filter (lambda s: self.getCell(s[0]+r0, s[1]+c0).isAlive(), Grid.directions))
        return len(livings)


    # return a cell from grid. if boundaries are crossed, return a dead cell
    def getCell(self, r, c):
        try:
            return self.rows[r][c]
        except:
            return GridCell() # a dead cell


    # return the row x col spread of the grid
    def getExtent(self):
        return self.extent
#
###########################################################
# GameOfLife
# sets up a game board, initializes it, and plays tick by tick
###########################################################
#
import os, time

class GameOfLife:
    def __init__(self, extent=[10,20], margins=[2,3,2,3], initialPattern="XX/XX"):
        # print(f"GOL extent={extent}, margins={margins}")
        self.g = Grid("inf", extent, margins)
        self.g.seedPattern(initialPattern, "center")
        self.tickCount = 0


    # todo - add more interesting rendering agents
    def run(self, tickIntervalMillis, maxTicks, redenrTo="html:filename"):
        for t in range(maxTicks):
            print(f"-------About to tick; already played {self.tickCount} ticks------------")
            self.tick()
            game.renderToConsole()
            time.sleep(tickIntervalMillis/1000.0)


    # one round of game play
    # - grid row by grid row, compute count of alive neighbors for each cell in the row
    # - compute deaths and births by applying game rules
    # - apply the transitions to the grid
    def tick(self):
        # since we have a margin of dead rows and columns all around, 
        # we don't have to worry about creating new rows /  columns here.
        rowcount, colcount = self.g.getExtent()
        transitions = []
        for rownum in range(rowcount):
            neighbors = self.g.countNeighborsForRow(rownum)
            row_census = self._determineTransitions(rownum, neighbors)
            if row_census:
                # print("at row#", rownum, "- row_census=", row_census)
                transitions += row_census
        # apply trim only every 5 ticks - so that we can see the moves on display
        self.g.applyPoints(transitions, self.tickCount and self.tickCount % 5 == 0) 
        self.tickCount += 1


    # compute deaths and births by applying game rules, given a grid rownum
    # alive neighbor count for each cell in that row 
    def _determineTransitions(self, rownum, neighbors):
        def __dieTest(ncount, colnum):
            return not (2 <= ncount <= 3) and self.g.isCellAlive(rownum, colnum)
        def __birthTest(ncount, colnum):
            return 3 == ncount and not self.g.isCellAlive(rownum, colnum)
        census = []
        for colnum in range(len(neighbors)):
            if __dieTest(neighbors[colnum], colnum):
                census.append(GridPoint(rownum, colnum, False))
            elif __birthTest(neighbors[colnum], colnum):
                census.append(GridPoint(rownum, colnum, True))
        return census


    # render game board on console - use curses?? nope
    def renderToConsole(self):
        print(f"Board after tick# {self.tickCount} >>>>>>>>>")
        print(self.g)

#################################################################

import pytest

#################################################################
import argparse
def getopts():
    parser = argparse.ArgumentParser(description="Run a pattern in game of life. \n" +
                "Several patterns are already coded: glider/blink/bounce/spaceship/expanding.")
    parser.add_argument("--pattern", default="glider", help="pattern or name to use")
    parser.add_argument("--num-ticks", type=int, default=60, help="how many ticks to play")
    parser.add_argument("--tick-interval", type=int, default=1000, help="tick interval in millis")
    parser.add_argument("--render-to", choices=["console", "html"], default="console", help="where to render grid. only console is supported for now")
    opts = parser.parse_args()
    return opts

if __name__ == "__main__":
    opts = getopts()
    print(f"Welcome to Game of Life: will run pattern {repr(opts.pattern)} " +
            " for {opts.num_ticks} ticks once every {opts.tick_interval} millis")
    game = GameOfLife(extent=[25,25], initialPattern=gPatternDict.get(opts.pattern, opts.pattern))
    print("==========INITIAL BOARD===========")
    game.renderToConsole()
    game.run(opts.tick_interval, opts.num_ticks, "consolde")
    print("Goodbye")