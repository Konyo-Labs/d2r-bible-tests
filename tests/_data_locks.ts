// Shared STRICT data-count locks (consolidated 2026-06-12, audit item B-3).
// These are deliberate tripwires: an exact count catches accidental data loss
// (a bad edit dropping 5 items turns the suite red immediately). Konyo's call:
// keep them strict — do NOT loosen to ranges or derive them from the data.
// When content is deliberately added/removed, update the ONE constant here;
// every spec imports from this file, so there is exactly one line to bump.

// Boss roster chips: 11 farmable bosses + 2 event drops
// (Summoner = Key of Hate, Dclone = Annihilus).
export const BOSS_CHIPS_TOTAL = 13;

// The calculator grid's full grail item count.
// v1717 — STAYS 322. The v1716 silospen pull added 216 item names to the drop tables, and for a
// few hours they landed in ITEMS too, which tripled the Calculator grid to 538 and put 66 of the
// 69 _UNI_EXTRA uniques inside the one surface bible.html says in words they must never enter.
// The routing now reads window.ITEM_REGISTRY (every droppable item) while ITEMS stays the curated
// calculator DB — so this tripwire keeps doing its job and the number it guards did not move.
// v3859 — 320 → 318: Konyo ruled "Polaris Spear" is not a unique (removed) and "The Scourge" is
// Stormlash's BASE (an alias of Stormlash, not a card). Both rows left ITEMS and the drop tables.
// v3890 — 318 → 317: Wilhelm's Pride is an Orphan's Call SET belt (ITEM_CODEX rarity set, green tip,
// same qlvl 41 as Guillaume's Face / Whitstan's Guard / Magnus' Skin). Its drop rows had been
// tagged tier:common without nc:1, so it sat in the calculator unique grid. REG-3506's unique-first
// roll then made those cells diverge from adjustChance (the unique curve the integrity test uses).
// The rows now carry tier:set and nc:1 like the other Orphan's Call pieces: still in ITEM_REGISTRY
// (DROP_INDEX_TOTAL unchanged) and on the Sets tab, out of the curated calculator grid.
export const CALC_ITEMS_TOTAL = 317;

// Distinct item names across every boss dropTable — the MASTER drop index that
// ITEM_REGISTRY is built from, and what the farm routing reads. This is a different
// number from CALC_ITEMS_TOTAL by design since v1717: the silospen RoW 3.0 pull put 216
// more real drops into the tables, and rows the calculator has no card for carry `nc:1`
// so they join the registry WITHOUT joining the curated calculator grid.
// v1720 — 538 → 549: Konyo ruled the 11 RotW uniques the pull found (Entropy Locket,
// Hellwarden's Will, the two missing Latent sunders, Measured Wrath, Opalvein, Sling, the three
// Ars charms, Gheed's Wager) into the GRAIL ROSTER, so their drop rows came back. They carry
// `nc:1` and stay out of CALC_ITEMS_TOTAL, which is why only this number moves.
// v1724 — 549 → 548 and the calculator 322 → 321: "Bloodmoon's Light" was removed. Its ITEM_CODEX
// entry gave its base item as "Reign of the Warlock" — the MOD'S NAME — with a note describing a
// sin claw and drop numbers cloning Jade Talon (tc85/qlvl71). Absent from ITEM_VALUE, the roster,
// his ledger and silospen's pool. A garbled ingest row, not an item.
// v1725 — 548 → 547 and the calculator 321 → 320: `Crescent Moon (sword)` was the RUNEWORD
// (ITEM_TIP: "t":"Runeword", Shael+Um+Tir affixes) listed as a farmable unique in ELEVEN boss
// drop tables, with a codex entry calling it a unique amulet. A runeword cannot drop.
// Same tripwire rule as its sibling: exact, and bumped deliberately.
// v3859 — 547 → 545: the same two rows (the fake spear, and The Scourge folded into Stormlash).
export const DROP_INDEX_TOTAL = 545;

// Collapsible .sec-h sections on the binds tab — bump in LOCKSTEP when adding
// a binds section (the v109 memory rule).
export const BINDS_SECTIONS_TOTAL = 16;

// isEndgameRelic() canonical set size (v80).
export const ENDGAME_RELICS_TOTAL = 15;

// Nav tab bar entries (v158 dock spec). v232: +TZ tracker → 12.
// v2099 — 17 → 19. Two rooms joined the workshop group and this pin did not move with them:
//   v2085  🎒 Vault  (its own room between F·Sets and TV·D)
//   v2094  ⚗️ Crafts (the cube-crafts, split out of the Forge chronicle)
// Routine I went red on shards 2 and 5 for two SHAs — "Expected 17 Received 18" — while every
// gate I ran locally stayed green, because the pre-push hook runs a SMOKE subset and the full
// Playwright suite only runs on CI. A pin is a CLAIM about the product; moving the product
// without moving the claim turns a real gate into noise. Measured, not assumed:
//   document.querySelectorAll('.tabs .tab[data-tab]').length === 19
// #245 — 19 → 20: 👤 Characters joined the workshop, right before the Vault (the manual side beside the
//   automated one). Measured in headless Chrome: the workshop row reads session · tools · forge · crafts ·
//   funi · fsets · chars · vault · tvd.
// v3693 — 20 → 21: D2JSP joined the workshop, right after the Vault. The console header door is a
//   separate strip and is not part of this count.
export const NAV_TABS_TOTAL = 21;   // v710.4 +📺 TV·D · v2085 +🎒 Vault · v2094 +⚗️ Crafts · #245 +👤 Characters · v3693 + D2JSP

// Horadric cube recipe browser rows (v177).
export const HORADRIC_RECIPES_TOTAL = 36;
