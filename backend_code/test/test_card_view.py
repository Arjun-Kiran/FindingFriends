from Game.Views.CardView import Card, card_list_to_dict_list
from Game.Views.CardView import card_to_dict, Rank, Suit


def test_card_to_dict():
    card_1 = Card(suit=Suit.BIG, rank=Rank.JOKER)
    card_2 = Card(suit=Suit.CLUB, rank=Rank.ACE)
    card_3 = Card(suit=Suit.DIAMOND, rank=Rank.JACK)

    dict_card_1 = card_to_dict(card_1)
    dict_card_2 = card_to_dict(card_2)
    dict_card_3 = card_to_dict(card_3)

    assert dict_card_1['rank'] == Rank.JOKER
    assert dict_card_1['suit'] == Suit.BIG

    assert dict_card_2['rank'] == Rank.ACE
    assert dict_card_2['suit'] == Suit.CLUB

    assert dict_card_3['rank'] == Rank.JACK
    assert dict_card_3['suit'] == Suit.DIAMOND
    

def test_card_list_to_dict_list():
    card_1 = Card(suit=Suit.BIG, rank=Rank.JOKER)
    card_2 = Card(suit=Suit.CLUB, rank=Rank.ACE)
    card_3 = Card(suit=Suit.DIAMOND, rank=Rank.JACK)
    card_4 = Card(suit=Suit.HEART, rank=Rank.FOUR)
    card_5 = Card(suit=Suit.SPADE, rank=Rank.EIGHT)
    card_6 = Card(suit=Suit.SMALL, rank=Rank.JOKER)
    card_list = [card_1, card_2, card_3, card_4, card_5, card_6]
    card_list_dict = card_list_to_dict_list(card_list)

    assert card_list_dict[0]['rank'] == Rank.JOKER
    assert card_list_dict[0]['suit'] == Suit.BIG

    assert card_list_dict[1]['rank'] == Rank.ACE
    assert card_list_dict[1]['suit'] == Suit.CLUB

    assert card_list_dict[2]['rank'] == Rank.JACK
    assert card_list_dict[2]['suit'] == Suit.DIAMOND

    assert card_list_dict[3]['rank'] == Rank.FOUR
    assert card_list_dict[3]['suit'] == Suit.HEART

    assert card_list_dict[4]['rank'] == Rank.EIGHT
    assert card_list_dict[4]['suit'] == Suit.SPADE

    assert card_list_dict[5]['rank'] == Rank.JOKER
    assert card_list_dict[5]['suit'] == Suit.SMALL
