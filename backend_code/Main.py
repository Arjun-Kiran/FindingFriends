from uuid import uuid4
from typing import Dict, Tuple

import hashlib
import eventlet
eventlet.monkey_patch()
from flask import Flask, jsonify, Response
from flask import request, redirect
from flask_socketio import SocketIO, emit, join_room


from Game.Components.GameState import GameState
from Game.Session.Words import generate_word_session
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state, PlayerView
from Game.Components.Player import Player
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players, generate_player, set_player_as_alpha, set_player_as_leading_player, set_game_state_trump, find_player, set_winning_player_of_round, next_person_turn, reset_round, is_round_over
from Game.Systems.DeckSystem import number_of_decks, number_of_card_to_deal
from Game.Systems.TeamSystem import number_of_cards_to_call_friends, check_friend_card_played
from Game.Systems.DecisionSystem import single_card_lead_decision, legal_cards_to_play, is_trump
from Game.Systems.PointSystem import calculate_rounds_points, point_card_pile
from Game.Components.GameState import DeclareCallingCard
from Game.Modules.CardConstants import Suit, Rank
from Game.Components.Card import Card
from Database.database import build_game_state_table, upsert_game_state_in_db, get_game_state_in_db, get_game_update_time_in_db

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


build_game_state_table()

MOCK_REDIS_CACHE: Dict[str, GameState] = dict()
SITE_URL = "http://127.0.0.1:5000"

# Maps socket session ID -> (game_code, player_uuid)
SID_TO_PLAYER: Dict[str, Tuple[str, str]] = dict()

@app.route("/")
def hello_world():
    return '''Hello, backend is alive.'''


@app.route("/create")
def create_game():
    gs = GameState()
    gs.session = str(uuid4())
    gs.game_code = generate_word_session(3).lower()
    gs.game_event_state = GameEventState.WAITING_FOR_PLAYERS_TO_JOIN
    update_redis_cache(game_state=gs)
    join_link = f'/join/{gs.game_code}'
    return jsonify({
        'game_code': gs.game_code.lower(),
        'join_link': join_link
    })


@app.route("/join")
def join_game():
    if len(request.args) == 0:
        return f'''
        <form action="/join">
            <label for="gamecode">Game Code:</label>
            <input type="text" id="gamecode" name="gamecode"><br><br>
            <input type="submit" value="Submit">
        </form>
        '''
    game_code: str = request.args.get('gamecode','')
    return redirect(f'/join/{game_code.lower()}', code=302)


@app.route("/join/<game_code>")
def join_game_with_session_id(game_code):
    gs = get_redis_cache(game_code.lower())

    if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
        return f'<p>Game is not accepting new players</p>'

    if gs:
        if len(request.args) == 0:
            return f'''<p>No Arguments</p>'''
        nick_name = request.args.get('nick_name')
        new_player = generate_player(name=nick_name)
        new_gs = add_player(gs, new_player)
        update_redis_cache(new_gs)
        game_link = f'/game/{game_code.lower()}/player/{new_player.uuid}'
        return jsonify({
            'game_link': game_link,
            'new_player_uuid': new_player.uuid,
            'nick_name': nick_name
        })
    return f'<p>Game Does Not Exists</p>'


@app.route("/game/<game_code>/player/<player_uuid>")
def game_session(game_code: str, player_uuid: str):
    game_state = get_redis_cache(game_code)
    player_view = player_view_state(game_state, player_uuid)
    return player_view.json()


@socketio.on('message')
def handle_message(message):
    print("Received message: " + message)


@socketio.on('connect')
def handle_connect():
    print("Client connected to WebSocket")


@socketio.on('disconnect')
def handle_disconnect():
    from flask import request as flask_request
    sid = flask_request.sid
    if sid in SID_TO_PLAYER:
        del SID_TO_PLAYER[sid]
    print(f"Client disconnected: {sid}")


