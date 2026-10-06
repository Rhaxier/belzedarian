"""The Belzedarian Bot's code.

Not much to see here. Run as the top-level user to activate
the bot on Lichess and be able to play it.
"""

import json
import requests
import time
import logging

import core as _core
import fen_updater as _fen

API = "https://lichess.org/api"

def _extract_belzedar_secrets(file):
    """Internal function"""
    secrets = json.loads((_tmp:=open(file)).read())
    # recov_phrase = secrets["proton_recovery_phrase"] # unused
    token = secrets["lichess_token"]
    _tmp.close()
    return token

class Communicator:
    def __init__(self, token):
        """Initialise a Lichess Communicator"""
        self.session = requests.Session()
        self.session.headers["Authorization"]="Bearer "+ token

        response = self.session.get(f"{API}/account")
        response.raise_for_status()

        self.account = response.json()
        self.id = self.account["id"]
        self.logger = logging.getLogger(__name__)


    def make_move(self, game_id, move):
        url = f"{API}/bot/game/{game_id}/move/{move}"

        for attempt in range(3):
            try:
                response = self.session.post(url, timeout=10)

                if response.status_code == 429:
                    self.logger.info("Rate limited")
                    time.sleep(60)
                    continue

                response.raise_for_status()
                return

            except requests.exceptions.ConnectionError as err:
                if attempt == 2:
                    raise

                self.logger.error(f"Connection error sending {move}; retrying...")
                time.sleep(1)

    def end_game(self, game_id):
        url = f"{API}/bot/game/{game_id}/"
        try:
            response = self.session.post(url+"abort", timeout=10)
            # if 429, i guess just fallback to getting timed out
            response.raise_for_status()
            return
        except requests.exceptions.HTTPError as err:
            try:
                response = self.session.post(url+"resign", timeout=10)
                # if 429, i guess just fallback to getting timed out
                response.raise_for_status()
                return
            except requests.exceptions.HTTPError as err:
                # get timeouted then
                self.logger.warning("Could not abort or resign. Timing out...")

    def handle_challenges(self, event):
        """Handle an incoming Lichess challenge."""
        challenge = event["challenge"]
        challenge_id = challenge["id"]


        if challenge["variant"]["key"] != "atomic":
            response = self.session.post(f"{API}/challenge/{challenge_id}/decline")
            response.raise_for_status()
        else:
            try:
                response = self.session.post(f"{API}/challenge/{challenge_id}/accept")
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                return


        # NOTE to self: do not try to return anything here; challenges will
        # trigger a gameStart if we accept.

    def wait_for_game(self):
        """Wait until a game starts or a challenge is offered"""
        response = self.session.get(f"{API}/stream/event", stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            event = json.loads(line)

            if event["type"] == "challenge":
                self.handle_challenges(event)

            elif event["type"] == "gameStart":
                return event["game"]["id"]

    def send_chat(self, game_id, text, room):
        """Send a message in a room."""
        if room != "both":
            response = self.session.post(f"{API}/bot/game/{game_id}/chat",data={"room":room,"text":text},timeout=10)
            response.raise_for_status()
            time.sleep(0.5) # pause for effect
        else:
            self.send_chat(game_id, text, "player")
            self.send_chat(game_id, text, "spectator")
        

    def play_game(self, game_id, core):
        """Play a game, indicated by game_id"""
        response = self.session.get(
            f"{API}/bot/game/stream/{game_id}",
            stream=True
        )
        response.raise_for_status()

        
        board = None
        side = None
        move_count = 0
        for line in response.iter_lines():
            if not line:
                continue

            event = json.loads(line)

            if event["type"] == "gameFull":
                board = _fen.Board()
                side = "w" if self.id == event["white"]["id"] else "b"

                moves = event["state"]["moves"].split()
                # Since transitioning to python-chess, moves aren't so serious
                # an issue anymore
                for move in moves:
                    #print("BEFORE:", board.get_fen)
                    board.push_move(move)
                    #print("AFTER", move, board.get_fen)

                move_count = len(moves)

                if side == board.side:
                    move = core.get_move(board.get_fen, )#event["wtime"], event["btime"], event["winc"], event["binc"])
                    self.make_move(game_id, move)
                
            elif event["type"] == "gameState":
                moves = event["moves"].split()

                for move in moves[move_count:]:
                    #print("BEFORE:", board.get_fen)
                    board.push_move(move)
                    #print("AFTER", move, board.get_fen)

                move_count = len(moves)

                if event["status"] != "started":
                    return 

                if board.side != side:
                    continue

                move = core.get_move(board.get_fen, event["wtime"], event["btime"], event["winc"], event["binc"])
                self.make_move(game_id, move)

if __name__ == "__main__":

    # todo: switch to argv, maybe using argparse or something
    clear = input("Clear the previous logs (y/n)? ")
    while clear.lower()[0] not in "yn":clear = input("Clear the previous logs? (y/n)")

    if clear.lower()[0] == "y":
        with open("belzedarian.log", "w") as f:
            # mission accomplished
            pass

    filelog = logging.FileHandler("belzedarian.log")
    console = logging.StreamHandler()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(module)s @ %(funcName)s @ %(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[filelog, console],
        level=logging.INFO
    )

    TOKEN = _extract_belzedar_secrets("secrets.json")
    
    communicator = Communicator(TOKEN)
    core = _core.Core()

    while True:
        communicator.logger.info("Waiting...")
        try:
            game_id = communicator.wait_for_game()
        except KeyboardInterrupt:
            communicator.logger.info("Terminating...")
            exit()
        communicator.logger.info("Playing...")
        communicator.send_chat(game_id, "Belzedarian v1.0.0", "both")
        #communicator.send_chat(game_id, "Running using belzedar.duckdns.org(slash)atomicdb", "both")
        core.new_game()
        try:
            communicator.play_game(game_id, core)
        except KeyboardInterrupt:
            # resign 
            communicator.logger.info("Ending game...")
            communicator.end_game(game_id)
            #exit() # just resign, if we must end Ctrl+C again
        except Exception as err:
            # Even if something goes wrong, does that really mean
            # we gotta stop everything? Maybe it's a network issue,
            # in which case the loop will go around and we end up
            # playing the same game. If its an unexpected ending
            # from other side, we'll terminate, but wait for a new
            # game.
            communicator.logger.info(f"Game unexpectedly over with error {err}")
        else:
            communicator.logger.info("Game over. GG!")
