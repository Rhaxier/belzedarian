"""Helper module for the Belzedarian bot, to update moves in Atomic."""

import chess
import chess.variant

STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class Board:
    def __init__(self, position=STARTPOS):
        self.board = chess.variant.AtomicBoard(position)

    def push_move(self, move):
        mv = chess.Move.from_uci(move)
        self.board.push(move=mv)

    @property
    def get_fen(self):
        return self.board.fen(en_passant="fen", promoted=False)

    @property
    def side(self):
        return "w" if self.board.turn==chess.WHITE else "b"
# old version
"""
import re
STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MOVE = re.compile("([a-h])([1-8])([a-h])([1-8])([qrbn])?")

class Board:
    def __init__(self, position=STARTPOS):
        # extract components
        components = position.split()
        # and set
        self.board = [sum([c.isdigit()and[" "]*int(c)or[c]for c in r],[])for r in components[0].split("/")]
                   # adapted from https://codegolf.stackexchange.com/a/292431/ (my answer)
        
        self.side = components[1]
        self.castling_rights = components[2]
        self.en_passants = components[3]
        self.halfmoves, self.fullmoves = map(int, [components[4], components[5]])

    def push_move(self, move):

        # Turns out castling is NOT e8g8, its more like e8h8 for some reason from
        # Lichess

        if self.board[startrank][startfile]in"Kk"and move in ("e1h1", "e1a1", "e8h8", "e8a8"):
            move = {"e1h1": "e1g1","e1a1": "e1c1","e8h8": "e8g8","e8a8": "e8c8",}[move]

        # extract components
        startfile, startrank, endfile, endrank, promotion = MOVE.fullmatch(move).group(1,2,3,4,5)
        # normalize
        startfile, endfile = map( "abcdefgh".index, [startfile, endfile])
        startrank, endrank = map(lambda v:8-int(v), [startrank, endrank])
        # get piece
        piece = self.board[startrank][startfile]
        # determine capture (intentionally misclassifies en passant)
        iscapture = self.board[endrank][endfile] != " "

        # Universally across all moves, the starting square shall have its
        # piece disappear.
        
        self.board[startrank][startfile] = " "

        # We'll set en passant target square here to empty, it will update later

        self.en_passants = "-"

        # If a capture, the ending square shall also be empty.

        if iscapture:
            
            # Indeed, in captures, the squares around the destination empty as
            # well, unless they are pawns
        
            for i in [-1, 0, 1]:
                for j in [-1, 0, 1]:
                    try: # remove non-pawn pieces, and pieces at the destination square
                        if (i==0==j)or self.board[endrank+i][endfile+j] not in "pP":
                            # handle rook capture (directly or indirectly) leading to castling right denial
                            if self.board[endrank+i][endfile+j]in "Rr":
                                match endfile+j:
                                    case 0:
                                        self.castling_rights=self.castling_rights.replace("Qq"["Rr".index(self.board[endrank+i][endfile+j])],"")
                                    case 7:
                                        self.castling_rights=self.castling_rights.replace("Kk"["Rr".index(self.board[endrank+i][endfile+j])],"")
                            self.board[endrank+i][endfile+j] = " "
                    except IndexError: # skip edge cases (literally)
                        continue
                    
        # Now handle en passant -> a pawn move to an adjacent file
        # (this must therefore be a capture) that was not caught by iscapture,
        
        elif piece in "pP" and abs(endfile-startfile)==1:
            for i in [-1, 0, 1]:
                for j in [-1, 0, 1]:
                    try: # remove non-pawn pieces, and the piece at the destination square and
                         # the en passanted square.
                        if (i==0==j)or(i==[-1,1]["pP".index(piece)])or self.board[endrank+i][endfile+j] not in "pP":
                            if self.board[endrank+i][endfile+j]in "Rr":
                                # handle rook capture (directly or indirectly) leading to castling right denial
                                match endfile+j:
                                    case 0:
                                        self.castling_rights=self.castling_rights.replace("Qq"["Rr".index(self.board[endrank+i][endfile+j])],"")
                                    case 7:
                                        self.castling_rights=self.castling_rights.replace("Kk"["Rr".index(self.board[endrank+i][endfile+j])],"")
                            self.board[endrank+i][endfile+j] = " "
                    except IndexError: # skip edge cases (literally)
                        continue
        else: # not a capture

            self.board[endrank][endfile] = piece

            # Whenever a king moves (not just castle) it will lose its castling rights on both
            # sides.

            if piece in "Kk":
                self.castling_rights=self.castling_rights.replace(piece,"").replace("Qq"["Kk".index(piece)],"")

                # The only special case UCI coordinate notation must deal with
                # is castling. When white's king castles kingside, it is recorded
                # as e1g1. We must update the king, the rook, and the castling right
                # of the king.
                # The 4 possible castles are e1g1, e1c1, e8g8, and e8c8. As we already
                # know the king has moved, we simply check the difference of the files
                # and move the rook if it is 2.

                # We don't check if we have castling rights, however, as we're guaranteed
                # the move is legal.

                if abs(endfile-startfile)==2:
                    # self.board[startrank] also works, but for clarity
                    self.board[endrank][{6:7, 2:0}[endfile]] = " "
                    self.board[endrank][{6:5, 2:3}[endfile]] = "Rr"["Kk".index(piece)]

            elif piece in "Rr":
                # Rooks can also affect castling rights. If a king has its castling rights,
                # but one of its rooks has moved, the king can no longer castle that side.

                # if we're on a corner, we must have moved from that corner, breaking
                # castling rights. of course that implies we shouldn't be doing this check
                # every time, but dammit, this is v1
                if startrank in (0, 7) and startfile in (0, 7):
                    match startfile:
                        case 0: # only remove queenside rights
                            self.castling_rights=self.castling_rights.replace("Qq"["Rr".index(piece)], "")
                        case 7:
                            self.castling_rights=self.castling_rights.replace("Kk"["Rr".index(piece)], "")

            elif piece in "Pp":
                # We have to set en passant target square if we moved two squares.
                if abs(endrank-startrank)==2: # can only happen once really
                    self.en_passants = "abcdefgh"[startfile]+{1:"6",6:"3"}[startrank]

                # ngl i kinda forgot abt this
                elif promotion is not None:
                    # override the destination square
                    self.board[endrank][endfile] = promotion.upper()if piece.isupper() else promotion
            
        # update other things

        self.side = "wb"[1-"wb".index(self.side)]
        self.halfmoves = 0 if iscapture or piece in "pP" else (self.halfmoves+1)
        if self.side == "w":
            self.fullmoves += 1

    @property
    def get_fen(self):
        fen =" ".join([re.sub(" +",lambda s:str(len(s.group())),"/".join(["".join(i)for i in self.board])),
              self.side,
              self.castling_rights if self.castling_rights else "-",
              self.en_passants,
              str(self.halfmoves),
              str(self.fullmoves)])
        print(
            "DEBUG:",
            repr(self.side),
            repr(self.castling_rights),
            repr(self.en_passants),
            self.halfmoves,
            self.fullmoves
        )
        return fen
"""