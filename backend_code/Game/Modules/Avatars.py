"""Animal emoji standing in for players around the table.

Players are told apart at a glance by their avatar — on the players bar, the
scoreboards and the round summary — so no two players in a game share one, and
everyone has one whether they picked it or not. A player with no avatar would
leave a hole in every list the UI draws.

The catalog is deliberately much longer than any table, so even the last player
to join still has a real choice rather than the one emoji nobody took.
"""

import random
from typing import Iterable, List

ANIMAL_AVATARS: List[str] = [
    '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯',
    '🦁', '🐮', '🐷', '🐸', '🐵', '🐔', '🐧', '🦆', '🦉', '🦇',
    '🐺', '🐗', '🐴', '🦄', '🐝', '🦋', '🐢', '🐙', '🦈', '🐬',
    '🐳', '🦭', '🐘', '🦒', '🦘', '🦔',
]

_AVATAR_SET = frozenset(ANIMAL_AVATARS)


def is_valid_avatar(avatar: str) -> bool:
    """Is this one of the avatars we offer? Guards against a hand-crafted
    socket payload putting arbitrary text where the UI expects one glyph."""
    return avatar in _AVATAR_SET


def available_avatars(taken: Iterable[str]) -> List[str]:
    """Catalog order, minus everything already spoken for."""
    taken_set = set(taken)
    return [avatar for avatar in ANIMAL_AVATARS if avatar not in taken_set]


def pick_avatar(taken: Iterable[str]) -> str:
    """An unused avatar for a player who did not choose one.

    Random rather than the next free one in the catalog: sequential assignment
    would hand every game the same first five animals.

    If somehow nothing is free, a duplicate beats leaving a player blank.
    """
    free = available_avatars(taken)
    return random.choice(free) if free else random.choice(ANIMAL_AVATARS)
