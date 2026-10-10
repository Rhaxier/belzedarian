"""Module for determining whether a position is a wolfrandom position.

Thanks to Wolfram_EP on lichess for providing all non-terminal 6-ply wolfrandom
positions which were converted to FENs via _loadwrfens.py"""

import pathlib
# This assumes the 7z has been unzipped
WRFILE = "wolfrandom.fen"

if not pathlib.Path(WRFILE).is_file():
    raise FileNotFoundError("wolfrandom.fen was not found, please unzip the 7z if it was provided")