@socketio.on('join')
def handle_join(data):
    """Client asks to join a game's room so it receives updates for that game.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        from flask import request as flask_request
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        if not game_code:
            emit('error', {'message': 'missing game_code'})
            return

        join_room(game_code)

        # Track which socket belongs to which player
        if player_uuid:
            SID_TO_PLAYER[flask_request.sid] = (game_code, player_uuid)

        # Send the current game state to the joining client (emit only to them)
        try:
            gs = get_redis_cache(game_code)
            if player_uuid and player_uuid in gs.player_dict:
                pv = player_view_state(gs, player_uuid)
                emit('game_stats', pv.dict())
            else:
                emit('game_stats', {'game_event_state': gs.game_event_state.value, 'number_of_players': len(gs.player_order)})
        except Exception as e:
            print(f"Could not fetch game state for {game_code}: {e}")
    except Exception as e:
        print(f"Error in handle_join: {e}")


@socketio.on('start_game')
def handle_start_game(data):
    """Host starts the game. Builds deck, deals cards, picks alpha.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')

        gs = get_redis_cache(game_code)

        # Validate: game must be in waiting state
        if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            emit('error', {'message': 'Game is not in a state to start'})
            return

        # Validate: only the host can start
        if str(gs.hosting_player.uuid) != player_uuid:
            emit('error', {'message': 'Only the host can start the game'})
            return

        # Validate: need minimum players
        if not gs.can_start_game:
            emit('error', {'message': 'Not enough players to start (need 5+)'})
            return

        # Build and deal
        num_players = len(gs.player_order)
        deck_count = number_of_decks(num_players)
        cards_per_person = number_of_card_to_deal(num_players)

        add_deck_to_game(gs, deck_count)
        deal_to_players(gs, cards_per_person)
        # Remaining cards in cards_in_deck are the kitty

        # Host is the first alpha player
        set_player_as_alpha(gs, player_uuid)
        set_player_as_leading_player(gs, player_uuid)

        gs.game_event_state = GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP
        gs.can_start_game = False

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_start_game: {e}")
        emit('error', {'message': str(e)})


