#!/usr/bin/env python3

import requests
import websocket
import json


WEBURL = "http://127.0.0.1:5000"


class ExitException(Exception):
	pass


def prompt(message) -> str:
	output = input(message)
	if output.strip() == '0':
		raise ExitException("Exiting the game!")
	return output

def print_menu(menu_str):
	print(menu_str)
	print("Type 0 to simply exit the system")
	print('--------------------------------')


def create_game():
	r = requests.get(f'{WEBURL}/create')
	if r.status_code == 200:
		game_code = r.json()['game_code']
		join_game(game_code)


def join_game_request(game_code)-> int:
	f'''{game_code}'''
	return 200



def join_game_menu():
	join_game_str = f'''
	Please type in the Game Code to join an existing game.
	'''
	print_menu(join_game_str)
	while True:
		game_code = prompt("What is the game code? ")
		output = join_game_request(game_code)
		if output == 200:
			break
	
	join_game(game_code)


def join_game(game_code = None):
	join_game_str = f'''
	Game Code: {game_code}
	Choose Your Name
	'''
	print_menu(join_game_str)
	name = prompt("What is your name? ")


def get_update_game_session():
	pass


def play_cards():
	pass


def pick_trump_suit_as_alpha():
	pass


def pick_calling_cards_as_alpha():
	pass


def kitty_exchange_as_alpha():
	pass


def main_menu():
	choice_exit_game = 0
	choice_create_game = 1
	choice_join_game = 2
	main_menu_str = f'''
	Welcome to Finding Friends Python Client

	[{choice_create_game}] Create a new game
	[{choice_join_game}] Join an existing game
	
	'''
	input_str = "Select: "
	print_menu(main_menu_str)
	while True:
		choice = prompt(input_str)
		if int(choice) == choice_create_game:
			create_game()
		elif int(choice) == choice_join_game:
			join_game_menu()
		else:
			print(f'You have to select the following choices: [{choice_create_game, choice_join_game, choice_exit_game}]')

def run():
	try:
		main_menu()
	except ExitException:
		print("Exiting System")


if __name__ == '__main__':
	run()

