from Game.Views.CardView import Card, card_list_to_dict_list
from Game.Views.CardView import card_to_dict, Rank, Suit


def test_card_to_dict():
    card_1 = Card(Suit.BIG, Rank.JOKER)
    card_2 = Card(Suit.CLUB, Rank.ACE)
    card_3 = Card(Suit.DIAMOND, Rank.JACK)

    dict_card_1 = card_to_dict(card_1)
    dict_card_2 = card_to_dict(card_2)
    dict_card_3 = card_to_dict(card_3)

    assert dict_card_1['rank'] == 'JOKER'
    assert dict_card_1['suit'] == 'BIG'

    assert dict_card_2['rank'] == 'ACE'
    assert dict_card_2['suit'] == 'CLUB'

    assert dict_card_3['rank'] == 'JACK'
    assert dict_card_3['suit'] == 'DIAMOND'
    

def test_card_list_to_dict_list():
    card_1 = Card(Suit.BIG, Rank.JOKER)
    card_2 = Card(Suit.CLUB, Rank.ACE)
    card_3 = Card(Suit.DIAMOND, Rank.JACK)
    card_4 = Card(Suit.HEART, Rank.FOUR)
    card_5 = Card(Suit.SPADE, Rank.EIGHT)
    card_6 = Card(Suit.SMALL, Rank.JOKER)
    card_list = [card_1, card_2, card_3, card_4, card_5, card_6]
    card_list_dict = card_list_to_dict_list(card_list)

    assert card_list_dict[0]['rank'] == 'JOKER'
    assert card_list_dict[0]['suit'] == 'BIG'

    assert card_list_dict[1]['rank'] == 'ACE'
    assert card_list_dict[1]['suit'] == 'CLUB'

    assert card_list_dict[2]['rank'] == 'JACK'
    assert card_list_dict[2]['suit'] == 'DIAMOND'

    assert card_list_dict[3]['rank'] == '4'
    assert card_list_dict[3]['suit'] == 'HEART'

    assert card_list_dict[4]['rank'] == '8'
    assert card_list_dict[4]['suit'] == 'SPADE'

    assert card_list_dict[5]['rank'] == 'JOKER'
    assert card_list_dict[5]['suit'] == 'SMALL'
