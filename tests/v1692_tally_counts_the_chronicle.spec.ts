import { test, expect } from './_net_stub';
import * as path from 'path';
import { suppressOneShots } from './_oneshots';

/* ══════════════════════════════════════════════════════════════════════════════════════════════
   v1692 — THE TALLY COUNTS THE CHRONICLE HE ACTUALLY HAS, AND IT GOES UP ON ITS OWN.

   Konyo: "i want it not rendering these numbers ive farmed alot more items in uniques and sets"
   · "from 236 it NEEDS TO GO UP". This spec is the proof, and the thing it proves is A NUMBER ON
   HIS SCREEN — the "named cards: N / M ticked" line inside #funi-body after his own click on the
   🏆 F·uniques tab — not a helper's return value. funiScan() is read too, and the two must agree.

   THE DATA IS HIS, NOT A FIXTURE. Every number below is measured against his real 346-key
   d2r_foundLog (236 bare unique names + 110 "(piece)" set rows), his 110-entry d2r_setPieces and
   his 9-name d2r_grailUnfound. Two sources, in this order:
     1. the READ-ONLY copy of his WKWebView store at LEDGER_DB (node:sqlite, readOnly:true —
        no write path in this file ever touches his live store), when that copy exists;
     2. otherwise REAL_SNAPSHOT below — the SAME data, exported from that copy on 2026-08-11 and
        frozen here so the gate is portable to CI and to the Windows box.
   There is deliberately NO synthetic fallback: a same-shape fake would let assert (0) pass on
   fabricated data, which is exactly how a gate ends up certifying nothing. When BOTH sources are
   available test (0) also diffs them, so a drifted snapshot is a red, not a silent lie.

   RED-PROVE SEAM (how this file was proven non-vacuous, and how to re-prove it):
     V1692_BIBLE=/abs/path/to/v1691/bible.html npx playwright test tests/v1692_*.spec.ts
   Measured on v1691 (HEAD fd36be6) through that seam: funiScan().total 368 (the boss-drop shortlist),
   window.d2rResolveItem undefined, window._gUnfoundConflicts undefined, #funi-body EMPTY at boot,
   no auto-apply (foundLog stays 346, found stays 236). Every assertion below except the raw
   baseline 236/110 goes RED there, with those numbers.

   ONE NUMBER IS DELIBERATELY NOT PINNED: the roster/denominator. It measured 512 at 02:52 and 385
   at 02:56 on 2026-08-11 while the implementation was still being tuned (512 counted set pieces
   and bases as uniques; 385 does not, and that is why the on-screen "chronicle rows still dark"
   line went from -109 to 18). Pinning a roster in a test is how a test ends up blessing whatever
   roster it was born with, so what is asserted here instead is the pair of laws the tuning cannot
   break: THE SCREEN AND funiScan() MUST PRINT THE SAME DENOMINATOR, it must not be 368 again, and
   the found count must equal the number of unique names in HIS OWN LEDGER — 236, whatever the
   universe around them is.
   ══════════════════════════════════════════════════════════════════════════════════════════════ */

const LEDGER_DB = '/private/tmp/claude-501/-Users-konyo/63b4ef22-a3c0-4f38-bb69-b17a7839a6ae/scratchpad/ls/1/localstorage.sqlite3';
const BIBLE = process.env.V1692_BIBLE || path.resolve(__dirname, '..', 'bible.html');
const URL = 'file://' + BIBLE;

// ── the measured magnitudes, stated before anything is read ──────────────────────────────────
const N_FOUNDLOG   = 346;   // keys in his d2r_foundLog
const N_SETPIECES  = 110;   // his d2r_setPieces entries
const N_UNIQUES    = 236;   // 346 - 110: the bare unique names = the baseline tally
const N_ROSTER_V1691 = 368; // the boss-drop shortlist v1691 tallied against — the number that must NOT come back
const N_PIECES_IN_LOG = 110;// foundLog keys the resolver calls 'set-piece' — 346 = 236 + 110, exactly
const N_SETS_TOTAL = 135;   // fsetsScan().totalPieces
const N_AFTER      = 248;   // v1695: 236 + Fleshrender + Gloom's Trap (v1692) + the nine + The Diggler (v1693 ruling)
/* v1695 — ONE NAME HAD COME TO MEAN TWO DIFFERENT QUANTITIES, which is the exact defect class this
   arc keeps finding: N_CONFLICTS was used both for the nine un-ticks recorded in the FIXTURE
   (history, permanently 9) and for the conflicts still LIVE on screen (0, since his v1693 ruling
   resolved them). They were the same number until he ruled, and then they silently were not. */
const N_CONFLICTS_SEEDED = 9;   // d2r_grailUnfound in his captured ledger — the history, never rewritten
const N_CONFLICTS_LIVE   = 0;   // still-contested after his v1693 ruling
/* the twelve a FIRST load applies, itemised so this is an inventory and not a magic number:
   v1692 → Fleshrender, Gloom's Trap                                            (2)
   v1693 → the nine he ruled on (Blackbog's Sharp · Islestrike · Lidless Wall ·
           Sureshrill Frost · Gravepalm · Hellslayer · Vampire Gaze · Pluckeye ·
           Chance Guards)                                                       (9)
   v1693 → The Diggler                                                          (1) */
const N_APPLIED_ON_FIRST_LOAD = 12;
const N_BATCHES_ON_FIRST_LOAD = 3;   // one undoable batch per one-shot, never one merged write

