"""HR-13: the host may put next round's trump rank to a vote.

Entirely optional and per round. At round end the host proposes one rank for
the whole table; everyone else votes. The host's proposal counts as a yes, and
a strict majority of everyone seated passes it. A vote that has not passed
stays open until the host cancels it. Nobody's level changes: it only decides
which rank the next alpha has to declare.
"""
from typing import Optional, Tuple

from Game.Components.GameState import GameState
from Game.Modules.CardConstants import NONJOKERNUMBERS, Rank
from Game.Modules.EventEnum import Event
from Game.Systems.EventSystem import record_event

def _name(game_state: GameState, uuid: str) -> str:
    player = game_state.player_dict.get(uuid)
    return str(player.name) if player else 'A player'


def _rank_label(value: int) -> str:
    return Rank(value).name.title()


def voters(game_state: GameState) -> list:
    """Everyone seated but the host, who has already voted by proposing."""
    host = str(game_state.hosting_player.uuid) if game_state.hosting_player else ''
    return [str(p.uuid) for p in game_state.player_order if str(p.uuid) != host]


def tally(game_state: GameState) -> Tuple[int, int]:
    """(yes, of) — the host's proposal is a yes, and a seat that has since
    been left no longer counts either way."""
    seated = voters(game_state)
    yes = 1 + sum(1 for uuid in seated if game_state.rank_votes.get(uuid) is True)
    return yes, len(seated) + 1


def has_majority(game_state: GameState) -> bool:
    yes, total = tally(game_state)
    return yes * 2 > total


def clear_proposal(game_state: GameState):
    game_state.rank_proposal = None
    game_state.rank_votes = {}


def clear_vote(game_state: GameState):
    """Forget the vote and anything it passed."""
    clear_proposal(game_state)
    game_state.next_round_rank = None


def _settle(game_state: GameState):
    if game_state.rank_proposal is not None and has_majority(game_state):
        rank = game_state.rank_proposal
        game_state.next_round_rank = rank
        clear_proposal(game_state)
        record_event(game_state, Event.RANK_VOTE_PASSED,
                     f'The table voted for {_rank_label(rank)} as the next trump rank')


def propose(game_state: GameState, host_uuid: str, rank) -> Optional[str]:
    """Open a vote, replacing any earlier proposal or passed result. Returns
    what is wrong, or None."""
    if game_state.settings.free_trump_choice:
        return 'This table names any trump it likes, so there is no rank to vote on.'
    try:
        chosen = Rank[rank] if isinstance(rank, str) else Rank(rank)
    except (KeyError, ValueError):
        chosen = None
    if chosen not in NONJOKERNUMBERS:
        return f'Not a rank: {rank}'
    value = chosen.value
    clear_vote(game_state)
    game_state.rank_proposal = value
    record_event(game_state, Event.RANK_PROPOSED,
                 f'{_name(game_state, host_uuid)} proposed {_rank_label(value)} as the next trump rank',
                 host_uuid)
    _settle(game_state)
    return None


def cast_vote(game_state: GameState, voter_uuid: str, approve: bool) -> Optional[str]:
    if game_state.rank_proposal is None:
        return 'There is no rank vote open.'
    if voter_uuid not in voters(game_state):
        return 'The host\'s proposal already counts as their vote.'
    game_state.rank_votes[voter_uuid] = bool(approve)
    _settle(game_state)
    return None


def cancel(game_state: GameState, host_uuid: str) -> Optional[str]:
    if game_state.rank_proposal is None and game_state.next_round_rank is None:
        return 'There is no rank vote to cancel.'
    clear_vote(game_state)
    record_event(game_state, Event.RANK_VOTE_CANCELLED,
                 f'{_name(game_state, host_uuid)} cancelled the rank vote', host_uuid)
    return None


def open_vote_problem(game_state: GameState) -> Optional[str]:
    """Why the round cannot start yet: a vote is still open."""
    if game_state.rank_proposal is not None:
        return 'A rank vote is still open. Cancel it or wait for the vote to pass.'
    return None


def start_round(game_state: GameState):
    """The round is being dealt: a passed result is in force for this round
    only, and is spent."""
    game_state.round_rank_override = game_state.next_round_rank
    game_state.next_round_rank = None
