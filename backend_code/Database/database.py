import os
import json
import sqlite3
from sqlite3 import Error

def get_database():
    return "game_state.db"


def create_connetion(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    
    return conn


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        conn.commit()
    except Error as e:
        print(e)


def build_game_state_table():
    database_table_str = """
    CREATE TABLE IF NOT EXISTS game_state_table (
	game_code text PRIMARY KEY,
	game_state text NOT NULL,
	active integer NOT NULL
);
    """
    conn = create_connetion(db_file=get_database())
    if conn is not None:
        create_table(conn, database_table_str)
    return conn


def insert_game_state_in_db(game_code : str, game_state: dict):
    sql_insert = """INSERT INTO game_state_table (game_code,game_state,active)
              VALUES(?,?,?);"""
    values = (game_code, json.dumps(game_state), True)
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_insert, values)
        conn.commit()


def update_game_state_in_db(game_code: str, game_state: dict, activate: bool):
    sql_update = """UPDATE game_state_table
              SET game_state = ?,
              active = ? 
              WHERE game_code = ?"""
    values = (json.dumps(game_state), activate, game_code)
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_update, values)
        conn.commit()


def get_game_state_in_db(game_code: str):
    sql_select = """SELECT game_state FROM game_state_table WHERE game_code=? and active=?"""
    values = (game_code, True)
    output = {}
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_select, values)
        output = c.fetchone()
        conn.commit()
        output = json.loads(output[0])
    return output


def upsert_game_state_in_db(game_code: str, game_state: dict, activate: bool):
    sql_upsert = """
    INSERT INTO game_state_table (game_code,game_state,active)
              VALUES(?,?,?) ON CONFLICT(game_code) DO UPDATE
              SET game_state=?,
              active=?;"""
    print(game_state)
    game_state_string = json.dumps(game_state)
    values = (game_code, game_state_string, activate, game_state_string, activate)
    output = False
    with create_connetion(db_file=get_database()) as conn:
        c = conn.cursor()
        c.execute(sql_upsert, values)
        conn.commit()
        output = True
    return output