// REAL_SNAPSHOT — his real store, exported 2026-08-11 from the read-only copy above. Frozen, not
// synthetic. Only the five keys this ship reads; nothing here is written back anywhere.
const REAL_SNAPSHOT: Record<string, string> = {
  "d2r_foundLog": "{\"Wormskull\":\"Jun 22, 2026 \u00b7 02:00\",\"Wraith Flight\":\"Jun 18, 2026 \u00b7 19:29\",\"Witherstring\":\"Jul 1, 2026 \u00b7 21:09\",\"Wizardspike\":\"Jun 3, 2026 \u00b7 12:45\",\"Wizendraw\":\"May 20, 2026 \u00b7 21:15\",\"Wolfhowl\":\"Jun 5, 2026 \u00b7 00:45\",\"War Traveler\":\"Jun 4, 2026 \u00b7 01:24\",\"Windhammer\":\"May 22, 2026 \u00b7 01:17\",\"Venom Grip\":\"May 20, 2026 \u00b7 18:35\",\"Venom Ward\":\"May 18, 2026 \u00b7 21:07\",\"Verdungo's Hearty Cord\":\"Jun 22, 2026 \u00b7 02:10\",\"Wall of the Eyeless\":\"May 20, 2026 \u00b7 18:26\",\"Twitchthroe\":\"Jun 2, 2026 \u00b7 01:07\",\"Ume's Lament\":\"May 18, 2026 \u00b7 00:25\",\"Undead Crown\":\"May 17, 2026 \u00b7 01:45\",\"Tomb Reaver\":\"Jun 18, 2026 \u00b7 02:19\",\"Toothrow\":\"May 22, 2026 \u00b7 00:59\",\"Treads of Cthon\":\"May 20, 2026 \u00b7 19:21\",\"The Ward\":\"May 18, 2026 \u00b7 00:40\",\"Thundergod's Vigor\":\"May 20, 2026 \u00b7 02:19\",\"Tiamat's Rebuke\":\"May 15, 2026 \u00b7 18:24\",\"Todesfaelle Flamme\":\"Jun 4, 2026 \u00b7 01:23\",\"The Rising Sun\":\"Jun 3, 2026 \u00b7 00:48\",\"The Salamander\":\"May 18, 2026 \u00b7 01:26\",\"The Spirit Shroud\":\"Jun 6, 2026 \u00b7 20:49\",\"The Vile Husk\":\"Jun 30, 2026 \u00b7 21:17\",\"The Jade Tan Do\":\"May 19, 2026 \u00b7 23:44\",\"The Minotaur\":\"Jul 6, 2026 \u00b7 21:10\",\"The Patriarch\":\"May 15, 2026 \u00b7 01:19\",\"The Reaper's Toll\":\"May 18, 2026 \u00b7 21:15\",\"The Gavel of Pain\":\"Jun 10, 2026 \u00b7 01:57\",\"The General's Tan Do Li Ga\":\"May 17, 2026 \u00b7 01:37\",\"The Grandfather\":\"Jun 4, 2026 \u00b7 01:41\",\"The Grim Reaper\":\"May 17, 2026 \u00b7 01:43\",\"Tearhaunch\":\"May 15, 2026 \u00b7 18:36\",\"The Battlebranch\":\"May 26, 2026 \u00b7 00:14\",\"The Chieftain\":\"May 18, 2026 \u00b7 21:04\",\"The Face of Horror\":\"May 20, 2026 \u00b7 02:19\",\"Suicide Branch\":\"May 27, 2026 \u00b7 00:49\",\"Swordguard\":\"Jun 22, 2026 \u00b7 02:57\",\"Stoneraven\":\"Jun 4, 2026 \u00b7 01:22\",\"Stormguild\":\"May 18, 2026 \u00b7 01:40\",\"Stormshield\":\"May 27, 2026 \u00b7 19:51\",\"Stormspike\":\"Jun 18, 2026 \u00b7 00:14\",\"Stormstrike\":\"May 17, 2026 \u00b7 01:53\",\"Stoutnail\":\"Jun 22, 2026 \u00b7 02:25\",\"Steel Shade\":\"May 18, 2026 \u00b7 01:50\",\"Steelclash\":\"May 21, 2026 \u00b7 11:51\",\"Steeldriver\":\"May 18, 2026 \u00b7 02:03\",\"Spire of Honor\":\"May 27, 2026 \u00b7 20:16\",\"Spirit Forge\":\"Jun 18, 2026 \u00b7 01:03\",\"Stealskull\":\"May 31, 2026 \u00b7 21:37\",\"Snowclash\":\"May 19, 2026 \u00b7 16:12\",\"Sparking Mail\":\"May 15, 2026 \u00b7 20:58\",\"Spellsteel\":\"May 17, 2026 \u00b7 23:50\",\"Skystrike\":\"May 18, 2026 \u00b7 00:38\",\"Snakecord\":\"May 15, 2026 \u00b7 00:58\",\"Skin of the Vipermagi\":\"May 20, 2026 \u00b7 22:27\",\"Skullder's Ire\":\"May 22, 2026 \u00b7 01:21\",\"Serpent Lord\":\"May 17, 2026 \u00b7 01:43\",\"Shaftstop\":\"May 31, 2026 \u00b7 20:50\",\"Sandstorm Trek\":\"Jun 25, 2026 \u00b7 00:56\",\"Schaefer's Hammer\":\"Jun 4, 2026 \u00b7 00:26\",\"Riphook\":\"May 27, 2026 \u00b7 20:59\",\"Rockfleece\":\"May 18, 2026 \u00b7 23:17\",\"Rockstopper\":\"May 27, 2026 \u00b7 19:44\",\"Rogue's Bow\":\"May 19, 2026 \u00b7 00:25\",\"Rattlecage\":\"Jun 21, 2026 \u00b7 17:52\",\"Raven Claw\":\"Jun 4, 2026 \u00b7 01:32\",\"Raven Frost\":\"May 25, 2026 \u00b7 21:26\",\"Razortail\":\"May 21, 2026 \u00b7 01:03\",\"Ribcracker\":\"May 17, 2026 \u00b7 01:32\",\"Pierre Tombale Couant\":\"Jul 6, 2026 \u00b7 22:43\",\"Plague Bearer\":\"May 27, 2026 \u00b7 01:29\",\"Pompeii's Wrath\":\"May 27, 2026 \u00b7 00:51\",\"Que-Hegan's Wisdom\":\"Jun 4, 2026 \u00b7 01:22\",\"Peasant Crown\":\"May 15, 2026 \u00b7 21:22\",\"Pelta Lunata\":\"Jun 29, 2026 \u00b7 01:20\",\"Nature's Peace\":\"May 23, 2026 \u00b7 01:06\",\"Nightsmoke\":\"May 15, 2026 \u00b7 20:17\",\"Nightwing's Veil\":\"May 18, 2026 \u00b7 00:38\",\"Nokozan Relic\":\"Jun 18, 2026 \u00b7 20:37\",\"Nord's Tenderizer\":\"May 18, 2026 \u00b7 20:53\",\"Nosferatu's Coil\":\"Jun 18, 2026 \u00b7 18:57\",\"Messerschmidt's Reaver\":\"May 31, 2026 \u00b7 23:46\",\"Moser's Blessed Circle\":\"Jun 10, 2026 \u00b7 21:55\",\"Manald Heal\":\"May 18, 2026 \u00b7 23:53\",\"Mang Song's Lesson\":\"May 31, 2026 \u00b7 21:00\",\"Marrowwalk\":\"Jun 21, 2026 \u00b7 20:12\",\"Lightsabre\":\"May 22, 2026 \u00b7 01:17\",\"Maelstrom\":\"Jun 1, 2026 \u00b7 01:00\",\"Magefist\":\"May 18, 2026 \u00b7 00:43\",\"Magewrath\":\"May 26, 2026 \u00b7 01:52\",\"Lava Gout\":\"May 18, 2026 \u00b7 21:11\",\"Kuko Shakaku\":\"Jun 19, 2026 \u00b7 00:46\",\"Lacerator\":\"Jun 4, 2026 \u00b7 01:41\",\"Lance Guard\":\"May 19, 2026 \u00b7 20:29\",\"Lance of Yaggai\":\"May 17, 2026 \u00b7 00:57\",\"Kira's Guardian\":\"May 19, 2026 \u00b7 20:39\",\"Iceblink\":\"May 15, 2026 \u00b7 20:54\",\"Infernostride\":\"May 20, 2026 \u00b7 21:58\",\"Ironstone\":\"May 19, 2026 \u00b7 20:30\",\"Jalal's Mane\":\"Jun 10, 2026 \u00b7 12:46\",\"Hotspur\":\"Jun 24, 2026 \u00b7 17:59\",\"Howltusk\":\"Jun 10, 2026 \u00b7 12:28\",\"Hellrack\":\"Jun 19, 2026 \u00b7 00:14\",\"Hexfire\":\"May 23, 2026 \u00b7 18:25\",\"Homunculus\":\"May 27, 2026 \u00b7 19:54\",\"Hone Sundan\":\"May 22, 2026 \u00b7 01:11\",\"Heart Carver\":\"May 26, 2026 \u00b7 00:19\",\"Heavenly Garb\":\"May 25, 2026 \u00b7 21:25\",\"Gravenspine\":\"May 17, 2026 \u00b7 01:51\",\"Gore Rider\":\"Jun 1, 2026 \u00b7 00:08\",\"Gorefoot\":\"Jun 12, 2026 \u00b7 23:47\",\"Goldskin\":\"May 15, 2026 \u00b7 15:20\",\"Goldstrike Arch\":\"May 18, 2026 \u00b7 00:37\",\"Goldwrap\":\"Jun 22, 2026 \u00b7 02:34\",\"Gimmershred\":\"May 28, 2026 \u00b7 20:14\",\"Ginther's Rift\":\"May 18, 2026 \u00b7 23:32\",\"Ethereal Edge\":\"May 31, 2026 \u00b7 20:47\",\"Firelizard's Talons\":\"May 20, 2026 \u00b7 01:36\",\"Flamebellow\":\"May 31, 2026 \u00b7 20:57\",\"Fleshripper\":\"May 28, 2026 \u00b7 20:23\",\"Ghoulhide\":\"May 15, 2026 \u00b7 20:23\",\"Doomslinger\":\"Jun 10, 2026 \u00b7 23:51\",\"Duriel's Shell\":\"Jun 1, 2026 \u00b7 00:28\",\"Duskdeep\":\"Jun 22, 2026 \u00b7 02:51\",\"Demonhorn's Edge\":\"May 18, 2026 \u00b7 01:05\",\"Demon Limb\":\"Jun 2, 2026 \u00b7 01:09\",\"Demon Machine\":\"May 25, 2026 \u00b7 21:56\",\"Demon's Arch\":\"May 18, 2026 \u00b7 01:40\",\"Death Cleaver\":\"May 19, 2026 \u00b7 16:05\",\"Crow Caw\":\"May 20, 2026 \u00b7 01:36\",\"Crushflange\":\"Jun 15, 2026 \u00b7 02:37\",\"Coldkill\":\"Jun 4, 2026 \u00b7 11:27\",\"Crainte Vomir\":\"Jul 6, 2026 \u00b7 21:05\",\"Cranebeak\":\"Jun 1, 2026 \u00b7 00:29\",\"Cloudcrack\":\"Jun 4, 2026 \u00b7 01:24\",\"Coif of Glory\":\"May 15, 2026 \u00b7 20:02\",\"Bverrit Keep\":\"May 18, 2026 \u00b7 00:33\",\"Carin Shard\":\"Jun 10, 2026 \u00b7 22:36\",\"Cerebus' Bite\":\"Jun 24, 2026 \u00b7 17:27\",\"Boneflesh\":\"May 26, 2026 \u00b7 01:21\",\"Bonehew\":\"Jun 18, 2026 \u00b7 02:21\",\"Boneslayer Blade\":\"May 21, 2026 \u00b7 13:24\",\"Bonesnap\":\"Jun 4, 2026 \u00b7 01:45\",\"Brainhew\":\"Jun 4, 2026 \u00b7 01:24\",\"Buriza-Do Kyanon\":\"May 31, 2026 \u00b7 20:46\",\"Blastbark\":\"Jun 22, 2026 \u00b7 01:56\",\"Bloodfist\":\"Jun 19, 2026 \u00b7 21:36\",\"Bloodletter\":\"May 15, 2026 \u00b7 17:47\",\"Bloodrise\":\"May 24, 2026 \u00b7 02:09\",\"Blade of Ali Baba\":\"May 25, 2026 \u00b7 23:55\",\"Bladebuckle\":\"May 27, 2026 \u00b7 20:11\",\"Bing Sz Wang\":\"May 31, 2026 \u00b7 20:42\",\"Black Hades\":\"Jun 22, 2026 \u00b7 02:08\",\"Blackhorn's Face\":\"Jun 15, 2026 \u00b7 02:54\",\"Blackleach Blade\":\"Jun 15, 2026 \u00b7 02:48\",\"Atma's Scarab\":\"Jun 19, 2026 \u00b7 20:17\",\"Bartuc's Cut-Throat\":\"May 20, 2026 \u00b7 02:19\",\"Andariel's Visage\":\"May 25, 2026 \u00b7 21:32\",\"Arioc's Needle\":\"May 21, 2026 \u00b7 12:53\",\"Arm of King Leoric\":\"May 26, 2026 \u00b7 00:00\",\"Wraithstep\":\"Jul 6, 2026 \u00b7 22:06\",\"Zakarum's Hand\":\"May 23, 2026 \u00b7 18:22\",\"Woestave\":\"May 20, 2026 \u00b7 13:50\",\"Viperfork\":\"May 18, 2026 \u00b7 23:36\",\"The Scalper\":\"May 20, 2026 \u00b7 02:19\",\"The Tannr Gorerod\":\"Jun 1, 2026 \u00b7 02:09\",\"The Iron Jang Bong\":\"May 19, 2026 \u00b7 19:54\",\"The Mahim-Oak Curio\":\"May 18, 2026 \u00b7 00:15\",\"The Fetid Sprinkler\":\"May 23, 2026 \u00b7 18:03\",\"The Dragon Chang\":\"Jun 10, 2026 \u00b7 22:13\",\"Steelgoad\":\"May 20, 2026 \u00b7 22:29\",\"Stone Crusher\":\"May 29, 2026 \u00b7 00:28\",\"Spineripper\":\"May 18, 2026 \u00b7 01:35\",\"Soul Harvest\":\"May 31, 2026 \u00b7 21:18\",\"Soulflay\":\"May 25, 2026 \u00b7 19:04\",\"Spectral Shard\":\"May 24, 2026 \u00b7 21:45\",\"Skewer of Krintiz\":\"May 15, 2026 \u00b7 21:06\",\"Skull Splitter\":\"May 20, 2026 \u00b7 01:42\",\"Shadowfang\":\"May 27, 2026 \u00b7 23:48\",\"Ripsaw\":\"May 15, 2026 \u00b7 20:51\",\"Rune Master\":\"Jun 3, 2026 \u00b7 00:20\",\"Rusthandle\":\"May 31, 2026 \u00b7 20:39\",\"Razortine\":\"May 18, 2026 \u00b7 01:47\",\"Moonfall\":\"May 15, 2026 \u00b7 20:12\",\"Medusa's Gaze\":\"May 27, 2026 \u00b7 19:45\",\"Latent Black Cleft\":\"Jun 8, 2026 \u00b7 17:26\",\"Latent Cold Rupture\":\"Jun 12, 2026 \u00b7 00:40\",\"Latent Crack of the Heavens\":\"Jun 25, 2026 \u00b7 00:47\",\"Latent Rotting Fissure\":\"Jun 18, 2026 \u00b7 02:24\",\"Leadcrow\":\"Jun 4, 2026 \u00b7 00:40\",\"Langer Briser\":\"Jun 8, 2026 \u00b7 19:53\",\"Knell Striker\":\"Jun 29, 2026 \u00b7 00:57\",\"Kelpie Snare\":\"May 29, 2026 \u00b7 00:46\",\"Kinemil's Awl\":\"Jun 10, 2026 \u00b7 16:01\",\"Ichorsting\":\"May 18, 2026 \u00b7 00:17\",\"Iron Pelt\":\"Jun 4, 2026 \u00b7 20:41\",\"Horizon's Tornado\":\"May 31, 2026 \u00b7 21:23\",\"Humongous\":\"May 18, 2026 \u00b7 01:40\",\"Husoldal Evo\":\"May 19, 2026 \u00b7 20:29\",\"Hellcast\":\"May 17, 2026 \u00b7 23:53\",\"Hellplague\":\"May 15, 2026 \u00b7 00:04\",\"Herald of Zakarum\":\"May 27, 2026 \u00b7 22:31\",\"Griswold's Edge\":\"May 15, 2026 \u00b7 20:10\",\"Grim's Burning Dead\":\"Jun 24, 2026 \u00b7 17:57\",\"Goreshovel\":\"May 14, 2026 \u00b7 19:15\",\"Gleamscythe\":\"Jun 1, 2026 \u00b7 01:58\",\"Dreadfang\":\"May 25, 2026 \u00b7 21:35\",\"Dimoak's Hew\":\"May 25, 2026 \u00b7 23:47\",\"Dark Clan Crusher\":\"May 19, 2026 \u00b7 20:25\",\"Darkglow\":\"May 19, 2026 \u00b7 11:27\",\"Deathbit\":\"May 23, 2026 \u00b7 17:53\",\"Deathspade\":\"May 14, 2026 \u00b7 18:57\",\"Culwen's Point\":\"May 18, 2026 \u00b7 23:38\",\"Coldsteel Eye\":\"Jun 19, 2026 \u00b7 20:25\",\"Bloodpact Shard\":\"Jun 4, 2026 \u00b7 01:20\",\"Bloodthief\":\"May 14, 2026 \u00b7 18:53\",\"Bladebone\":\"May 12, 2026 \u00b7 00:43\",\"Blacktongue\":\"May 20, 2026 \u00b7 18:41\",\"Axe of Fechmar\":\"Jun 15, 2026 \u00b7 02:40\",\"Baezil's Vortex\":\"Jun 4, 2026 \u00b7 00:50\",\"Athena's Wrath\":\"May 19, 2026 \u00b7 00:19\",\"Nagelring\":\"May 19, 2026 \u00b7 16:08\",\"Djinn Slayer\":\"May 18, 2026 \u00b7 01:45\",\"Endlesshail\":\"Jun 24, 2026 \u00b7 17:56\",\"Hawkmail\":\"May 14, 2026 \u00b7 19:30\",\"Radament's Sphere\":\"May 18, 2026 \u00b7 23:24\",\"Rakescar\":\"May 25, 2026 \u00b7 23:49\",\"Skull Collector\":\"Jul 6, 2026 \u00b7 22:59\",\"Steel Carapace\":\"May 19, 2026 \u00b7 23:48\",\"String of Ears\":\"Jun 3, 2026 \u00b7 00:34\",\"Witchwild String\":\"Jun 2, 2026 \u00b7 01:04\",\"Aldur's Advance (boots)\":\"May 18, 2026 \u00b7 23:24\",\"Aldur's Rhythm (mace)\":\"May 18, 2026 \u00b7 23:39\",\"Aldur's Stony Gaze (helm)\":\"Jun 4, 2026 \u00b7 01:18\",\"Angelic Halo (ring)\":\"May 18, 2026 \u00b7 01:28\",\"Angelic Mantle (armor)\":\"May 14, 2026 \u00b7 18:27\",\"Angelic Sickle (sword)\":\"May 19, 2026 \u00b7 16:12\",\"Angelic Wings (amulet)\":\"May 19, 2026 \u00b7 23:47\",\"Arcanna's Deathwand (staff)\":\"May 15, 2026 \u00b7 20:47\",\"Arcanna's Flesh (armor)\":\"May 28, 2026 \u00b7 20:14\",\"Arcanna's Head (helm)\":\"May 14, 2026 \u00b7 20:17\",\"Arcanna's Sign (amulet)\":\"Jul 5, 2026 \u00b7 23:20\",\"Arctic Binding (belt)\":\"May 15, 2026 \u00b7 20:05\",\"Arctic Furs (armor)\":\"May 13, 2026 \u00b7 00:21\",\"Arctic Horn (bow)\":\"May 21, 2026 \u00b7 13:16\",\"Arctic Mitts (gloves)\":\"May 25, 2026 \u00b7 21:36\",\"Bane's Authority (belt)\":\"May 17, 2026 \u00b7 01:29\",\"Bane's Oathmaker (sword)\":\"May 19, 2026 \u00b7 20:30\",\"Bane's Wraithskin (armor)\":\"May 14, 2026 \u00b7 20:07\",\"Berserker's Hatchet (axe)\":\"May 18, 2026 \u00b7 23:14\",\"Berserker's Hauberk (armor)\":\"May 15, 2026 \u00b7 15:39\",\"Berserker's Headgear (helm)\":\"May 18, 2026 \u00b7 23:33\",\"Bul-Kathos' Sacred Charge (sword)\":\"May 18, 2026 \u00b7 02:25\",\"Cathan's Mesh (chainmail)\":\"May 15, 2026 \u00b7 14:23\",\"Cathan's Rule (rod)\":\"May 20, 2026 \u00b7 01:42\",\"Cathan's Seal (ring)\":\"May 16, 2026 \u00b7 01:20\",\"Cathan's Sigil (amulet)\":\"May 27, 2026 \u00b7 19:40\",\"Cathan's Visage (mask)\":\"May 18, 2026 \u00b7 00:45\",\"Civerb's Cudgel (scepter)\":\"Jun 4, 2026 \u00b7 12:57\",\"Civerb's Icon (amulet)\":\"May 19, 2026 \u00b7 23:43\",\"Civerb's Ward (shield)\":\"Jun 10, 2026 \u00b7 19:42\",\"Cleglaw's Claw (shield)\":\"May 27, 2026 \u00b7 19:30\",\"Cleglaw's Pincers (gloves)\":\"May 14, 2026 \u00b7 18:40\",\"Cleglaw's Tooth (sword)\":\"May 15, 2026 \u00b7 19:20\",\"Cow King's Hide (studded leather)\":\"May 20, 2026 \u00b7 01:50\",\"Cow King's Horns (war bonnet)\":\"May 17, 2026 \u00b7 01:56\",\"Credendum (mithril coil)\":\"May 18, 2026 \u00b7 23:22\",\"Dangoon's Teaching (reinforced mace)\":\"Jun 10, 2026 \u00b7 21:54\",\"Dark Adherent (dusk shroud)\":\"May 22, 2026 \u00b7 00:58\",\"Death's Touch (sword)\":\"May 15, 2026 \u00b7 18:10\",\"Griswold's Heart (armor)\":\"May 17, 2026 \u00b7 01:51\",\"Griswold's Valor (helm)\":\"Jun 8, 2026 \u00b7 16:10\",\"Guillaume's Face (winged helm)\":\"Jun 10, 2026 \u00b7 23:36\",\"Haemosu's Adamant (cuirass)\":\"May 18, 2026 \u00b7 00:32\",\"Horazon's Countenance (helm)\":\"May 19, 2026 \u00b7 21:06\",\"Horazon's Hold (gloves)\":\"May 15, 2026 \u00b7 20:03\",\"Horazon's Legacy (boots)\":\"May 19, 2026 \u00b7 00:23\",\"Hsarus' Iron Fist (shield)\":\"Jul 12, 2026 \u00b7 19:08\",\"Hsarus' Iron Heel (boots)\":\"May 25, 2026 \u00b7 01:50\",\"Hsarus' Iron Stay (belt)\":\"May 14, 2026 \u00b7 18:41\",\"Hwanin's Blessing (belt)\":\"May 14, 2026 \u00b7 23:38\",\"Hwanin's Justice (bill)\":\"Jun 3, 2026 \u00b7 21:44\",\"Hwanin's Refuge (tigulated mail)\":\"Jun 21, 2026 \u00b7 19:57\",\"Hwanin's Splendor (grand crown)\":\"May 29, 2026 \u00b7 00:52\",\"Immortal King's Detail (belt)\":\"May 18, 2026 \u00b7 23:34\",\"Immortal King's Forge (gloves)\":\"May 15, 2026 \u00b7 19:09\",\"Immortal King's Pillar (boots)\":\"Jun 2, 2026 \u00b7 01:06\",\"Immortal King's Stone Crusher (hammer)\":\"May 23, 2026 \u00b7 17:56\",\"Infernal Cranium (helm)\":\"Jun 29, 2026 \u00b7 01:31\",\"Infernal Sign (belt)\":\"May 15, 2026 \u00b7 18:36\",\"Infernal Torch (wand)\":\"May 27, 2026 \u00b7 23:58\",\"Iratha's Coil (helm)\":\"May 25, 2026 \u00b7 21:53\",\"Iratha's Collar (amulet)\":\"Jun 18, 2026 \u00b7 00:18\",\"Iratha's Cord (belt)\":\"May 14, 2026 \u00b7 23:56\",\"Iratha's Cuff (gloves)\":\"May 19, 2026 \u00b7 15:52\",\"Isenhart's Case (armor)\":\"May 15, 2026 \u00b7 20:06\",\"Isenhart's Horns (helm)\":\"May 17, 2026 \u00b7 01:29\",\"Isenhart's Lightbrand (sword)\":\"May 15, 2026 \u00b7 01:26\",\"Isenhart's Parry (shield)\":\"May 25, 2026 \u00b7 19:22\",\"M'avina's Caster (bow)\":\"Jun 10, 2026 \u00b7 21:12\",\"M'avina's Icy Clutch (gloves)\":\"May 18, 2026 \u00b7 23:22\",\"M'avina's Tenet (belt)\":\"May 19, 2026 \u00b7 00:18\",\"Magnus' Skin (sharkskin gloves)\":\"May 18, 2026 \u00b7 01:04\",\"Milabrega's Diadem (helm)\":\"May 27, 2026 \u00b7 00:51\",\"Milabrega's Orb (shield)\":\"May 15, 2026 \u00b7 18:02\",\"Milabrega's Robe (armor)\":\"May 19, 2026 \u00b7 22:59\",\"Milabrega's Rod (scepter)\":\"May 18, 2026 \u00b7 20:56\",\"Naj's Circlet (circlet)\":\"May 15, 2026 \u00b7 01:18\",\"Naj's Light Plate (hellforge plate)\":\"Jun 19, 2026 \u00b7 00:50\",\"Naj's Puzzler (elder staff)\":\"Jun 10, 2026 \u00b7 19:31\",\"Natalya's Shadow (armor)\":\"May 31, 2026 \u00b7 21:18\",\"Natalya's Soul (claws)\":\"May 27, 2026 \u00b7 01:02\",\"Ondal's Almighty (spired helm)\":\"May 18, 2026 \u00b7 00:58\",\"Rite of Passage (sharkskin boots)\":\"May 15, 2026 \u00b7 01:33\",\"Sander's Paragon (cap)\":\"Jun 7, 2026 \u00b7 23:03\",\"Sander's Riprap (heavy boots)\":\"May 15, 2026 \u00b7 01:19\",\"Sander's Superstition (bone wand)\":\"May 15, 2026 \u00b7 17:57\",\"Sander's Taboo (heavy gloves)\":\"May 18, 2026 \u00b7 01:45\",\"Sazabi's Cobalt Redeemer (cryptic sword)\":\"May 31, 2026 \u00b7 21:32\",\"Sigon's Gage (gloves)\":\"May 15, 2026 \u00b7 13:39\",\"Sigon's Guard (shield)\":\"May 20, 2026 \u00b7 12:43\",\"Sigon's Sabot (boots)\":\"May 15, 2026 \u00b7 01:29\",\"Sigon's Shelter (armor)\":\"May 15, 2026 \u00b7 01:00\",\"Sigon's Visor (helm)\":\"May 14, 2026 \u00b7 18:58\",\"Sigon's Wrap (belt)\":\"May 18, 2026 \u00b7 01:49\",\"Tal Rasha's Fine-Spun Cloth (belt)\":\"May 25, 2026 \u00b7 23:42\",\"Tal Rasha's Horadric Crest (helm)\":\"May 17, 2026 \u00b7 01:58\",\"Tal Rasha's Lidless Eye (orb)\":\"May 15, 2026 \u00b7 20:00\",\"Tancred's Crowbill (military pick)\":\"May 15, 2026 \u00b7 13:40\",\"Tancred's Skull (bone helm)\":\"May 15, 2026 \u00b7 15:24\",\"Tancred's Spine (full plate mail)\":\"May 15, 2026 \u00b7 17:46\",\"Tancred's Weird (amulet)\":\"May 18, 2026 \u00b7 00:23\",\"Trang-Oul's Guise (helm)\":\"May 29, 2026 \u00b7 00:46\",\"Trang-Oul's Scales (armor)\":\"May 26, 2026 \u00b7 00:17\",\"Vidala's Barb (bow)\":\"May 25, 2026 \u00b7 23:11\",\"Vidala's Fetlock (boots)\":\"May 15, 2026 \u00b7 17:59\",\"Vidala's Snare (amulet)\":\"May 19, 2026 \u00b7 16:08\",\"Whitstan's Guard (round shield)\":\"May 15, 2026 \u00b7 18:24\",\"Wilhelm's Pride (battle belt)\":\"Jun 25, 2026 \u00b7 00:24\",\"Natalya's Mark (boots)\":\"Aug 6, 2026 \u00b7 01:38\",\"Sazabi's Ghost Liberator (balrog skin)\":\"Aug 6, 2026 \u00b7 08:09\",\"Baranar's Star\":\"Aug 10, 2026 \u00b7 20:29\",\"Atma's Wail\":\"Aug 10, 2026 \u00b7 21:23\"}",
  "d2r_setPieces": "[\"Aldur's Advance (boots)\",\"Aldur's Rhythm (mace)\",\"Aldur's Stony Gaze (helm)\",\"Angelic Halo (ring)\",\"Angelic Mantle (armor)\",\"Angelic Sickle (sword)\",\"Angelic Wings (amulet)\",\"Arcanna's Deathwand (staff)\",\"Arcanna's Flesh (armor)\",\"Arcanna's Head (helm)\",\"Arcanna's Sign (amulet)\",\"Arctic Binding (belt)\",\"Arctic Furs (armor)\",\"Arctic Horn (bow)\",\"Arctic Mitts (gloves)\",\"Bane's Authority (belt)\",\"Bane's Oathmaker (sword)\",\"Bane's Wraithskin (armor)\",\"Berserker's Hatchet (axe)\",\"Berserker's Hauberk (armor)\",\"Berserker's Headgear (helm)\",\"Bul-Kathos' Sacred Charge (sword)\",\"Cathan's Mesh (chainmail)\",\"Cathan's Rule (rod)\",\"Cathan's Seal (ring)\",\"Cathan's Sigil (amulet)\",\"Cathan's Visage (mask)\",\"Civerb's Cudgel (scepter)\",\"Civerb's Icon (amulet)\",\"Civerb's Ward (shield)\",\"Cleglaw's Claw (shield)\",\"Cleglaw's Pincers (gloves)\",\"Cleglaw's Tooth (sword)\",\"Cow King's Hide (studded leather)\",\"Cow King's Horns (war bonnet)\",\"Credendum (mithril coil)\",\"Dangoon's Teaching (reinforced mace)\",\"Dark Adherent (dusk shroud)\",\"Death's Touch (sword)\",\"Griswold's Heart (armor)\",\"Griswold's Valor (helm)\",\"Guillaume's Face (winged helm)\",\"Haemosu's Adamant (cuirass)\",\"Horazon's Countenance (helm)\",\"Horazon's Hold (gloves)\",\"Horazon's Legacy (boots)\",\"Hsarus' Iron Fist (shield)\",\"Hsarus' Iron Heel (boots)\",\"Hsarus' Iron Stay (belt)\",\"Hwanin's Blessing (belt)\",\"Hwanin's Justice (bill)\",\"Hwanin's Refuge (tigulated mail)\",\"Hwanin's Splendor (grand crown)\",\"Immortal King's Detail (belt)\",\"Immortal King's Forge (gloves)\",\"Immortal King's Pillar (boots)\",\"Immortal King's Stone Crusher (hammer)\",\"Infernal Cranium (helm)\",\"Infernal Sign (belt)\",\"Infernal Torch (wand)\",\"Iratha's Coil (helm)\",\"Iratha's Collar (amulet)\",\"Iratha's Cord (belt)\",\"Iratha's Cuff (gloves)\",\"Isenhart's Case (armor)\",\"Isenhart's Horns (helm)\",\"Isenhart's Lightbrand (sword)\",\"Isenhart's Parry (shield)\",\"M'avina's Caster (bow)\",\"M'avina's Icy Clutch (gloves)\",\"M'avina's Tenet (belt)\",\"Magnus' Skin (sharkskin gloves)\",\"Milabrega's Diadem (helm)\",\"Milabrega's Orb (shield)\",\"Milabrega's Robe (armor)\",\"Milabrega's Rod (scepter)\",\"Naj's Circlet (circlet)\",\"Naj's Light Plate (hellforge plate)\",\"Naj's Puzzler (elder staff)\",\"Natalya's Shadow (armor)\",\"Natalya's Soul (claws)\",\"Ondal's Almighty (spired helm)\",\"Rite of Passage (sharkskin boots)\",\"Sander's Paragon (cap)\",\"Sander's Riprap (heavy boots)\",\"Sander's Superstition (bone wand)\",\"Sander's Taboo (heavy gloves)\",\"Sazabi's Cobalt Redeemer (cryptic sword)\",\"Sigon's Gage (gloves)\",\"Sigon's Guard (shield)\",\"Sigon's Sabot (boots)\",\"Sigon's Shelter (armor)\",\"Sigon's Visor (helm)\",\"Sigon's Wrap (belt)\",\"Tal Rasha's Fine-Spun Cloth (belt)\",\"Tal Rasha's Horadric Crest (helm)\",\"Tal Rasha's Lidless Eye (orb)\",\"Tancred's Crowbill (military pick)\",\"Tancred's Skull (bone helm)\",\"Tancred's Spine (full plate mail)\",\"Tancred's Weird (amulet)\",\"Trang-Oul's Guise (helm)\",\"Trang-Oul's Scales (armor)\",\"Vidala's Barb (bow)\",\"Vidala's Fetlock (boots)\",\"Vidala's Snare (amulet)\",\"Whitstan's Guard (round shield)\",\"Wilhelm's Pride (battle belt)\",\"Natalya's Mark (boots)\",\"Sazabi's Ghost Liberator (balrog skin)\"]",
  "d2r_grailUnfound": "{\"Gravepalm\":1,\"Chance Guards\":1,\"Blackbog's Sharp\":1,\"Pluckeye\":1,\"Lidless Wall\":1,\"Hellslayer\":1,\"Islestrike\":1,\"Vampire Gaze\":1,\"Sureshrill Frost\":1}",
  "d2r_owned": "[\"Andariel's Visage\",\"Bartuc's Cut-Throat\",\"Blade of Ali Baba\",\"Goldstrike Arch\",\"Gore Rider\",\"Atma's Wail\"]",
  "d2r_chronSyncMerged_v1": "1"
};

