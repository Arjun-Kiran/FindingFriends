"""One change to a game at a time.

Every handler loads the game from the database, changes it and saves it back.
The server runs handlers on threads, so without a lock two of them can load the
same state, and whichever saves second silently throws the first one's change
away. These tests widen that window on purpose — a sleep between the load and
the save — so the race happens every run rather than once in a blue moon.
"""
import threading
import time

import pytest

from Database import database


@pytest.fixture
def http(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True
    with Main.app.test_client() as client:
        yield client


def _slow_loads(monkeypatch):
    """Hold every load for a moment before handing the state back."""
    import Main

    real = Main.get_redis_cache

    def slow(game_code):
        game_state = real(game_code)
        time.sleep(0.05)
        return game_state

    monkeypatch.setattr(Main, 'get_redis_cache', slow)
    return real


def _at_once(*jobs):
    threads = [threading.Thread(target=job) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


@pytest.mark.unit
def test_two_players_joining_at_once_are_both_seated(http, monkeypatch):
    import Main

    code = http.get("/create").get_json()['game_code']
    load = _slow_loads(monkeypatch)

    def join(name):
        def job():
            with Main.app.test_client() as client:
                client.get(f"/join/{code}?nick_name={name}")
        return job

    _at_once(join('Ann'), join('Bob'))

    assert sorted(p.name for p in load(code).player_order) == ['Ann', 'Bob']


@pytest.mark.unit
def test_the_same_game_always_gets_the_same_lock():
    import Main

    assert Main.game_lock('below-adopt-havoc') is Main.game_lock('BELOW-adopt-havoc')


@pytest.mark.unit
def test_different_games_do_not_wait_on_each_other():
    import Main

    assert Main.game_lock('below-adopt-havoc') is not Main.game_lock('other-game-code')
