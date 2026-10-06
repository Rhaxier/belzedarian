"""A cache for AtomicDB."""

from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

class OpeningCache(OrderedDict):
    def __init__(self, path, maxsize, *args, **kwargs):
        """Init OpeningCache, an LRU cache for AtomicDB"""
        super().__init__(*args, **kwargs)
        self.path = path
        # Worst case scenario: the upper bound for the max characters per
        # line is 96 (+ \n). The cache should at most be 10 MB, allowing
        # for 104,166 unique positions to be stored. If atomicdb goes down,
        # these lines would be enough to carry practical opening theory,
        # because except for my fellow DB eval tickers, no one cares
        # for nodes that no one will ever reach
        self.maxsize = maxsize
        try:
            with open(path, "r") as file:
                self._frompath(file)
        except FileNotFoundError:
            pass # create later

    def _frompath(self, file): 
        """Load a cache into OpeningCache from a path.
        
        While technically an internal function, it can be
        used to load from an external file if the destination
        file is not the same as the loading file. 
        """
        for line in file:
            fen, move = line.strip().split("|")
            if fen and move:self[fen] = move

    def __getitem__(self, fen):
        """Return the AtomicDB move for this FEN, marking this move as
        most recently used"""
        value = super().__getitem__(fen)
        self.move_to_end(fen)
        return value

    def __setitem__(self, fen, move):
        """Add this move from AtomicDB, removing the least recently used
        move if cache is over size limit"""
        super().__setitem__(fen, move)
        self.move_to_end(fen) # if we assigned this, we used it, meaning it's
                              # extra-stable under LRU
        if len(self) > self.maxsize:
            self.popitem(False)

    def save_to_path(self):
        """Save to disk."""
        with open(self.path, "w") as file:
            for fen, move in self.items():
                file.write(f"{fen}|{move}\n")

