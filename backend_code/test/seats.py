"""Seats at a test table: a real join, a real token, and a socket per player.

The server takes every socket action as coming from the player that socket
joined as (see Main.validate_player), so a test driving five players needs five
sockets. `TableSockets` keeps the one-socket shape these tests were written in:
`emit` reads the payload's player_uuid and sends the message down that player's
own socket, and `get_received` gathers what every socket was sent. The uuid in
the payload is only a routing label for the test — the server ignores it.
"""
import time
from typing import Dict, List

# uuid -> token for every seat or watcher taken through here. uuids are random, so one
# registry serves every test without them treading on each other.
TOKENS: Dict[str, str] = {}


def token_for(player_uuid: str) -> str:
    return TOKENS.get(player_uuid, '')


def join_over_http(http, code: str, name: str) -> str:
    """Take a seat the way the browser does, and remember its token."""
    body = http.get(f"/join/{code}?nick_name={name}").get_json()
    TOKENS[body['new_player_uuid']] = body['player_token']
    return body['new_player_uuid']


def watch_over_http(http, code: str, name: str) -> str:
    """Start watching the way the browser does, and remember the token."""
    body = http.get(f"/watch/{code}?nick_name={name}").get_json()
    TOKENS[body['watcher_uuid']] = body['player_token']
    return body['watcher_uuid']


class Clock:
    """Stands in for Main.now, so HR-8's countdowns can be moved on by hand.

    Starts a little ahead of the real clock, so anything the server stamps with
    the real time — a player's join — comes before anything stamped with this."""

    def __init__(self):
        self.t = time.time() + 1000

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float):
        self.t += seconds


def view(http, code: str, player_uuid: str) -> dict:
    """One player's view over HTTP, asked for with that player's token."""
    return http.get(f"/game/{code}/player",
                    headers={'X-Player-Token': token_for(player_uuid)}).get_json()


class TableSockets:
    """Stands in for one socket client, backed by one real socket per player."""

    def __init__(self):
        import Main

        self._main = Main
        self._sockets: Dict[str, object] = {}
        # For payloads naming nobody this table seated: a socket that never
        # joined anything, which is exactly what a stranger's is.
        self._stranger = Main.socketio.test_client(Main.app)

    def seat(self, http, code: str, name: str) -> str:
        """Join over HTTP and connect that player's socket straight away.

        Straight away matters: a socket first joining mid-game is a player
        coming back, and the table would be told they reconnected."""
        player_uuid = join_over_http(http, code, name)
        self.socket_of(player_uuid, code)
        return player_uuid

    def watch(self, http, code: str, name: str) -> str:
        """Start watching over HTTP and connect the watcher's socket."""
        watcher_uuid = watch_over_http(http, code, name)
        self.socket_of(watcher_uuid, code)
        return watcher_uuid

    def reconnect(self, player_uuid: str, code: str):
        """A fresh socket for someone, joined with the token they have always had."""
        client = self._main.socketio.test_client(self._main.app)
        client.emit('join', {'game_code': code, 'player_token': token_for(player_uuid)})
        self._sockets[player_uuid] = client
        return client

    def adopt(self, seat_uuid: str, watcher_uuid: str):
        """After a watcher takes over a seat, their socket and token speak for it."""
        self._sockets[seat_uuid] = self._sockets.pop(watcher_uuid)
        TOKENS[seat_uuid] = TOKENS[watcher_uuid]

    def socket_of(self, player_uuid: str, code: str = ''):
        """This player's socket, connected and joined on first use."""
        if player_uuid not in TOKENS:
            return self._stranger
        if player_uuid not in self._sockets:
            client = self._main.socketio.test_client(self._main.app)
            client.emit('join', {'game_code': code, 'player_token': token_for(player_uuid)})
            self._sockets[player_uuid] = client
        return self._sockets[player_uuid]

    def emit(self, event: str, data: dict):
        player_uuid = data.get('player_uuid', '')
        client = self.socket_of(player_uuid, data.get('game_code', ''))
        if event == 'join' and player_uuid in TOKENS:
            data = {**data, 'player_token': token_for(player_uuid)}
        client.emit(event, data)

    def get_received(self) -> List[dict]:
        # A socket a test has disconnected has nothing more to say, and asking
        # it raises.
        return [message for client in self._clients() if client.is_connected()
                for message in client.get_received()]

    def is_connected(self) -> bool:
        return any(client.is_connected() for client in self._clients())

    def disconnect(self):
        for client in self._clients():
            if client.is_connected():
                client.disconnect()

    def _clients(self):
        return [self._stranger, *self._sockets.values()]