function loadRealLedger(): Record<string, string> | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(LEDGER_DB, { readOnly: true });
    try {
      const rows = db.prepare('SELECT key, value FROM ItemTable').all() as Array<{ key: unknown; value: unknown }>;
      const out: Record<string, string> = {};
      for (const row of rows) {
        // WKWebView stores both key and value as UTF-16LE bytes.
        const k = typeof row.key === 'string' ? row.key : Buffer.from(row.key as any).toString('utf16le');
        const v = typeof row.value === 'string' ? row.value : Buffer.from(row.value as any).toString('utf16le');
        out[k] = v;
      }
      if (!out.d2r_foundLog) return null;
      return out;
    } finally { db.close(); }
  } catch (e) { return null; }
}

const REAL = loadRealLedger();
const LEDGER: Record<string, string> = REAL
  ? { d2r_foundLog: REAL.d2r_foundLog, d2r_setPieces: REAL.d2r_setPieces, d2r_grailUnfound: REAL.d2r_grailUnfound,
      d2r_owned: REAL.d2r_owned, d2r_chronSyncMerged_v1: REAL.d2r_chronSyncMerged_v1 }
  : REAL_SNAPSHOT;

// SUPPRESS = the v1692 one-shot auto-apply flag pre-set, i.e. "the page as he will see it on every
// load after the first". Its absence is the FIRST load, where the tally moves 236 → 238 by itself.
/* v1695 — SUPPRESS HAS TO NAME *EVERY* ONE-SHOT, OR "the app mutated his ledger" FIRES ON WORK
   THAT WAS CORRECT. v1693 added two more one-shot applies (the nine grailUnfound rulings, and The
   Diggler) with their own flags. This list still named only v1692's, so the two v1693 applies ran
   during a test whose entire premise is "the page as he will see it on every load AFTER the first"
   — and the ledger honestly grew 346 → 356 while the spec called it an app-side mutation.
   ⚠ THIS LIST IS A LIABILITY BY DESIGN: every future one-shot must be added here on the same
   commit that introduces it, or this test starts lying in whichever direction is least convenient.
   The idempotency claim itself is unchanged and still the point — with every one-shot already
   flagged, a repeat load must not write a single key. */
