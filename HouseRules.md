# Finding Friends — House Rules

**These rules override [ZhaoPengyou_Rules.md](ZhaoPengyou_Rules.md).**

`ZhaoPengyou_Rules.md` is the traditional game as described by John McLeod et al.
It is kept as background and as the reference for everything this document does
*not* mention. Where the two disagree, **this document wins** and is what the
code implements.

Precedence, highest first:

1. **HouseRules.md** (this file) — deliberate departures from the traditional game
2. **ZhaoPengyou_Rules.md** — the traditional game, background only

Each house rule carries an `HR-n` tag so it can be cited from code comments,
tests, and issues.

---

## Table of Contents

1. [HR-1 — Table sizes, decks and the deal](#hr-1--table-sizes-decks-and-the-deal)
2. [HR-2 — Two jokers per deck, variable kitty](#hr-2--two-jokers-per-deck-variable-kitty)
3. [HR-3 — Card points in play](#hr-3--card-points-in-play)
4. [HR-4 — Scoring thresholds at 5 and 6 decks](#hr-4--scoring-thresholds-at-5-and-6-decks)
5. [HR-5 — Tractors must be answered with tractors](#hr-5--tractors-must-be-answered-with-tractors)
6. [HR-6 — The attackers' points decide the round](#hr-6--the-attackers-points-decide-the-round)
7. [HR-7 — The order of the alpha's opening steps](#hr-7--the-order-of-the-alphas-opening-steps)
8. [HR-8 — Watching, and taking a seat mid-game](#hr-8--watching-and-taking-a-seat-mid-game)
9. [HR-9 — Two lobby settings start on](#hr-9--two-lobby-settings-start-on)
10. [HR-10 — The winner clears the trick](#hr-10--the-winner-clears-the-trick)
11. [HR-11 — The next alpha comes from the winning side](#hr-11--the-next-alpha-comes-from-the-winning-side)
11. [Unchanged from the traditional rules](#unchanged-from-the-traditional-rules)
12. [Change log](#change-log)

---

## HR-1 — Table sizes, decks and the deal

**Overrides:** *Players and Cards* → "Card Requirements by Player Count" in
`ZhaoPengyou_Rules.md`.

**Why:** the traditional pack counts (2 packs for 5–7, 3 for 8–11, 4 for 12)
give short hands — 14 cards each at 7 and 11 players. More decks means longer
hands, more sets and tractors per hand, and a longer, swingier round. This is a
deliberate feel change, not a correction.

Every value below is derived from player count and nothing else.

| Players | Decks | Total cards | Cards dealt each | Kitty (remainder) | Jokers in play | Friend cards called | Max alpha team |
|--------:|------:|------------:|-----------------:|------------------:|---------------:|--------------------:|---------------:|
| 5  | 3 | 162 | 30 | 12 | 6  | 1 | 2 |
| 6  | 3 | 162 | 26 | 6  | 6  | 2 | 3 |
| 7  | 4 | 216 | 29 | 13 | 8  | 2 | 3 |
| 8  | 4 | 216 | 26 | 8  | 8  | 3 | 4 |
| 9  | 5 | 270 | 29 | 9  | 10 | 3 | 4 |
| 10 | 5 | 270 | 26 | 10 | 10 | 4 | 5 |
| 11 | 6 | 324 | 29 | 5  | 12 | 4 | 5 |
| 12 | 6 | 324 | 26 | 12 | 12 | 5 | 6 |

The deck ladder: **5–6 → 3 decks, 7–8 → 4, 9–10 → 5, 11–12 → 6.**

`Total cards` is `decks × 54`. `Kitty` is the remainder,
`decks × 54 − players × cards_each` — see [HR-2](#hr-2--two-jokers-per-deck-variable-kitty).

**Unchanged:** fewer than 5 players cannot start, more than 12 cannot join.
**Unchanged:** friend cards called and max alpha team size are exactly as in the
traditional rules — only the deck and deal columns move.

**Implemented by:** `number_of_decks` and `number_of_card_to_deal` in
[backend_code/Game/Systems/DeckSystem.py](backend_code/Game/Systems/DeckSystem.py).

---

## HR-2 — Two jokers per deck, variable kitty

**Overrides:** *Players and Cards* → "Sufficient red and black jokers are
included so that all cards can be distributed equally, with a kitty of 6 (or 8)
cards left over", and the Red/Black Joker rows of the traditional table.

The traditional game varies the joker count per table size to force a 6-card
kitty. This game always uses a **complete 54-card deck — one small joker and one
big joker per deck** — and accepts whatever kitty falls out.

- Jokers in play is always `2 × decks`, so 6 to 12 (see [HR-1](#hr-1--table-sizes-decks-and-the-deal)).
- The kitty is **not** fixed at 6. Under HR-1 it ranges from **5 to 13**.
- Every part of the system that needs a kitty size must read it from the actual
  remainder, never assume a constant.

Kitty size is public information, and a fixed joker count is simpler to build
and to explain, which is why the variance is acceptable.

**Implemented by:** `JOKERSUITS` in
[backend_code/Game/Modules/CardConstants.py](backend_code/Game/Modules/CardConstants.py)
(consumed by `build_a_deck`). There is no separate joker-count setting; the size
of that list *is* the rule.

---

## HR-3 — Card points in play

**Overrides:** "The total card points in play is 200 (2 packs), 300 (3 packs),
or 400 (4 packs)."

Point values per card are **unchanged** — each King 10, each Ten 10, each Five 5,
everything else 0. That is 100 points per deck.

Because HR-1 raises the deck count, total points in play is now:

| Decks | 3 | 4 | 5 | 6 |
|---|---|---|---|---|
| Points in play | 300 | 400 | 500 | 600 |
| Player counts | 5–6 | 7–8 | 9–10 | 11–12 |

---

## HR-4 — Scoring thresholds at 5 and 6 decks

**Overrides:** *Scoring* → "Full Scoring Table", which only covers 2, 3, and 4
packs and therefore cannot be applied as written.

The bands in [HR-6](#hr-6--the-attackers-points-decide-the-round) are fifths of
the points in play, so they extend to any deck count without reinterpretation.
With `U` = one fifth = **20 × decks**, the tables for the two deck counts the
traditional rules do not cover are:

**5 decks (500 points in play) — 9–10 players.** `U` = 100, neutral = 200:

| Attackers' pts | Result |
|---|---|
| 0 | Alpha +3 |
| 5–95 | Alpha +2 |
| 100–195 | Alpha +1 |
| 200 | nobody moves |
| 205–300 | Attackers +1 |
| 305–400 | Attackers +2 |
| 405+ | Attackers +3 |

**6 decks (600 points in play) — 11–12 players.** `U` = 120, neutral = 240:

| Attackers' pts | Result |
|---|---|
| 0 | Alpha +3 |
| 5–115 | Alpha +2 |
| 120–235 | Alpha +1 |
| 240 | nobody moves |
| 245–360 | Attackers +1 |
| 365–480 | Attackers +2 |
| 485+ | Attackers +3 |

Card points only ever arrive in multiples of 5, so a band edge never falls
between two reachable totals.

**Changed 2026-09-20.** These tables used to be built by scaling the 2-deck
thresholds by `decks / 2`, which put every attacker band one fifth too high and
made "neither" a wide band rather than a single value. They are now the same
fifths rule as every other deck count. The undersized-alpha-team multiplier
that this rule used to preserve is gone — see HR-6.

## HR-5 — Tractors must be answered with tractors

**Overrides:** *Leading a Sequence of Sets* → "Following rules" in
`ZhaoPengyou_Rules.md`, specifically:

> Players are not required to follow with a sequence — any sets of the right
> size will do.

**Why:** answering a led tractor with two unrelated pairs while holding a
tractor is the cheapest way to dodge a trick in the traditional rules, and it
makes leading a tractor much weaker than it looks. Requiring the run to be kept
together is the *Forced sub-patterns* variation the traditional rules list but
do not enable; this game enables it. This is a deliberate feel change — leading
a tractor becomes a real squeeze.

**The rule:** when a sequence of sets is led, a follower must keep together as
much of a run as their holding in the led suit allows.

Stated precisely, in terms of **links**. A link is one neighbouring pair of
ranks among the sets a player plays: 5-5 beside 4-4 is one link, 8-8 beside 5-5
is none, and 9-9-8-8-7-7 is two. A follower must play **as many links as their
led-suit holding permits**.

> **Examples (Hearts trump, Twos the trump rank). Lead: ♣10-♣10-♣9-♣9.**
>
> | Holding in clubs | Owed | Why |
> |---|---|---|
> | 8-8, 5-5, 4-4 | 5-5 4-4 | One link is available; only 5-4 provides it |
> | K-K, 8-8, 6-6 | any two pairs | No two of those ranks are neighbours — nothing to keep |
> | K-K, 8-8 | both | Only one play exists; the rule asks nothing extra |
> | one pair only | that pair, plus filler | Sets owed fall short of the lead, so the rest is free |

**Unchanged:** everything about *how many* cards and sets are owed. A follower
still plays as many cards of the led suit as they hold, and as many sets of the
led size as they hold — HR-5 only decides **which** of those sets, when the
player has a choice. A player short of the led suit is as free as they ever
were, and a mixed "group of top cards" lead is untouched, since it has no one
set size to run.

**Adjacency** works exactly as it does for leading a sequence: same suit, same
set size, and the trump rank is stepped over (with Fives trump, Six and Four are
neighbours). The trump rank and jokers cannot sit in a run, so a pair of either
is a pair a player owes but never a link they could have kept.

**Implemented by:** `most_links_available` and `links_played` in
[backend_code/Game/Systems/DecisionSystem.py](backend_code/Game/Systems/DecisionSystem.py),
enforced in `validate_multi_card_play`, explained to the player by
`explain_illegal_follow`, and reflected in the in-hand highlighting by
`ranks_in_best_runs`.

---

## HR-6 — The attackers' points decide the round

**Overrides:** *Scoring* → "Winning Thresholds (per pack)", "Bonus Promotions"
and the "Full Scoring Table" of `ZhaoPengyou_Rules.md`, which are stated per
pack and do not cover every deck this game deals.

**Why:** a round is a contest for the points on the table, and the two sides'
totals always add up to the points in play — so naming one names the other.
Scoring on the attackers' total alone says the same thing in half the words,
and lets the size of the win set the size of the step: a rout should be worth
more than a scrape. The bands are fifths of the points in play, so they mean
the same thing at every table size.

**The rule:** at the end of a round, **the attackers' captured points decide
who is promoted and by how much.** The alpha team's total is not consulted.

Let `p` be the attackers' points, `U` = one fifth of the points in play
(**20 × decks**) and `N` = the neutral point (**two fifths, 40 × decks**):

| Attackers' points | Result |
|---|---|
| `p = 0` | **Alpha team +3** — a shutout, and only a shutout |
| `0 < p < U` | Alpha team +2 |
| `U ≤ p < N` | Alpha team +1 |
| `p = N` | **Nobody moves** — one exact value, not a band |
| `N < p ≤ N + U` | Attackers +1 |
| `N + U < p ≤ N + 2U` | Attackers +2 |
| `p > N + 2U` | Attackers +3 |

- **A level is gained for going past a fifth, never for landing on it.** The
  alpha bands close at the bottom — exactly `U` is +1, not +2. The attacker
  bands close at the top — exactly `N + U` is +1, not +2.
- **Nobody moving is a single total**, not a range. One card point either side
  of it and somebody is promoted.
- **Three levels is the most any round is worth**, to either side. There is no
  undersized-alpha-team multiplier: a short-handed alpha team is promoted the
  same as a full one.
- The attackers' total includes the kitty, counted double, when an attacker
  takes the last trick. That can carry them past the raw card total, which is
  why the top band is open-ended. The alpha team never collects the kitty.

> **Examples (3 decks, 300 points in play; `U` = 60, `N` = 120).**
>
> | Attackers' pts | Result |
> |---:|---|
> | 0 | Alpha team +3 |
> | 55 | Alpha team +2 |
> | 60 | Alpha team +1 |
> | 120 | Nobody moves |
> | 125 | Attackers +1 |
> | 180 | Attackers +1 |
> | 185 | Attackers +2 |
> | 245 | Attackers +3 |

**Unchanged:** how card points are won, the kitty counting double for attackers
who take the last trick, levels belonging to each player individually, and the
game ending when a player climbs **past** Ace.

**Configurable:** the lobby house rule *Bigger wins climb more levels*
(`scaled_level_promotion`) is **on by default**, and is this rule. Turned off,
a round is decided by comparing the two totals instead — more points wins, by
exactly one level, and an exact tie moves nobody. That flat rule was HR-6
itself between 2026-09-13 and 2026-09-20, and stays available for a table that
wants every round to count the same.

**Implemented by:** `score_round` and `promotion_for_round` in
[backend_code/Game/Systems/PointSystem.py](backend_code/Game/Systems/PointSystem.py),
called from `handle_end_of_round` in [backend_code/Main.py](backend_code/Main.py),
with the setting on `GameSettings` in
[backend_code/Game/Components/GameState.py](backend_code/Game/Components/GameState.py).

---

## HR-7 — The order of the alpha's opening steps

**Overrides:** the fixed order of *The Kitty* and *Calling Partners* in
`ZhaoPengyou_Rules.md`, which has trump made, then the kitty taken, then
partners called.

**The rule:** before the first trick the alpha declares trump, takes the kitty
and discards the same number face-down, and calls their friend cards. The host
picks the order in the lobby (*Order of the alpha's opening steps*,
`alpha_declaration_order`):

| Option | Order |
|---|---|
| 1 | Trump Suit → Call Friends → Kitty |
| 2 — **default** | Trump Suit → Kitty → Call Friends |
| 3 | Kitty → Trump Suit → Call Friends |

The default is the traditional order. Under option 3 the alpha declares trump
from the hand they kept, kitty included. Whatever the order, the round starts
once all three are done, with the alpha leading.

**Implemented by:** `ALPHA_PHASE_ORDERS` and `advance_alpha_phase` in
[backend_code/Main.py](backend_code/Main.py), with the setting on `GameSettings` in
[backend_code/Game/Components/GameState.py](backend_code/Game/Components/GameState.py).

---

## HR-8 — Watching, and taking a seat mid-game


**Overrides:** nothing in `ZhaoPengyou_Rules.md`, which assumes the same people
sit at the table from the first deal to the last. It fills that gap for an
online table, where people drop, leave, and turn up late.

**Why:** a game of Finding Friends runs for many rounds. Without this, one
player losing their connection stalls everyone, a player who leaves keeps a seat
nobody can use, and a friend who arrives late can only wait for the next game.

### Watching

- Anyone with the game code may **watch**, at any point — in the lobby or mid-game.
- Someone who joins a game that has already started **becomes a watcher
  automatically**. There is no seat to give them yet; from there they can ask
  the host for one.
- A watcher sees what every player at the table sees, **except any hand**. The
  kitty stays hidden until the round ends, as it does for players.
- *Hide the running totals* applies to watchers too. A watcher must never know
  more than the table, or they could tell a player.

### When a seat changes hands

- A player who presses **Leave** gives up their seat **immediately**.
- A player who **loses connection** has **60 seconds** to come back. A countdown
  is shown beside their name.
- From the moment a player drops or leaves, watchers may **volunteer** for the
  seat. Each volunteer appears to the host as soon as they ask.
- **The host's approval is final, and it takes effect at once.** The approved
  watcher takes the seat immediately; the rest of the countdown is not waited
  out. A player who reconnects after that has become a watcher, and can ask for
  a seat again later.
- If the player reconnects **before** the host has approved anyone, they carry
  on, and any volunteers go back to watching.
- If several watchers volunteer, the host picks one. Only one approval can ever
  land on a seat.
- A player still gone after **5 minutes** loses the seat for good. If they come
  back after that, they can only watch.

### Taking over a seat

- The new player takes over **everything the seat holds**: the hand, the level,
  the points, the place at the table, the avatar, and any role in the round —
  alpha, or a friend who has not yet revealed themselves.
- The table is told who took over whose seat.

### Joining as an extra player

- A watcher may ask to join as an extra player at any time. **The host approves
  or declines.**
- An approved player is seated **when the next round starts**, never partway
  through a round. They get a **random place at the table**.
- **The host sets their starting level.**
- The table may not grow past 12. Decks, deal and kitty follow the new player
  count as usual ([HR-1](#hr-1--table-sizes-decks-and-the-deal)).
- The next alpha ([HR-11](#hr-11--the-next-alpha-comes-from-the-winning-side))
  is decided before anyone is seated or removed, so joining never changes who
  is alpha next.

### Seats nobody took

- An open seat nobody took is removed **when the next round starts**. A seat is
  never removed partway through a round, because its hand and its place in the
  turn order are part of that round.

### A round held up by an empty seat

"During a round" means from the deal to the last trick, including the alpha's
opening steps.

- If a player **presses Leave** during a round, the host may straight away
  either approve a volunteer or **end the round as a draw**.
- If a player **loses connection** during a round and **60 seconds** pass with
  no volunteer approved, the host is asked to choose: approve a volunteer, if
  anyone has asked, or **end the round as a draw**. Watchers can still volunteer
  while the host is being asked, and whichever the host does first settles it.
- If the player comes back before the host has done either, the question is
  withdrawn and the round carries on.
- A round is never ended automatically. If the host is gone too, their own
  countdown hands the host role to someone who is present, and that host is
  asked instead.
- **A round ended as a draw scores nothing.** No level moves for anyone, and
  the kitty is not counted. The next round starts as usual, with the next seat
  as alpha (a draw has no winning side — see
  [HR-11](#hr-11--the-next-alpha-comes-from-the-winning-side)), and any seat
  nobody took is removed as it starts.

### The host

- If the host **presses Leave**, the host role passes **immediately**.
- If the host **loses connection**, it passes after **60 seconds**.
- Either way it goes to the **player who joined the game earliest** of those
  still at the table. Someone who took over a seat counts from when they took it.
- The new host takes over **every power the old host had**: approving
  volunteers and joiners, and ending a held-up round as a draw.
- The old host's seat is then treated like anyone else's. If they pressed
  Leave, the new host may end the round straight away. If they lost connection,
  the 60-second rule above applies.
- A host who returns comes back as an ordinary player.

### Too few players

- When **fewer than 5 players** are connected, the whole table is warned
  **immediately**, warned again at **5 minutes**, and the room **closes at 10
  minutes**.
- If the table gets back to 5 connected players before then, the countdown stops.

**Unchanged:** the rules of play. Watching and changing seats affect who sits at
the table, never how a hand is dealt, played or scored.

**Implemented by:** [backend_code/Game/Systems/SeatSystem.py](backend_code/Game/Systems/SeatSystem.py),
which holds every rule and countdown above; the socket handlers and the
once-a-second sweep in [backend_code/Main.py](backend_code/Main.py); and
`watcher_view_state` in
[backend_code/Game/Views/PlayerView.py](backend_code/Game/Views/PlayerView.py),
which builds a watcher's view from the same table view a player's starts from.

---

## HR-9 — Two lobby settings start on

**Overrides:** *The Play* in `ZhaoPengyou_Rules.md`, which keeps the attackers'
Kings, Tens and Fives face-up "to make point tracking easy". The other setting
recorded here overrides nothing — see below.

**Why:** every other setting in the lobby starts off, so a host who changes
nothing plays the traditional game. These two do not. What a table gets without
opening the settings is what most tables play, so it belongs in the rules rather
than only in a default value.

**The rule:** a table that configures nothing plays with both of these on:

| Setting | What it does |
|---|---|
| *Draw the first alpha at random* (`random_first_alpha`) | The first alpha is drawn from the table rather than taken by the host. Only the first — after that the seat passes by the usual rules. |
| *Hide points until the round ends* (`hide_scores_until_round_end`) | Nobody sees a running total during the round. The full totals arrive with the round summary. |

Either is the host's to turn off in the lobby, before the cards are dealt.

**The draw is not a departure.** `ZhaoPengyou_Rules.md` → *Who Starts the Deal*
already picks the first starter at random. It was the host always being the
first alpha — what this game did before — that departed from the traditional
rules, so turning this setting off restores that older behaviour, not the
traditional one.

**Hiding the totals is a departure.** Traditionally the attackers' points sit
face-up and anyone can track them. With this on the table keeps count from the
cards it has seen, or waits for the summary. It applies to watchers too
([HR-8](#hr-8--watching-and-taking-a-seat-mid-game)), and is enforced when the
view is built rather than in the client, so the numbers do not leave the server
at all.

**Implemented by:** `GameSettings` in
[backend_code/Game/Components/GameState.py](backend_code/Game/Components/GameState.py);
the draw in `handle_start_game` in [backend_code/Main.py](backend_code/Main.py);
the withheld totals in
[backend_code/Game/Views/PlayerView.py](backend_code/Game/Views/PlayerView.py).

---

## HR-10 — The winner clears the trick

**Overrides:** nothing in `ZhaoPengyou_Rules.md`, which is played face to face
and has no need to say when cards are gathered up. This is a rule about playing
the game on a screen.

**Why:** the cards used to vanish the instant the last player played. At a real
table the trick sits there while everyone looks at it, and the player who took
it gathers it up when they are ready — which is also the moment everyone else
has had to work out what just happened. On a screen the cards were gone before
a slower player had read them, and the information a trick carries is most of
what there is to reason about: who followed suit, who trumped in, who has
finally revealed themselves as a friend.

**The rule:** when the last card of a trick is played, **the trick stays
face-up.** The player who took it clears it, and the next trick starts when they
do. They have **30 seconds**; if they have not cleared it by then the table
clears it for them and play carries on exactly as if they had.

- Card points are settled the moment the trick is won, not when it is cleared.
  Waiting changes nothing about the score.
- Nobody may play while a trick is waiting, including the winner. There is no
  turn during that window.
- Only the winner may clear it. Everyone else is shown whose trick it is and how
  long is left, so a stopped board is never a mystery.
- **The last trick of a round waits like any other.** Clearing it is what ends
  the round. That keeps one rule for every trick, and the last trick is the one
  that decides whether the kitty counts double — the one the table most wants a
  moment to look at.
- A winner who has dropped connection costs the table 30 seconds, not the rest
  of the round.

**Implemented by:** `TRICK_CLEAR_SECONDS`, `trick_waiting` and
`trick_clear_expired` in
[backend_code/Game/Systems/GameStateSystem.py](backend_code/Game/Systems/GameStateSystem.py);
`finish_trick`, `handle_clear_trick` and the expiry in `sweep_game` in
[backend_code/Main.py](backend_code/Main.py).

---

## HR-11 — The next alpha comes from the winning side

**Overrides:** *Subsequent deals* in `ZhaoPengyou_Rules.md` — "the player who
made trumps in the previous deal starts" — and the seat-by-seat rotation this
game used before, which no rule had written down.

**Why:** winning a round should be worth more than the levels alone. Passing
the alpha to the next player on the winning side keeps the initiative with
whoever earned it, while still moving it round the table rather than letting
one player hold it.

**The rule:** going round the table in play order from the last alpha, the
next alpha is **the first player who was on the side that won the round.**

- **The alpha team** is the alpha and every friend who revealed themselves —
  the same sides the round was scored on. Everyone else attacked.
- **After a draw** — nobody moved, or the host ended the round as a draw
  ([HR-8](#hr-8--watching-and-taking-a-seat-mid-game)) — there is no winning
  side, and the alpha passes to the next seat.
- **An alpha who won alone stays alpha.** The walk round the table ends on
  them, and nobody before them was on their side.
- **A seat that is being removed** as the next round starts is passed over. If
  nobody from the winning side is left, the alpha passes to the next seat that
  stays.
- Players joining at the next round are seated after the next alpha is chosen,
  so they never change it.
- The round summary names the next alpha.

> **Example (5 players, play order P1 → P2 → P3 → P4 → P5 → P1).** P4 was
> alpha, and P2 was their friend.
>
> | Result | Next alpha |
> |---|---|
> | Attackers win | P5 — the next seat, and an attacker |
> | Alpha team wins | P2 — past P5 and P1, who attacked |
> | Draw | P5 — the next seat |

**Configurable:** the lobby house rule *Next alpha comes from the winning side*
(`next_alpha_from_winners`) is **on by default**, and is this rule. Turned off,
the alpha passes to the next seat whatever the result.

**Implemented by:** `next_alpha` and `_next_alpha` in
[backend_code/Game/Systems/SeatSystem.py](backend_code/Game/Systems/SeatSystem.py),
called from `prepare_next_round` when the host starts the next round and from
the round summary in
[backend_code/Game/Views/PlayerView.py](backend_code/Game/Views/PlayerView.py).

---

## Unchanged from the traditional rules

Everything in `ZhaoPengyou_Rules.md` not listed above still applies as written,
in particular:

- Trump suit and trump rank, the trump hierarchy, and jokers always being trumps
- Making and overriding trumps by exposing cards matching your level
- Taking the kitty and discarding face-down, with doubled value to the attackers
  if they win the last trick
- Calling specific copies of cards to find friends, and partners staying hidden
  until they play
- All four lead types — single, set of identicals, sequence of sets (tractors),
  and group of top cards — and the penalty for a false top-card lead
- Level promotion from 2 up through Ace, and the game ending beyond Ace

The *Variations* section of `ZhaoPengyou_Rules.md` is not in force unless a house
rule here adopts it.

---

## Change log

| Date | Rule | Change |
|---|---|---|
| 2026-09-10 | HR-1 | Deck ladder raised to 5–6→3, 7–8→4, 9–10→5, 11–12→6 decks, with a new deal table. Replaces the traditional 2/3/4-pack ladder. |
| 2026-09-10 | HR-2 | Recorded as an override: always two jokers per deck, kitty varies (now 5–13). |
| 2026-09-10 | HR-3 | Points in play restated for 3–6 decks: 300/400/500/600. |
| 2026-09-10 | HR-4 | Scoring tiers documented for 5 and 6 decks, which the traditional table does not cover. |
| 2026-09-12 | HR-5 | Following a led tractor now requires keeping a run together where the hand allows one. Adopts the *Forced sub-patterns* variation, overriding "any sets of the right size will do". |
| 2026-09-13 | HR-6 | The side with more card points wins the round and climbs exactly one level; an exact tie moves nobody. No point bands, no margin bonus, no undersized-team multiplier. The traditional scoring stays available as the *Bigger wins climb more levels* house rule. |
| 2026-09-13 | HR-7 | The order of trump, kitty and friend call is a lobby choice of three. Defaults to the traditional trump → kitty → friends; previously the game always called friends before the kitty. |
| 2026-09-13 | HR-8 | Watching, open seats after Leave or 60 seconds disconnected, host-approved takeovers and next-round joins, host handover to the earliest joiner, a host option to end a round held up by an empty seat as a draw, and closing a room left below 5 players for 10 minutes. |
| 2026-09-15 | HR-9 | Two lobby settings now start on rather than off: the first alpha is drawn, and the running point totals are withheld until the round ends. The draw restores the traditional random starter; withholding the totals is a departure from points being trackable face-up. Both stay the host's to turn off. |
| 2026-09-16 | — | Terminology only, no rule change: the non-alpha side is now the **attackers** (it was "the defenders"), since the alpha team is the side holding the points rather than taking them. The tier shorthand `D+n` becomes `A+n`. `ZhaoPengyou_Rules.md` follows the same wording, except where *defend* means defending a trump declaration. |
| 2026-09-20 | HR-10 | A finished trick stays face-up until the player who took it clears it, or until 30 seconds pass and the table clears it for them. Nobody plays during that window, and the last trick of a round waits like any other — clearing it is what ends the round. Card points are still settled the moment the trick is won. |
| 2026-09-20 | HR-4, HR-6 | Scoring rebuilt on the attackers' points alone, against fifths of the points in play: a shutout is +3 to the alpha team, exactly two fifths moves nobody, and each further fifth the attackers pass is another level, capped at 3 either way. Replaces the flat one-level rule, which stays as the opt-out; *Bigger wins climb more levels* now starts **on**. HR-4's 5 and 6 deck tables are rebuilt on the same fifths rule, correcting bands that sat one fifth too high, and the undersized-alpha-team multiplier is gone. |
| 2026-10-03 | HR-11, HR-8 | The next alpha is the next player round the table who was on the side that won the round; after a draw, the next seat. An alpha who won alone stays alpha. Replaces passing the alpha seat by seat whatever the result, which stays available by turning off *Next alpha comes from the winning side*. The round summary names the next alpha. |
