"""Fast route for the Belzedarian bot, and its core purpose.
Provides a function to query the API.

Not meant to be used directly, unless you decided to install
a complete bot's source code to make a simple GET request.
"""

import requests

# The URL where this all happens. May God have enough mercy on
# this bot to keep this link alive.
URL = "https://belzedar.duckdns.org/atomicdb/api/query"

def query_from_url(fen):
    """Queries the best move for fen from the URL, may raise errors
    (requiring manual handling)"""
    response = requests.get(URL,params={"fen": fen},timeout=5)
    # Including 404, so whoever uses this is forced to use a
    # try-except to fallback to atomic-sf
    response.raise_for_status()
    move = response.json()["best_move"]
    return move # well we survived
    

