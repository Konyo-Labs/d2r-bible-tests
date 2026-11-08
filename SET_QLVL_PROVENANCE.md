# Where the set-piece qlvl numbers came from

**Filled 2026-09-08 (v2787). 1,477 of 1,598 set-tier drop records now carry a quality level; 121
remain 0, which means UNKNOWN and is not a claim that they are zero.**

His rule, from `HANDOFF_items_tab_scope.md`: *no value ships unless it traces to
`UniqueItems.txt`/`SetItems.txt` (or a 2-source cross-check).* This file is that trace. **The game
data itself is deliberately NOT in this repo — it is Blizzard's and this repo is public.**

## The source

Extracted from the local Diablo II Resurrected CASC store with a CascLib-based reader:

    <D2R install>/Data/data          (CASC, ~28 GB)
      data:data\global\excel\setitems.txt         31325 bytes   sha256 1aa7e5dbb16e27442634a630489b3eee
      data:data\global\excel\base\setitems.txt    30286 bytes   sha256 6481d53c22a525f52248a3043dd2497d

The quality level is the column named **`lvl`** (column 13 of 102); `lvl req` (column 14) is the
character level requirement and is a different number. The join key is the column named **`index`**,
which carries the piece name ("Civerb's Ward"), not `*ItemName`, which carries the base type
("Large Shield").

## The two-source cross-check

Both files were extracted and compared independently. **132 pieces appear in both. They disagree on
zero of them.** That is the second witness his rule allows, taken from a genuinely separate file
rather than a second read of the same bytes.

## Three aliases, and why they are not fabrication

The game's own table misspells three names. Each alias maps a table row to a piece whose identity is
unambiguous from its set and slot — it is a decision about WHICH ROW, never about a VALUE:

| the bible's name | the game table's spelling |
|---|---|
| Haemosu's Adamant | `Haemosu's Adament` |
| Griswold's Redemption | `Griswolds's Redemption` (double-s possessive) |
| Cow King's Hooves | `Cow King's Hoofs` |

## What is still UNKNOWN, and stays that way

Eleven piece names in `bible.html` have **no row in the game table under any spelling**, so they
keep `qlvl: 0`:

    Aldur's Rhythm · Dark Adherent · Hwanin's Blessing · Sander's Paragon · Sander's Riprap
    Sander's Superstition · Sander's Taboo · Taebaek's Glory · Tal Rasha's Fine-Spun Cloth
    Tal Rasha's Guardianship · Whitstan's Guard

⚠ **Some of these are probably NAMING ERRORS IN THE BIBLE, not missing game data.** The table has
`Tal Rasha's Fire-Spun Cloth` where the bible says `Fine-Spun Cloth`, and it has four Aldur's pieces
(Stony Gaze, Deception, Gauntlet, Advance) with no `Aldur's Rhythm` among them. I did **not** guess:
a near-spelling is not a trace, and mapping one would be exactly the fabrication the rule forbids.
These want a human ruling. [[unknown-stays-unknown]]

## v3884 (REG-3440) - THE ELEVEN NOW TRACE TO SILOSPEN, AND EVERY QLVL IS SILOSPEN'S LEVEL

His ruling 2026-11-08 ("the Q levels i think its 69 and not 71? could that based on what it reads in silopen", "bane ash
... the console reads q5 ... it should be q7"): an item's quality level is silospen's `level`. Silospen's RotW 3.0 drop
calculator lists all eleven pieces above, spelled exactly as the bible spells them (so no near-spelling was mapped):

    Aldur's Rhythm 29 · Dark Adherent 39 · Hwanin's Blessing 28 · Sander's Paragon 20 · Sander's Riprap 20
    Sander's Superstition 20 · Sander's Taboo 20 · Taebaek's Glory 55 · Tal Rasha's Fine-Spun Cloth 26
    Tal Rasha's Guardianship 26 · Whitstan's Guard 41

Each agrees with its set-mates (every piece of a set shares one qlvl - the uniformity law still holds). Source:
`dropcalc.php?type=itemProbabilities&version=D2R_ROW_3_0&itemQuality=SET&itemId=<id>` -> `context.level`, read 2026-11-08,
vendored in `tv/data/silospen_qlvl_rotw30.json` (536 uniques and set items). Laws: `tv/test_every_qlvl_is_silospens.py`
(zero mismatches), `tv/test_the_set_pieces_carry_a_real_qlvl.py`, `tv/test_the_missing_wall_shows_the_qlvl.py`.
The game-table extract above stays the record of where the 1,477 levels first came from.

## Reproducing it

The extractor lives OUTSIDE this repo at `~/casc-tools/` (rescued from a `/private/tmp` scratchpad
that the OS sweeper had already begun deleting — its sibling copy had lost its dylib):

    ~/casc-tools/casc_extract "<D2R install root>" 'data:data\global\excel\setitems.txt'

It writes to stdout, so a pull creates no file. If the binary is ever lost, `tv/chronicle_total.py`
carries the ten-minute rebuild recipe: clone ladislav-zezula/CascLib (MIT), cmake, make.
