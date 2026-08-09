import json
import sqlite3
from sqlite3 import Error
from datetime import datetime

from logging_config import get_logger

log = get_logger(__name__)


def get_database():
    return "game_state.db"

def get_date_time():
    return datetime.now().strftime("%m/%d/%Y, %H:%M:%S")


def create_connetion(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        log.exception("Could not connect to database %s: %s", db_file, e)

    return conn


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        conn.commit()
    except Error as e:
        log.exception("Could not create table: %s", e)


def build_game_state_table():
    database_table_str = """
    CREATE TABLE IF NOT EXISTS game_state_table (
	game_code text PRIMARY KEY,
	game_state text NOT NULL,
	active integer NOT NULL,
    timestamp text NOT NULL
);
    """
    conn = create_connetion(db_file=get_database())
    if conn is not None:
        create_table(conn, database_table_str)
        # Migrate: add timestamp column if missing (old databases)
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(game_state_table)")
            columns = [row[1] for row in c.fetchall()]
            if 'timestamp' not in columns:
                c.execute("ALTER TABLE game_state_table ADD COLUMN timestamp text NOT NULL DEFAULT ''")
                conn.commit()
        except Error as e:
            log.error("Migration check failed: %s", e)
    return conn


def get_game_state_in_db(game_code: str):
    """Return the stored game state dict, or None when no active game matches."""
    sql_select = """SELECT game_state FROM game_state_table WHERE game_code=? and active=?"""
    values = (game_code, True)
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_select, values)
        row = c.fetchone()
        conn.commit()
    if row is None:
        return None
    return json.loads(row[0])


def upsert_game_state_in_db(game_code: str, game_state: dict, activate: bool):
    sql_upsert = """
    INSERT INTO game_state_table (game_code,game_state,active,timestamp)
              VALUES(?,?,?,?) ON CONFLICT(game_code) DO UPDATE
              SET game_state=?,
              active=?,
              timestamp=?;"""
    game_state_string = json.dumps(game_state)
    time_stamp = get_date_time()
    values = (game_code, game_state_string, activate, time_stamp, game_state_string, activate, time_stamp)
    output = False
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_upsert, values)
        conn.commit()
        output = True
    return output

