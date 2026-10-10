"""Converts nonterm6.txt to wolfrandom.fen"""

import sys
import re
import chess
import chess.variant
from tqdm import tqdm
import subprocess

if __name__ == "__main__":
    LINES = int(subprocess.run(["wc", "-l", sys.argv[1]], capture_output=True, text=True).stdout.strip().split(" ")[0])
    try:
        output=open(sys.argv[2], "x")
    except FileExistsError:
        output=open(sys.argv[2], "w")
    try:
        with open(sys.argv[1]) as file:
            print("Started")
            for line in tqdm(file, total=LINES, desc="Reading line"):
                moves=sum([g.strip().split() for g in re.split("[0-9]\\.", line)if g],[])
                board = chess.variant.AtomicBoard()
                for i in moves:board.push_san(i)
                output.write(board.fen().replace(" w","")[:-2]+"\n")
                output.flush()

        print("Done!")
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        output.close()