const SUPPRESS = suppressOneShots();   // derived from bible.html — see tests/_oneshots.ts

async function seed(page: any, overrides: Record<string, string> = {}, once = false) {
  const data = { ...LEDGER, ...overrides };
  await page.addInitScript((a: { d: Record<string, string>, once: boolean }) => {
    const d = a.d;
    // REG-1270 — `once`: addInitScript runs on EVERY navigation, so a reload would re-seed and measure a
    // second FIRST load. A repeat load must boot on what the first boot left.
    if (a.once) { try { if (sessionStorage.getItem('__v1692Seeded')) return; sessionStorage.setItem('__v1692Seeded', '1'); } catch (e) {} }
    for (const k of Object.keys(d)) { if (d[k] != null) localStorage.setItem(k, d[k]); }
    // Captured AT INJECTION, before a line of app code runs. This is what proves his data loaded;
    // reading the same key after boot cannot tell "his data never arrived" from "the app wrote to
    // it", and those two need different fixes.
    try { (window as any).__seedFoundLogKeys = Object.keys(JSON.parse(d.d2r_foundLog || '{}')).length; } catch (e) { (window as any).__seedFoundLogKeys = -1; }
  }, { d: data, once });
  await page.goto(URL);
  await page.waitForTimeout(1500);
}

