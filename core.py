"""Core logic of the Belzedarian bot.

In a nutshell: given a FEN, try to query the belzedar website
for its best move. If it 404s, run our local engine on it.
"""

ENGINE_EXEC = "./Atomic-Stockfish-linux-x86_64"

import sys
import query as _query, engine as _engine
import requests
import logging

logger = logging.getLogger(__name__)

class Core:
    def __init__(self):
        self.engine = _engine.AtomicStockfish(ENGINE_EXEC)

        # Repeatedly setting up the engine gets
        # expensive really quick. Better allocate
        # required resources once, then leave it
        # running forever, waiting for new games.
        self.configured = False

        # When an unevaluated position is reached on
        # belzedar.duckdns.org/atomicdb, none of its
        # leaf nodes will have been evaluated, even
        # if there turns out to be a mate there. So
        # once we 404 the website, there's no point
        # querying it anymore, just fallback to SF
        # until the next game.
        self.out_of_eval = False

    def get_move(self, fen, wtime=None, btime=None, winc=None, binc=None, movetime=3000, depth=37):
        if not self.out_of_eval:
            try:
                move = _query.query_from_url(fen)
                if move is not None:
                    logger.info(f"AtomicDB move: {move}")
                    return move
                self.out_of_eval = True # we've reached unexplored territory
            except (requests.exceptions.HTTPError) as err:
                if err.response.status_code != 404:
                    # probably not that serious,
                    # fallback to atomic-sf anyways
                    logger.error(f"Error: {err}")
                else:
                    self.out_of_eval = True
            except Exception as err:
                # again we've reached a fatal error with connecting to
                # atomicdb, but that shouldn't incapacitate us. fallback
                # to sf, but let us know what happened
                logger.error(f"Error: {err}")
                self.out_of_eval = True
        self.prepare_sf(4, 512, fen) # change per user
        logger.debug("Sent FEN:", fen)
        move = self.engine.go(
            wtime=wtime,
            btime=btime,
            winc=winc,
            binc=binc,
            movetime=movetime,
            depth=depth
        )
        logger.info("SF MOVE: %r" %move)
        return move
        
    def prepare_sf(self, threads, hash, fen):
        """Start up the engine, giving it the context
        of the current game.
        """
        if not self.configured:
            self.engine.set_threads(threads)
            self.engine.set_hash(hash)
            self.engine.is_ready() # see comment in new_game
            self.configured = True # until program terminates, engine stays up,
                                  # just idle
            logger.info("Atomic SF ready")
        self.engine.set_position(fen)

    def new_game(self):
        """Let the system know a new game is started.
        """
        self.engine.send("ucinewgame")
        self.engine.is_ready() # ucinewgame is kinda expensive, better make sure its actually
                               # on standby
        self.out_of_eval = False
        logger.info("Atomic SF reset")

            
            
