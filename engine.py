"""Internal bridge between the Belzedarian Bot and the underlying
Atomic-Stockfish engine.

Can be used on any atomic engine that talks UCI and supports the
expected commands.
"""

# todo: should we do something about engine processes running
# while an error is raised, terminating the program, but leaving
# the engine as a zombie subprocess?

import subprocess
import time
import os
import selectors
import logging

class BlockingTimeoutExpiredError(Exception):
    """Raised when a target is not received within a timeout"""
    pass

class Engine:
    
    def __init__(self, path):
        """Initialize a basic Engine.

        Very barebones, can be subclassed for any specific
        UCI engine's commands. 
        """
        self.engine = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # The below line causes issues with selectors
            #text=True,
            bufsize=0,
        )

        self.selector = selectors.DefaultSelector()
        self.selector.register(
            self.engine.stdout,
            selectors.EVENT_READ,
        )

        self.buffer = b""
        # Make sure we're ready to go
        self.start_uci()
        self.is_ready()

    def send(self, command):
        """Send a command to the engine"""
        self.engine.stdin.write(command.encode() + b"\n")
        self.engine.stdin.flush()

    def start_uci(self):
        """Start UCI. Should be autorun at __init__, if
        something messes up (as it probably will) this
        function is provided for your convenience.
        """
        self.send("uci") 
        self.block("uciok", 5)

    def is_ready(self):
        """Confirm the engine is ready."""
        self.send("isready")
        self.block("readyok", 5)

    def block(self, target, timeout=None,):# doreturn=False):
        """Pause execution for at most timeout seconds until
        target is found in the engine's stdout. If the timeout
        expires, the engine terminates with an error.
        """
        deadline = time.monotonic() + timeout if timeout is not None else None

        while True:
            
            while b"\n" in self.buffer: # consume all we've already received
                line, self.buffer = self.buffer.split(b"\n", 1)
                line = line.decode("utf-8").strip()
                if target in line:
                    return line# if doreturn else None

            # do timeout checks
            remaining = deadline - time.monotonic() if deadline is not None else None

            if remaining is not None and remaining <= 0:
                raise BlockingTimeoutExpiredError(f"expected {target} within {timeout:.2f} seconds")

            events = self.selector.select(remaining)

            if not events:
                raise BlockingTimeoutExpiredError(f"expected {target} within {timeout:.2f} seconds")

            # read new lines
            nextchunk = os.read(self.engine.stdout.fileno(), 4096)

            # At no point should the stream just die. If it does, we're in trouble, big trouble.
            if not nextchunk:
                raise EOFError(f"Engine stdout unexpectedly ended while expecting {target}, returncode={self.engine.poll()}")

            self.buffer += nextchunk
        
    def quit(self):
        self.send("quit") # note: always close the engine before deleting the object to prevent
                          # BrokenPipeError and other weird memory holes
        self.selector.close()
        self.engine.wait()
        # del self # not worth dealing with all the gc know-it-alls
                          
    def _setoption(self, option, value):
        """Internal function to set options. It is recommended to subclass the Engine
        and use this function within your engine to prevent arbitrary option errors.
        """
        self.send("setoption name " + option + " value " + str(value))
        
class AtomicStockfish(Engine):
    
    def __init__(self, path):
        """Initialize *specifically* belzedar's own Atomic-Stockfish engine."""
        super().__init__(path)

    def set_threads(self, value):
        """Sets the number of threads this engine can use."""
        self._setoption("Threads", value)

    def set_hash(self, value):
        """Sets the size of the hash table (in megabytes) this engine can use."""
        self._setoption("Hash", value)

    # more options can be added here

    def set_position(self, fen, newgame=False):
        """Setup position."""
        if newgame:
            self.send("ucinewgame") # for safety
            self.is_ready()
        self.send("position fen "+fen)

    def go(self, **kwargs):
        """Search for best move.
        Arguments:
        wtime, btime, winc, binc, depth, nodes, movetime
        
        Leave empty to go infinite. Must manually send("stop"),
        however.
        """
        if not kwargs:
            command = "go infinite"
        else:
            command = "go " + " ".join(f"{key} {value}" for key, value in kwargs.items() if value is not None)

        self.send(command)
        return self.block("bestmove").split()[1]    

if __name__ == "__main__":
    # why?
    print("Wrong module")