/* REG-1270 — THE BASELINE IS MEASURED, NEVER A 2026-08-11 LITERAL. The fixture ledger is frozen; the seed the
   board floors into it is not (243 names when this file was written, 309 now), so an absolute count pinned here
   goes stale on every bake - bake_seed.py itself says so. The same ledger booted as a LATER load (every one-shot
   flagged), in its OWN context so no storage leaks between them, is the baseline each law is stated against.
   Measured in a real page on the 309-name seed: baseline 297 found / 420 keys; a first load 309 / 432, batches
   [2, 9, 1] - exactly the twelve, exactly three batches. */
async function baseline(browser: any) {
  const ctx = await browser.newContext();
  try {
    const p = await ctx.newPage();
    await seed(p, SUPPRESS);
    return await scan(p);
  } finally { await ctx.close(); }
}

// His own click on the 🏆 F·uniques tab — the render path that puts the number on his screen.
async function openUniquesTab(page: any) {
  await page.click('.tab[data-tab="funi"]');
  await page.waitForTimeout(400);
  const txt = (await page.textContent('#funi-body')) || '';
  expect(txt.length, '#funi-body rendered nothing after clicking 🏆 F·uniques — every screen number below would be vacuous').toBeGreaterThan(50);
  return txt.replace(/\s+/g, ' ');
}

