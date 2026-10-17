"""Module for determining whether a position is a wolfrandom position.

Thanks to Wolfram_EP on lichess for providing all non-terminal 6-ply wolfrandom
positions which were converted to FENs via _loadwrfens.py"""

import pathlib
import os
import mmap
from array import array # store the offsets
#import subprocess

# This assumes the 7z has been unzipped
WRFILE = "wolfrandom.fen"
WROFFSETS = "wroffsets.bin"

if not pathlib.Path(WRFILE).is_file():
    raise FileNotFoundError("wolfrandom.fen was not found, please unzip the 7z provided")

# sus due to newline presence issues
#LINES = int(subprocess.run(["wc", "-l", WRFILE], capture_output=True, text=True).stdout.strip().split(" ")[0])

def save_offsets(): # precomputed
    offsets = array("Q")
    with open(WRFILE, "rb") as f:
        while 1:
            pos = f.tell()
            line = f.readline()

            if not line:break

            offsets.append(pos)

    with open(WROFFSETS, "wb") as f:
        offsets.tofile(f)
    return offsets

def load_offsets():
    offsets = array("Q")
    try:
        with open(WROFFSETS, "rb") as f:
            offsets.fromfile(f, os.path.getsize(WROFFSETS) // offsets.itemsize)
    except FileNotFoundError:
        offsets = save_offsets()
    return offsets

def _getline(file, lineno):
    file.seek(lineno)
    return file.readline()

OFFSETS = load_offsets()

# The kind of ordering we need, or smth
#def _cmp(fen1, fen2):
#   for charin in range(min(len(fen1), len(fen2))):
#        if fen1[charin] < fen2[charin]:
#            return 1
#        elif fen1[charin] > fen2[charin]:
#            return -1
#    return (len(fen1) > len(fen2))-(len(fen1) < len(fen2))

def exists(fen):
    fen=fen.encode() if isinstance(fen, str) else fen

    with open(WRFILE, "rb") as f:
        lower, upper = 0, len(OFFSETS) - 1

        while lower <= upper:
            middle = (lower+upper)//2
            line = _getline(f, middle).strip(b"\r\n") # just in case

            if line == fen:
                return True
            elif line < fen:
                upper = middle +1
            else:
                lower = middle -1
    return False
