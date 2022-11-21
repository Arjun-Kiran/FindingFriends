

def number_of_cards_to_call_friends(number_of_players: int) -> int:
    if number_of_players < 5:
        raise Exception("Not enough players. Need 5 or more")

    if number_of_players > 12:
        raise Exception("Too many players")
    
    call_to_friend_dict = {
        '5': 1,
        '6': 2,
        '7': 2,
        '8': 3,
        '9': 3,
        '10': 4,
        '11': 4,
        '12': 5
    }

    return call_to_friend_dict[str(number_of_players)]