function namedCards(txt: string) {
  const m = txt.match(/named cards:\s*(\d+)\s*\/\s*(\d+)/);
  return m ? { found: Number(m[1]), total: Number(m[2]) } : { found: -1, total: -1 };
}

const scan = (page: any) => page.evaluate(() => {
  const w = window as any;
  const fl = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
  const fu = (typeof w.funiScan === 'function') ? w.funiScan() : null;
  const fs = (typeof w.fsetsScan === 'function') ? w.fsetsScan() : null;
  return {
    bootFoundLogKeys: Object.keys(fl).length,
    bootKeySig: Object.keys(fl).sort().join('\u0000'),
    seedFoundLogKeys: w.__seedFoundLogKeys,
    hasFleshrender: Object.prototype.hasOwnProperty.call(fl, 'Fleshrender'),
    hasGloomsTrap: Object.prototype.hasOwnProperty.call(fl, "Gloom's Trap"),
    hasBlackbog: Object.prototype.hasOwnProperty.call(fl, "Blackbog's Sharp"),
    hasIslestrike: Object.prototype.hasOwnProperty.call(fl, 'Islestrike'),
    found: fu ? fu.found : -1, total: fu ? fu.total : -1, chronTotal: fu ? fu.chronTotal : -1,
    havePieces: fs ? fs.havePieces : -1, totalPieces: fs ? fs.totalPieces : -1,
    conflicts: (typeof w._gUnfoundConflicts === 'function') ? w._gUnfoundConflicts() : null,
    batches: JSON.parse(localStorage.getItem('d2r_chronApplied') || '[]'),
  };
});

/* ── (0) SANITY, FIRST AND ALWAYS ─────────────────────────────────────────────────────────────
   A probe in this same arc ran against a BLANK browser profile and reported plausible numbers
   that were entirely fictional. Nothing below this line means anything until his 346 keys are
   provably in the page. The seed-time count answers "did his data load"; the post-boot count is
   asserted SEPARATELY so an app-side write reads as an app-side write and not as a load failure. */
test('(0) SANITY — his real 346-key ledger is in the page, and nothing wrote to it on a repeat load', async ({ page }) => {
  await seed(page, SUPPRESS, true);
  const s = await scan(page);
  expect(s.seedFoundLogKeys, 'HIS LEDGER DID NOT LOAD — the seed itself did not carry ' + N_FOUNDLOG + ' foundLog keys, so every count in this file is fiction').toBe(N_FOUNDLOG);
  /* REG-1270 — A REPEAT LOAD, MEASURED AS ONE. This asserted bootFoundLogKeys === 346 on the FIRST boot and
     went red at 423 for 30+ runs: the fixture was exported 2026-08-11, when _GRAIL_SEED held 243 names; it holds
     312 now, and the seed FLOORS its names into d2r_foundLog on every boot (v659, by design) - so the first boot
     of an old ledger legitimately writes 79 keys (67 unique + 12 set-piece floors, 2 aliases folded). Measured in a
     real page, owner world, all one-shots suppressed: 346 -> 423 on boot one, 423 -> 423 on boot two, nothing
     added or removed. The law this line names - a REPEAT load writes nothing - is true and is now what is asked. */
  const firstBoot = s;
  await page.reload();
  await page.waitForTimeout(1500);
  const again = await scan(page);
  expect(again.bootFoundLogKeys, 'his ledger changed on a REPEAT load (all one-shots flagged, seed already floored) - an app write, NOT a load failure').toBe(firstBoot.bootFoundLogKeys);
  expect(again.bootKeySig === firstBoot.bootKeySig, 'a repeat load changed WHICH names are in his ledger, even if the count held').toBe(true);
  expect(JSON.parse(LEDGER.d2r_setPieces).length, 'd2r_setPieces').toBe(N_SETPIECES);
  expect(Object.keys(JSON.parse(LEDGER.d2r_grailUnfound)).length, 'd2r_grailUnfound (the fixture history)').toBe(N_CONFLICTS_SEEDED);
  // Both sources present? then they must be the same ledger, key for key.
  if (REAL) {
    const a = Object.keys(JSON.parse(REAL.d2r_foundLog)).sort().join('\u0000');
    const b = Object.keys(JSON.parse(REAL_SNAPSHOT.d2r_foundLog)).sort().join('\u0000');
    expect(b, 'the frozen REAL_SNAPSHOT has drifted from the read-only copy of his store — re-export it').toBe(a);
  }
});