@socketio.on('declare_trump')
def handle_declare_trump(data):
    """Alpha player declares trump suit by selecting a card from their hand.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>', 'suit': '<SUIT>', 'rank': '<RANK>' }
    The rank must match the alpha player's current level.
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        suit_str = data.get('suit', '')
        rank_str = data.get('rank', '')

        gs = get_redis_cache(game_code)

        # Validate: must be in trump declaration phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP:
            emit('error', {'message': 'Not in trump declaration phase'})
            return

        # Validate: only the alpha can declare
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can declare trump'})
            return

        # Parse suit and rank
        try:
            declared_suit = Suit(suit_str)
            declared_rank = Rank(rank_str)
        except ValueError:
            emit('error', {'message': f'Invalid suit or rank: {suit_str}, {rank_str}'})
            return

        # Validate: the rank must match the alpha player's level
        alpha_level = gs.player_levels.get(player_uuid, Rank.TWO.value)
        if declared_rank.value != alpha_level:
            emit('error', {'message': f'You must declare a card matching your level ({alpha_level})'})
            return

        # Validate: the alpha must hold a card with this suit+rank
        hand = gs.players_and_hand.get(player_uuid, [])
        has_card = any(c.suit == declared_suit and c.rank == declared_rank for c in hand)
        if not has_card:
            emit('error', {'message': 'You do not hold a card with that suit and rank'})
            return

        # Set trump
        set_game_state_trump(gs, declared_suit, declared_rank)
        gs.game_event_state = GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_declare_trump: {e}")
        emit('error', {'message': str(e)})


@socketio.on('call_friends')
def handle_call_friends(data):
    """Alpha player calls friend cards to determine secret partners.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'calling_cards': [{'suit': '<SUIT>', 'rank': '<RANK>', 'order': <int>}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        calling_cards_data = data.get('calling_cards', [])

        gs = get_redis_cache(game_code)

        # Validate: must be in friend calling phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE:
            emit('error', {'message': 'Not in friend calling phase'})
            return

        # Validate: only the alpha can call friends
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can call friends'})
            return

        # Validate: correct number of calling cards
        num_players = len(gs.player_order)
        expected_count = number_of_cards_to_call_friends(num_players)
        if len(calling_cards_data) != expected_count:
            emit('error', {'message': f'Must call exactly {expected_count} friend cards, got {len(calling_cards_data)}'})
            return

        # Parse and validate each calling card
        calling_cards = []
        for cc in calling_cards_data:
            try:
                suit = Suit(cc['suit'])
                rank = Rank(cc['rank'])
                order = int(cc['order'])
            except (ValueError, KeyError) as e:
                emit('error', {'message': f'Invalid calling card: {cc}'})
                return

            # Called cards must not be trumps
            if suit == gs.declare_trump.suit or rank == gs.declare_trump.rank:
                emit('error', {'message': f'Called cards must not be trumps: {rank.value} of {suit.value}'})
                return

            if order < 1:
                emit('error', {'message': 'Order must be at least 1'})
                return

            calling_cards.append(DeclareCallingCard(suit=suit, rank=rank, order=order))

        gs.friend_calling_cards = calling_cards
        gs.game_event_state = GameEventState.WAITING_ON_ALPHA_KITTY_SORT

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_call_friends: {e}")
        emit('error', {'message': str(e)})


@socketio.on('kitty_exchange')
def handle_kitty_exchange(data):
    """Alpha player exchanges kitty cards — takes the kitty into hand, discards same number.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'discarded_cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        discarded_data = data.get('discarded_cards', [])

        gs = get_redis_cache(game_code)

        # Validate: must be in kitty sort phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_KITTY_SORT:
            emit('error', {'message': 'Not in kitty exchange phase'})
            return

        # Validate: only the alpha
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can exchange kitty'})
            return

        kitty_size = len(gs.cards_in_deck)
        if len(discarded_data) != kitty_size:
            emit('error', {'message': f'Must discard exactly {kitty_size} cards, got {len(discarded_data)}'})
            return

        # Parse discarded cards
        discarded_cards = []
        for dc in discarded_data:
            try:
                discarded_cards.append(Card(suit=Suit(dc['suit']), rank=Rank(dc['rank'])))
            except (ValueError, KeyError):
                emit('error', {'message': f'Invalid card: {dc}'})
                return

        # Add kitty to alpha's hand
        hand = gs.players_and_hand.get(player_uuid, [])
        hand.extend(gs.cards_in_deck)
        gs.cards_in_deck = []

        # Remove discarded cards from hand
        remaining_hand = list(hand)
        for dc in discarded_cards:
            found = False
            for i, hc in enumerate(remaining_hand):
                if hc.suit == dc.suit and hc.rank == dc.rank:
                    remaining_hand.pop(i)
                    found = True
                    break
            if not found:
                emit('error', {'message': f'Card not in hand: {dc.rank.value} of {dc.suit.value}'})
                return

        gs.players_and_hand[player_uuid] = remaining_hand
        gs.card_out_of_play = discarded_cards

        # Set alpha as leading player for first trick and start the round
        set_player_as_leading_player(gs, player_uuid)
        gs.game_event_state = GameEventState.ROUND_STARTED

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_kitty_exchange: {e}")
        emit('error', {'message': str(e)})


@socketio.on('play_cards')
def handle_play_cards(data):
    """Player plays a card during a trick.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'card': {'suit': '<SUIT>', 'rank': '<RANK>'}
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        card_data = data.get('card', {})

        gs = get_redis_cache(game_code)

        # Validate: must be in round started phase
        if gs.game_event_state != GameEventState.ROUND_STARTED:
            emit('error', {'message': 'Not in a playing phase'})
            return

        # Validate: it must be this player's turn
        current_uuid = gs.player_order[gs.current_player.index].uuid
        if current_uuid != player_uuid:
            emit('error', {'message': 'It is not your turn'})
            return

        # Parse the played card
        try:
            played_card = Card(suit=Suit(card_data['suit']), rank=Rank(card_data['rank']))
        except (ValueError, KeyError):
            emit('error', {'message': f'Invalid card: {card_data}'})
            return

        # Validate: card must be in player's hand
        hand = gs.players_and_hand.get(player_uuid, [])
        card_index = None
        for i, hc in enumerate(hand):
            if hc.suit == played_card.suit and hc.rank == played_card.rank:
                card_index = i
                break
        if card_index is None:
            emit('error', {'message': 'Card not in your hand'})
            return

        # Validate: card must be legal to play (follow suit)
        _, player_obj = find_player(gs, player_uuid)
        legal_cards = legal_cards_to_play(gs, player_obj)
        is_legal = any(lc.suit == played_card.suit and lc.rank == played_card.rank for lc in legal_cards)
        if not is_legal:
            emit('error', {'message': 'You must follow suit if you can'})
            return

        # Remove card from hand
        hand.pop(card_index)

        # Add card to active pile
        gs.cards_in_active_pile.append(played_card)
        gs.current_hand_played = [played_card]

        trump = {'suit': gs.declare_trump.suit, 'rank': gs.declare_trump.rank}

        # If this is the leading play, set it
        is_leading = len(gs.leading_hand_of_subround) == 0
        if is_leading:
            gs.leading_hand_of_subround = [played_card]
            set_winning_player_of_round(gs, player_uuid)

        # Check friend card
        check_friend_card_played(gs, player_uuid, [played_card])

        # Determine if this play beats the current winner
        if not is_leading:
            leading_card = gs.leading_hand_of_subround[0]
            winning_uuid = gs.winning_player_of_round.player_uuid
            winning_hand = None
            # Find the winning player's card in the active pile
            # The winning card is at the position corresponding to the winning player
            # We track by comparing: find which card in active pile belongs to current winner
            # Simpler: iterate active pile cards and find the best one
            # Actually, use single_card_lead_decision to compare current winner's card vs new card
            # We need to know which card the current winner played
            # Find it by position: cards are added in player order starting from leading player
            winning_player_idx_in_trick = None
            leading_idx = gs.leading_player.index
            num_players = len(gs.player_order)
            winning_player_trick_idx = None
            for trick_pos in range(len(gs.cards_in_active_pile)):
                player_idx_in_order = (leading_idx + trick_pos) % num_players
                if gs.player_order[player_idx_in_order].uuid == winning_uuid:
                    winning_player_trick_idx = trick_pos
                    break

            if winning_player_trick_idx is not None:
                winning_card = gs.cards_in_active_pile[winning_player_trick_idx]
                if single_card_lead_decision(trump, leading_card, winning_card, played_card):
                    set_winning_player_of_round(gs, player_uuid)

        # Advance to next player's turn
        continue_trick, next_player = next_person_turn(gs)

        if continue_trick:
            # Trick continues, next player's turn
            gs.current_player.player_uuid = next_player.uuid
            update_redis_cache(gs)
        else:
            # Trick is complete
            trick_winner_uuid = gs.winning_player_of_round.player_uuid
            gs.last_trick_winner = trick_winner_uuid

            # Award points for this trick
            calculate_rounds_points(gs)

            # Check if round is over (all hands empty)
            if is_round_over(gs):
                # End of round scoring
                handle_end_of_round(gs)
            else:
                # Reset for next trick
                reset_round(gs)

            update_redis_cache(gs)

    except Exception as e:
        print(f"Error in handle_play_cards: {e}")
        import traceback
        traceback.print_exc()
        emit('error', {'message': str(e)})


def handle_end_of_round(gs: GameState):
    """Calculate final round scores and transition to ROUND_ENDED."""
    alpha_uuid = gs.current_alpha_player.player_uuid
    friends = gs.current_friends_of_alpha

    # Determine teams
    alpha_team = {alpha_uuid} | set(friends)
    defender_team = set()
    for p in gs.player_order:
        if p.uuid not in alpha_team:
            defender_team.add(p.uuid)

    # Sum defender points
    defender_points = sum(gs.players_round_score.get(uuid, 0) for uuid in defender_team)

    # If defenders won the last trick, kitty points count double
    if gs.last_trick_winner in defender_team and gs.card_out_of_play:
        kitty_points = point_card_pile(gs.card_out_of_play)
        defender_points += kitty_points * 2
        # Add the bonus to the last trick winner's score for display
        gs.players_round_score[gs.last_trick_winner] = gs.players_round_score.get(gs.last_trick_winner, 0) + kitty_points * 2

    # Move remaining active pile to discard
    gs.card_in_discard_pile.extend(gs.cards_in_active_pile)
    gs.cards_in_active_pile = []
    gs.leading_hand_of_subround = []
    gs.current_hand_played = []

    gs.game_event_state = GameEventState.ROUND_ENDED


def broadcast_player_views(game_state: GameState):
    """Send each connected player their own filtered PlayerView."""
    game_code = game_state.game_code.lower()
    for sid, (gc, player_uuid) in SID_TO_PLAYER.items():
        if gc == game_code and player_uuid in game_state.player_dict:
            try:
                pv = player_view_state(game_state, player_uuid)
                socketio.emit('game_stats', pv.dict(), room=sid)
            except Exception as e:
                print(f"Failed to emit player view to {player_uuid}: {e}")


def update_redis_cache(game_state: GameState):
    game_code = game_state.game_code.lower()
    upsert_game_state_in_db(game_code, game_state.dict(), True)
    try:
        broadcast_player_views(game_state)
    except Exception as e:
        print(f"Failed to emit game_stats for {game_code}: {e}")


def get_redis_cache(game_code) -> GameState:
    output = get_game_state_in_db(game_code.lower())
    return GameState(**output)


if __name__ == "__main__":
    socketio.run(app)
