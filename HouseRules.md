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
5. [Unchanged from the traditional rules](#unchanged-from-the-traditional-rules)
6. [Change log](#change-log)

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

The traditional tiers are proportional to the points in play, so they extend to
5 and 6 decks by scaling. Tiers, by defenders' point total (`T` = trump makers
promoted, `D` = defenders promoted):

**5 decks (500 points in play) — 9–10 players:**

| Defenders' pts | Result |
|---|---|
| 0 | T+3 |
| 5–87 | T+2 |
| 90–187 | T+1 |
| 190–287 | neither |
| 290–387 | D+1 |
| 390–487 | D+2 |
| 490+ | D+3 |

**6 decks (600 points in play) — 11–12 players:**

| Defenders' pts | Result |
|---|---|
| 0 | T+3 |
| 5–105 | T+2 |
| 108–225 | T+1 |
| 228–345 | neither |
| 348–465 | D+1 |
| 468–585 | D+2 |
| 588+ | D+3 |

Card points only ever arrive in multiples of 5, so the apparent gaps between
tiers (88–89, 188–189, 106–107, and so on) are unreachable.

**Unchanged:** the undersized-alpha-team bonus. If the trump makers win with
fewer than the maximum team size, their promotion is multiplied the same way as
in the traditional rules, for every table size.

**Implemented by:** `calculate_level_promotion` in
[backend_code/Game/Systems/PointSystem.py](backend_code/Game/Systems/PointSystem.py),
which scales the 2-pack tiers by `decks / 2` for any deck count it has no
explicit table for.

---

## Unchanged from the traditional rules

Everything in `ZhaoPengyou_Rules.md` not listed above still applies as written,
in particular:

- Trump suit and trump rank, the trump hierarchy, and jokers always being trumps
- Making and overriding trumps by exposing cards matching your level
- Taking the kitty and discarding face-down, with doubled value to the defenders
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