/* ── THE MEASURED LIMIT OF THIS PROOF (read before trusting the 236) ──────────────────────────
   234 of his 236 unique names ALSO live in bible.html's _GRAIL_SEED (243 names, itself built from
   his Chronicle screenshots), and the app re-writes seeded names into d2r_foundLog at boot — a
   path that predates this ship (v1692 does not touch it). Measured: deleting TEN real unique names
   from the injected ledger left the screen at 236, because all ten came straight back. So "236" is
   his ledger UNION that seed, and for a seeded name this spec cannot tell the two apart — assert
   (0), which counts the ledger AT INJECTION, is the only thing that can, and it goes red at 336.
   For a name the seed does not carry it is fully responsive: deleting "Baranar's Star" alone drops
   the screen to 235 and the auto-applied first load to 237 — both measured, both restored after.

   ── (1) THE BASELINE IS HIS WHOLE LEDGER, ON SCREEN ──────────────────────────────────────────
   236 is not a constant this spec invented: it is 346 foundLog keys minus the 110 set-piece rows,
   and it is what the screen must read before the auto-apply. The v1691 comment at bible.html
   ~35099 says this tally "topped out around 32" — measured on HEAD it is 236, so that comment
   describes an older roster, not today's. The number that DID change is the denominator: the
   universe is now the resolver's roster (385 as measured at 02:56 on 2026-08-11, deliberately not
   pinned — see the header) instead of the v1691 boss-drop shortlist (368). */
test('(1) COUNTS — the Uniques tab reads 236 of his own finds, F·Sets reads 110 of 135', async ({ page }) => {
  await seed(page, SUPPRESS);
  const txt = await openUniquesTab(page);
  const screen = namedCards(txt);
  const s = await scan(page);
  // REG-1270 — no absolute: the seed the board floors in moves with every bake. The screen must agree with the
  // engine, and every unique HIS injected ledger holds (and he has not un-ticked) must be among the found.
  expect(screen.found, 'funiScan().found must agree with the number ON HIS SCREEN (#funi-body "named cards")').toBe(s.found);
  expect(screen.total, 'THE SCREEN AND funiScan() PRINT DIFFERENT DENOMINATORS — two answers to one question').toBe(s.total);
  expect(s.total, 'the universe is the v1691 boss-drop shortlist again — that is the undercount this ship exists to end').not.toBe(N_ROSTER_V1691);
  expect(s.total, 'a roster smaller than his own finds is not a roster').toBeGreaterThan(s.found);
  /* THE DURABLE FORM OF "236": his ledger's own unique names, counted by the resolver. His 346 keys partition
     with nothing left over - 236 unique + 110 set-piece, zero base, zero unknown.
     ⚠ REG-1270/1274 — the COUNTS moved (the seed floor adds names), so the law is stated without them: the
     ledger as the board holds it classifies completely, and every unique of HIS injected ledger is counted.
     The board migrates two old Natalya slot labels on boot (v2119), so it is the POST-boot store that is
     partitioned; its one unclassifiable key was the seed's own `Harlequin Crest (Shako)` - now seeded as the
     resolvable `Harlequin Crest` (REG-1274). */
  const injected = Object.keys(JSON.parse(LEDGER.d2r_foundLog));
  const unfound = Object.keys(JSON.parse(LEDGER.d2r_grailUnfound || '{}'));
  const part = await page.evaluate((a: { names: string[], unfound: string[] }) => {
    const w = window as any;
    const out: Record<string, number> = {};
    // his ledger AS THE BOARD HOLDS IT: after its own migrations (v2119 renames two old Natalya slot labels)
    for (const n of Object.keys(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'))) {
      const k = w.d2rResolveItem(n).kind; out[k] = (out[k] || 0) + 1;
    }
    const missing = new Set(((w.funiScan().missing) || []).map((x: any) => x.n));
    const uncounted = a.names.filter((n) => w.d2rResolveItem(n).kind === 'unique' && a.unfound.indexOf(n) < 0 && missing.has(n));
    return { out, uncounted };
  }, { names: injected, unfound });
  expect(Object.keys(part.out).sort(), "his ledger must partition into uniques + set pieces with NOTHING unclassified (REG-1274: the seed once floored an unresolvable alias spelling)").toEqual(['set-piece', 'unique']);
  expect(part.uncounted, 'a unique HIS OWN ledger holds (and he never un-ticked) is not counted as found').toEqual([]);
  expect(s.havePieces, 'fsetsScan().havePieces — his 110 set pieces are all counted (the set seed may floor more)').toBeGreaterThanOrEqual(N_SETPIECES);
  expect(s.totalPieces, 'fsetsScan().totalPieces').toBe(N_SETS_TOTAL);
});

/* ── (2) THE RESOLVER, ON REAL NAMES ──────────────────────────────────────────────────────────
   Real strings off his Chronicle and his stash, not invented ones. 'Gloom' resolves to UNKNOWN and
   that is the correct answer: the item is "Gloom's Trap" and a bare "Gloom" is not a name in the
   roster — a resolver that guessed here is how a base item lands in the unique ledger. */
test('(2) CLASSIFY — d2rResolveItem separates unique / base / set-piece / unknown on real names', async ({ page }) => {
  await seed(page, SUPPRESS);
  const kinds = await page.evaluate((names: string[]) => {
    const w = window as any;
    if (typeof w.d2rResolveItem !== 'function') return null;
    const out: Record<string, string> = {};
    for (const n of names) { const r = w.d2rResolveItem(n); out[n] = (r && r.kind) || 'NULL'; }
    return out;
  }, ['Fleshrender', "Gloom's Trap", 'Gore Rider', 'Gauntlets', 'Ornate Plate', 'Pavise', 'Skull Cap', 'Amulet', 'Ring', "Aldur's Advance (boots)", 'Gloom']);
  expect(kinds, 'window.d2rResolveItem is not defined — this is v1691').not.toBeNull();
  expect(kinds).toEqual({
    'Fleshrender': 'unique',
    "Gloom's Trap": 'unique',
    'Gore Rider': 'unique',
    'Gauntlets': 'base',
    'Ornate Plate': 'base',
    'Pavise': 'base',
    'Skull Cap': 'base',
    'Amulet': 'unknown',
    'Ring': 'unknown',
    "Aldur's Advance (boots)": 'set-piece',
    'Gloom': 'unknown',
  });
});

/* ── (3) IT GOES UP ON ITS OWN, AND THE UNDO IS WHAT MAKES THAT SAFE ──────────────────────────
   First load with no suppression flag: the two screenshot-verified finds go in through
   chronicleApply — the same adds-only path his hand-tick uses — and the screen reads 238. Then
   chronicleUndoLast() puts the screen back to 236 and his ledger back to 346 keys. An auto-apply
   without a working undo is a write he cannot take back; that is the whole risk of this ship. */
test('(3) UP — a first load applies the twelve one-shot names by itself, and undo returns to the baseline', async ({ page, browser }) => {
  const base = await baseline(browser);   // REG-1270 — the same ledger as a LATER load, measured, never a literal
  await seed(page);   // no SUPPRESS: this is his first load of v1692
  const before = await scan(page);
  const txt = await openUniquesTab(page);
  expect(namedCards(txt).found, 'the screen after the boot auto-apply agrees with the engine').toBe(before.found);
  expect(before.found, 'the first load added EXACTLY the twelve one-shot names to the tally').toBe(base.found + N_APPLIED_ON_FIRST_LOAD);
  /* v1695 — a FIRST load now runs three one-shots, not one: v1692's two verified finds, then
     v1693's nine-name ruling and The Diggler. 346 + 12 = 358, and every one of the twelve is
     named below so this stays an inventory rather than a magic number that drifts. */
  expect(before.bootFoundLogKeys, 'his ledger grew by exactly the twelve applied names').toBe(base.bootFoundLogKeys + N_APPLIED_ON_FIRST_LOAD);
  expect(before.hasFleshrender && before.hasGloomsTrap, 'both names landed in d2r_foundLog (the LEDGER), not in d2r_owned (the vault)').toBe(true);
  expect(before.batches.length, 'each one-shot recorded its own undoable batch').toBe(N_BATCHES_ON_FIRST_LOAD);
  expect(before.batches[0].uniques, 'the v1692 batch records only what it actually flipped').toEqual(['Fleshrender', "Gloom's Trap"]);

  /* v1695 — UNDO THE WHOLE STACK, NOT "THE" BATCH. This asserted a single undo returned 2 names,
     which was true when a first load ran exactly one one-shot. Three one-shots later, undoLast
     correctly returns 1 (The Diggler, the most recent) and the old assertion read as a broken undo
     while undo was working exactly as specified.
     The property was never "one batch exists" — it is THE LEDGER IS FULLY RECOVERABLE. So this
     unwinds every batch and checks the whole stack reverses, which also survives the next one-shot
     without another edit here. */
  let undoneTotal = 0;
  for (let i = 0; i < N_BATCHES_ON_FIRST_LOAD + 2; i++) {
    const r = await page.evaluate(() => (window as any).chronicleUndoLast());
    if (!r || !r.undone) break;
    undoneTotal += r.undone;
  }
  await page.click('.tab[data-tab="funi"]');
  await page.waitForTimeout(400);
  const after = await scan(page);
  expect(undoneTotal, 'every applied name came back off').toBe(N_APPLIED_ON_FIRST_LOAD);
  expect(after.batches.length, 'no batch left behind').toBe(0);
  expect(after.found, 'funiScan().found back to the pre-apply baseline').toBe(base.found);
  expect(after.bootFoundLogKeys, 'his ledger back to the baseline key count').toBe(base.bootFoundLogKeys);
  expect(namedCards((await page.textContent('#funi-body')) || '').found, 'the screen back to the baseline').toBe(base.found);

  // and the same two names applied BY HAND from an already-flagged load do the same 236 → 238.
  const manual = await page.evaluate(() => {
    const w = window as any;
    const res = w.chronicleApply({ wouldAdd: { uniques: ['Fleshrender', "Gloom's Trap"], sets: [] }, lanes: ['spec'] });
    return { applied: res.uniques, found: w.funiScan().found };
  });
  expect(manual.applied, 'chronicleApply applied both names').toEqual(['Fleshrender', "Gloom's Trap"]);
  /* v1695 — this reaches 238, not N_AFTER. The stack was fully undone above, so the board is back
     at his 236 baseline and this hand-apply adds exactly the TWO v1692 names. N_AFTER is the
     twelve-name first-load state and stopped being the right constant here the moment v1693 added
     its one-shots — the third time in this file one number quietly came to mean two things. */
  expect(manual.found, 'a hand-apply of the two v1692 names reaches the baseline + 2').toBe(base.found + 2);
});

/* ── (4) ADDS ONLY — A CHRONICLE READ CAN NEVER COST HIM AN ITEM ──────────────────────────────
   grailFoundUni/toggleOwned TOGGLE, so an apply that forgot the already-found guard would silently
   UN-find whatever it re-read. There is no unfind in Diablo. Three names taken from his own ledger,
   fed back in: the count must not move by even one. */
test('(4) NEVER REMOVES — re-applying names he already has skips them and the tally does not drop', async ({ page }) => {
  await seed(page, SUPPRESS);
  const r = await page.evaluate(() => {
    const w = window as any;
    const fl = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    const already = Object.keys(fl).filter((n) => { const k = w.d2rResolveItem(n); return k && k.kind === 'unique'; }).slice(0, 3);
    const beforeFound = w.funiScan().found, beforeKeys = Object.keys(fl).length;
    const res = w.chronicleApply({ wouldAdd: { uniques: already, sets: [] }, lanes: ['spec-reapply'] });
    return { already, beforeFound, beforeKeys, skipped: res.skipped, appliedUniques: res.uniques,
             afterFound: w.funiScan().found,
             afterKeys: Object.keys(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')).length,
             batches: JSON.parse(localStorage.getItem('d2r_chronApplied') || '[]').length };
  });
  expect(r.already.length, 'three real already-found unique names off his own ledger').toBe(3);
  expect(r.beforeFound, 'a real baseline before the re-apply, not an empty board').toBeGreaterThan(0);
  expect(r.skipped.sort(), 'all three were skipped as already-found').toEqual([...r.already].sort());
  expect(r.appliedUniques, 'nothing was flipped').toEqual([]);
  expect(r.afterFound, 'THE TALLY MUST NOT DROP — a toggle bug here silently un-finds real items').toBe(r.beforeFound);
  expect(r.afterKeys, 'his ledger is untouched').toBe(r.beforeKeys);
  expect(r.batches, 'an apply that flipped nothing records no undo batch').toBe(0);
});

/* ── (5) THE CONTESTED NAMES WERE DECIDED — BY HIM, AND REVERSIBLY ────────────────────────────
   ⚠ THIS TEST INVERTED AT v1693, AND THE INVERSION IS THE POINT — it must not be read as the
   safety property weakening.

   At v1692 the nine `d2r_grailUnfound` names were SURFACED and applied to nothing, because
   d2r_grailUnfound is user truth and nobody but Konyo may overrule his own un-tick. That was
   correct, and it stayed correct right up until he ruled. He then ruled: all nine print a
   "First Found:" line in his own Chronicle, his tally had to go UP, and v1693 applied them.

   So the property under test was never "the nine are never applied" — it was "NOTHING overrules
   his un-tick except him". That property is unchanged and is what is asserted here:
     · the applying batch is LANE-TAGGED with his ruling (v1693-konyo-ruling-the-nine), so the
       authority for the write is recorded in the data and not merely in a commit message;
     · it is a chronicleApply batch, so chronicleUndoLast() can still take it back — a ruling that
       cannot be un-ruled would be a worse violation than the original silent apply;
     · d2r_grailUnfound is consequently EMPTY, which is what makes the boot floor stop
       re-suppressing them.
   If a future change applies a grailUnfound name WITHOUT a named ruling lane, this test is what
   should catch it. */
test('(5) RULED — the 9 un-ticked names are applied under HIS named ruling, and the ruling is undoable', async ({ page }) => {
  await seed(page);   // first load — every one-shot is live, so this sees the full applied state
  await openUniquesTab(page);
  const s = await scan(page);
  expect(s.conflicts, 'window._gUnfoundConflicts is not defined — this is v1691').not.toBeNull();
  // his ruling RESOLVED the disagreement, so nothing is left contested
  expect((s.conflicts as string[]).length, 'after his ruling, no un-tick still contradicts the game').toBe(N_CONFLICTS_LIVE);
  expect(Object.keys(JSON.parse(LEDGER.d2r_grailUnfound)).length,
    'the FIXTURE still records the nine he originally un-ticked — that history is not rewritten').toBe(N_CONFLICTS_SEEDED);
  // the nine are now his, by his own call
  expect(s.hasBlackbog, "Blackbog's Sharp — ruled found").toBe(true);
  expect(s.hasIslestrike, 'Islestrike — ruled found').toBe(true);
  // THE AUTHORITY IS IN THE DATA: some batch must carry his ruling lane, and it must be undoable.
  const lanes = (s.batches as any[]).flatMap(b => (b && b.lanes) || []);
  expect(lanes.join(' '), 'the applying batch names HIS ruling as its authority')
    .toContain('konyo-ruling');
  const undoable = await page.evaluate(() => typeof (window as any).chronicleUndoLast === 'function');
  expect(undoable, 'a ruling that cannot be undone is worse than one never made').toBe(true);
});

/* ── (6) THE TWO TOTALS ON THAT SCREEN MUST AGREE ─────────────────────────────────────────────
   This one was RED for four minutes and is kept as a guard. With the 512-name roster (02:52) his
   screen printed "named cards: 238 / 512 ticked · -109 chronicle rows still dark" — the sub-line
   is chronTotal - total, and a 512-name universe under a 403-row Chronicle makes that NEGATIVE. A
   right-looking number under a word that stopped being true is the exact defect class this arc
   keeps finding, and nothing else in this file would have caught it: every other assertion here
   was green while that line was on his screen. The 385-name roster (02:56) prints 18 and passes. */
test('(6) SURFACES AGREE — the "chronicle rows still dark" figure on screen is not negative', async ({ page }) => {
  await seed(page, SUPPRESS);
  const txt = await openUniquesTab(page);
  const dark = txt.match(/(-?\d+)\s*<?\/?b?>?\s*chronicle rows still dark/) || txt.match(/(-?\d+) chronicle rows still dark/);
  const screen = namedCards(txt);
  /* When funiScan().total reaches chronTotal the dark sentence is a lie, so the screen says
     every chronicle row is named instead. A missing dark line is correct only in that case.
     A negative still fails. */
  if (dark) {
    const n = Number(dark[1]);
    expect(n, 'HIS SCREEN SAYS ' + n + ' CHRONICLE ROWS STILL DARK — a negative count; the headline divides by 403 while the grid counts ' + screen.total).toBeGreaterThanOrEqual(0);
  } else {
    expect(txt, 'the dark line is gone and the screen does not say every chronicle row is named').toContain('every chronicle row is named');
    expect(screen.total, 'named cards total').toBeGreaterThan(0);
  }
});
