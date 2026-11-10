/**
 * /api/d2jsp_quote — a public reading of forum gold for one item.
 *
 * The bible cannot read forums.d2jsp.org from the browser (no CORS). This
 * function fetches the board 268 search and returns the middle
 * fg price only when a line that names the item carries an fg number.
 * A challenge page, a login wall, a failed fetch, or a page with no such
 * line returns fg:null. It never substitutes a remembered or default price.
 *
 * Board 268 is D2:R RotW Softcore Trading (non-ladder), the board the search reads (v3843; it was 243, Switch Ladder).
 * Posts still go to board 268. The two are different economies.
 */

const CORS = {
  'Access-Control-Allow-Origin': 'https://bull-4-u.com',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
const BOARD = 268;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      ...CORS,
    },
  });
}

/* ⟦D2JSP QUOTE BEGIN⟧ */
var D2JSP_QUOTE_BOARD = 268;
/* v3843 - ONLY RECENT POSTS PRICE AN ITEM. A price line counts only under a post dated within the last
   D2JSP_QUOTE_WINDOW_DAYS days of the reading (its readAt, else now) - a rolling window, so prices do not stop on
   Jan 1. A page that dates nothing, or only older posts, reads 'no prices' and the desk says unknown. */
var D2JSP_QUOTE_WINDOW_DAYS = 120;
var D2JSP_DAY_MS = 86400000;

/* v3843 - THE D2JSP LEXICON: the trade forum's own short names (its guides' slang and notation, never their prices).
   Each item maps to the words traders write for it; the search asks with the first, and a price line naming any
   form counts. */
var D2JSP_SLANG = {
  "Annihilus": ["anni"], "Hellfire Torch": ["torch"], "Gheed's Fortune": ["gheeds"],
  "Harlequin Crest": ["shako"], "Griffon's Eye": ["gface", "griffons"], "Crown of Ages": ["coa"],
  "Arreat's Face": ["arreats"], "Andariel's Visage": ["andy"], "Herald of Zakarum": ["hoz"],
  "Jalal's Mane": ["jalals"], "Stone of Jordan": ["soj"],
  "Bul-Kathos' Wedding Band": ["bk", "bk ring"], "Raven Frost": ["raven"], "Mara's Kaleidoscope": ["maras"],
  "Highlord's Wrath": ["highlords"], "Crown of Thieves": ["cot"], "Nightwing's Veil": ["nightwing", "veil"],
  "Mang Song's Lesson": ["mang song", "mangs"], "Eschuta's Temper": ["eschutas"], "Death's Fathom": ["fathom"],
  "Call to Arms": ["cta"], "Breath of the Dying": ["botd"], "Heart of the Oak": ["hoto"],
  "Hand of Justice": ["hoj"], "Enigma": ["nigma"], "Infinity": ["infy"], "Insight": [],
  "Grief": [], "Spirit": [], "Heart of Winter": [], "Fortitude": ["forti"],
  "Stormshield": ["storm shield"], "Death's Web": ["deathweb"], "Titan's Revenge": ["titans"],
  "Windforce": ["wf"], "Eaglehorn": [], "War Traveler": ["war travs", "wartravs"], "Waterwalk": [],
  "Sandstorm Trek": ["treks"], "Shadow Dancer": ["sdancer"], "Gore Rider": ["gores"],
  "Steelrend": ["rends"], "Magefist": ["mages"], "Dracul's Grasp": ["dracs"], "Bloodfist": ["bfists"],
  "Chance Guards": ["chancies"], "Arachnid Mesh": ["arach", "arachnid"], "Verdungo's Hearty Cord": ["dungo"],
  "Thundergod's Vigor": ["tgod"], "String of Ears": ["soe"], "Nosferatu's Coil": ["nos", "nosferatus"],
  "The Oculus": ["occy", "oculus"], "Spirit Ward": [],
  "Tyrael's Might": ["tyraels"], "Skullder's Ire": ["skullders"], "Vipermagi": ["viper", "vmagi"],
  "Shaftstop": ["shaft"], "Leviathan": ["levi"], "Guardian Angel": ["ga"], "Blackhorn's Face": ["bhades"],
  "Gladiator's Bane": ["glads"], "Templar's Might": ["templars"], "Atma's Scarab": ["atmas"],
  "Metalgrid": ["mgrid"], "Seraph's Hymn": ["seraphs"],
  "Doombringer": ["doom"], "Death Cleaver": ["dc"], "Executioner's Justice": ["ej"],
  "The Reaper's Toll": ["reapers"], "Stormlash": [], "Tomb Reaver": ["reaver"],
  "Grandfather": ["gf sword"], "Azurewrath": ["azure"], "Lightsabre": ["lsabre"],
  "Hellslayer": [], "Messerschmidt's Reaver": ["messer"], "Rainbow Facet": ["facet"],
  /* v3847 (Elad 15:42) - more of the forum's names; the first word is what the search box is given */
  "Guardian's Thunder": ["guardians thunder", "gt"], "Jeweler's Monarch of Deflecting": ["jmod"],
  "Doom": ["doom rw"], "Chains of Honor": ["coh"], "Phoenix": ["phoenix rw"], "Last Wish": ["lw"], "Faith": [],
  "Beast": [], "Exile": [], "Dream": [], "Fury": [], "Pride": [], "Silence": [],
  "Crescent Moon": ["cmoon"], "Bramble": [], "Destruction": [], "Obedience": ["obe"],
  "Whirlwind": ["ww"], "Vampire Gaze": ["vgaze"], "Wisp Projector": ["wisp"],
  "Dwarf Star": ["dwarf"], "Wizardspike": ["wspike", "spike"],
  "Ondal's Wisdom": ["ondals"], "Lidless Wall": ["lidless"], "Homunculus": ["homu"],
  "Arkaine's Valor": ["arkaines"], "Thunderstroke": ["tstroke"], "Kira's Guardian": ["kiras"],
  "Tal Rasha's Guardianship": ["tal armor"], "Sigon's Complete Steel": ["sigons"],
  "Immortal King's Stone Crusher": ["ik maul"], "Griswold's Honor": ["gris shield"]
};

/* v3847 (Elad 15:42) - A WORD THAT MEANS DIFFERENT ITEMS. Each entry lists its readings in order; a reading is taken
   when its context words are on the line (or in the search), and the LAST reading is the default. A post line whose
   context points at another reading does not count for this item. */
var D2JSP_AMBIG = {
  "doom": [{ item: "Doom", ctx: /\b(?:rw|runeword|cv|voulge|thresher|gt|polearm|pole|merc|eth)\b/ },
           { item: "Doombringer", ctx: /\b(?:sword|champion|unique|db)\b/ }, { item: "Doom", ctx: null }],
  "gt": [{ item: "Doom", ctx: /\b(?:doom|rw|runeword|thresher|polearm|base)\b/ },
         { item: "Guardian's Thunder", ctx: null }],
  "facet": [{ item: "Rainbow Facet", ctx: null }],
  "veil": [{ item: "Nightwing's Veil", ctx: null }],
  "storm": [{ item: "Stormshield", ctx: /\b(?:shield|monarch|ss)\b/ }, { item: "Stormlash", ctx: /\b(?:flail|lash)\b/ },
            { item: "Stormshield", ctx: null }],
  "spike": [{ item: "Wizardspike", ctx: null }],
  "gf": [{ item: "Grandfather", ctx: /\b(?:sword|colossus blade|unique|gfather)\b/ }, { item: null, ctx: null }]
};

/* -> {item, via, ambiguous}: the item a typed or written name means. A full name stays itself; a forum word becomes
   its item; an ambiguous word becomes the reading its context names (else its default). via says how it was read. */
function d2jspResolveItem(text, context) {
  var f = d2jspFoldPrice(text).replace(/[^a-z0-9 \-]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!f) return { item: '', via: 'empty', ambiguous: false };
  var ctx = ' ' + d2jspFoldPrice(context || text).replace(/[^a-z0-9]+/g, ' ') + ' ';
  var head = f.split(' ')[0];                       /* "doom cv": the first word, read by the rest */
  var key = Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, f) ? f : (Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, head) && f !== head ? head : null);
  if (key) {
    var rs = D2JSP_AMBIG[key];
    for (var i = 0; i < rs.length; i++) {
      if (!rs[i].ctx || rs[i].ctx.test(ctx)) return { item: rs[i].item || String(text), via: rs[i].ctx ? 'context' : 'default', ambiguous: rs.length > 1 };
    }
  }
  for (var k in D2JSP_SLANG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k)) continue;
    var kf = d2jspSimpleName(k);
    if (kf === d2jspSimpleName(text)) return { item: k.trim(), via: 'name', ambiguous: false };
    if (D2JSP_SLANG[k].some(function (w) { return w === f; })) return { item: k.trim(), via: 'alias', ambiguous: false };
  }
  /* one edit of one known item: a swapped pair, a missing letter, an extra letter, or one wrong letter.
     "gaurdian's thunder" is Guardian's Thunder. Two known items at the same distance stay as typed. */
  var near = d2jspNearItem(f);
  if (near) return { item: near, via: 'near', ambiguous: false };
  return { item: String(text).trim(), via: 'as typed', ambiguous: false };
}

/* distance above 1 is not a match. An adjacent swap counts as one edit. */
function d2jspEdit(a, b) {
  if (a === b) return 0;
  var n = a.length, m = b.length;
  if (Math.abs(n - m) > 1) return 2;
  var prev2 = [], prev = [], cur = [];
  for (var j = 0; j <= m; j++) prev[j] = j;
  for (var i = 1; i <= n; i++) {
    cur = [];
    cur[0] = i;
    var low = i;
    for (var k = 1; k <= m; k++) {
      var cost = a.charAt(i - 1) === b.charAt(k - 1) ? 0 : 1;
      var v = prev[k] + 1;
      if (cur[k - 1] + 1 < v) v = cur[k - 1] + 1;
      if (prev[k - 1] + cost < v) v = prev[k - 1] + cost;
      if (i > 1 && k > 1 && a.charAt(i - 1) === b.charAt(k - 2) && a.charAt(i - 2) === b.charAt(k - 1)) {
        var swap = prev2[k - 2] + 1;
        if (swap < v) v = swap;
      }
      cur[k] = v;
      if (v < low) low = v;
    }
    if (low > 1) return 2;
    prev2 = prev;
    prev = cur;
  }
  return prev[m] > 1 ? 2 : prev[m];
}

function d2jspNearItem(f) {
  if (!f || f.length < 4) return null;
  var best = '', bestD = 2, ties = 0;
  function consider(item, form) {
    if (!form || form === f) return;
    var d = d2jspEdit(f, form);
    if (d > 1) return;
    if (d < bestD) { best = item; bestD = d; ties = 1; }
    else if (item !== best) ties += 1;
  }
  for (var k in D2JSP_SLANG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k)) continue;
    var name = k.trim();
    consider(name, d2jspFoldPrice(k).replace(/[^a-z0-9 \-]/g, ' ').replace(/\s+/g, ' ').trim());
    consider(name, d2jspSimpleName(k));
    (D2JSP_SLANG[k] || []).forEach(function (w) { consider(name, d2jspFoldPrice(w)); });
  }
  return ties === 1 ? best : null;
}

/* true when a line that names an ambiguous form of itemName points, by a context word on it, at a different item
   (a bare ambiguous word with no context still counts: nothing on the line says otherwise) */
function d2jspOtherReading(line, itemName) {
  var folded = ' ' + d2jspFoldPrice(line).replace(/[^a-z0-9]+/g, ' ') + ' ', me = d2jspSimpleName(itemName);
  for (var w in D2JSP_AMBIG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, w) || folded.indexOf(' ' + w + ' ') < 0) continue;
    if (folded.indexOf(' ' + me + ' ') >= 0) continue;          /* the full name is on the line: no doubt */
    var mine = D2JSP_AMBIG[w].some(function (r) { return r.item && d2jspSimpleName(r.item) === me; });
    if (!mine) continue;
    var r = d2jspResolveItem(w, line);
    if (r.via === 'context' && r.item && d2jspSimpleName(r.item) !== me) return true;   /* only a context word rules it out */
  }
  return false;
}

/* the guides' notation for mods: the short word and the plain words a seller means by it */
var D2JSP_NOTATION = {
  "@": "all resistances", "os": "open sockets", "eth": "ethereal", "ed": "enhanced damage", "dr": "damage reduced",
  "mdr": "magic damage reduced", "fcr": "faster cast rate", "fhr": "faster hit recovery", "frw": "faster run walk",
  "ias": "increased attack speed", "ll": "life leech", "ml": "mana leech", "lpl": "life per level",
  "lpk": "life per kill", "mpk": "mana per kill", "cb": "crushing blow", "gc": "grand charm", "lc": "large charm",
  "sc": "small charm", "perf": "perfect roll", "p": "perfect roll", "upd": "upgraded", "rand": "random roll",
  "unid": "unidentified", "igg": "in game gold", "pc": "poison charm", "pnb": "poison and bone",
  "cr": "cold resist", "fr": "fire resist", "lr": "lightning resist", "pr": "poison resist",
  "mf": "magic find", "gf": "gold find", "rep": "replenish", "res": "resistances", "req": "requirement",
  "str": "strength", "dex": "dexterity", "ar": "attack rating", "def": "defense", "dmg": "damage",
  "ow": "open wounds", "ls": "life stolen", "sorc": "sorceress", "sin": "assassin", "zon": "amazon",
  "barb": "barbarian", "dru": "druid", "nec": "necromancer", "pala": "paladin"
};

/* v3885 (#30, GrokBot's real-post pass) - EACH ITEM'S VARIABLE ROLLS, from the page's own data (tv/d2jsp_rolls.py --emit; a
   law holds this block equal to bible.html's ITEM_CODEX / RUNEWORD_TIP / BASE_DB). Never typed here. */
/* ⟦D2JSP ROLLS BEGIN⟧ */
var D2JSP_ROLLS = {"alma negra":[[5,9],[40,75],[138,164],[180,210]],"andariels visage":[[8,10],[25,30],[100,150],[101,154]],"annihilus":[[5,10],[10,20]],"arachnid mesh":[[55,62],[90,120]],"ariocs needle":[[10,20],[180,230]],"arkaines valor":[[1,2],[10,15],[150,180],[410,517]],"arreats face":[[3,6],[93,120],[150,200]],"astreons iron ward":[[4,7],[150,200],[240,290]],"athenas wrath":[[150,180]],"atlantean":[[200,250]],"atmas wail":[[120,160],[282,303]],"authority":[[40,60]],"azurewrath":[[5,10],[230,270]],"bane ash":[[50,60]],"bartucs cut-throat":[[5,9],[150,200]],"battlebranch":[[50,70],[50,100]],"beast":[[25,40],[240,270]],"bing sz wang":[[130,160]],"black hades":[[30,60],[140,200],[200,250],[315,342]],"blackhorns face":[[54,86],[180,220]],"blackleach blade":[[100,140]],"blackoak shield":[[108,123],[160,200]],"blade of ali baba":[[5,15],[60,120]],"bladebuckle":[[8,11],[80,100]],"blastbark":[[70,130]],"blood ravens charge":[[180,230],[200,300]],"bloodfist":[[5,6],[10,20]],"bloodletter":[[1,3],[2,4]],"bloodmoon":[[7,13],[10,15],[210,260]],"bone":[[100,150]],"boneflame":[[20,30],[100,146],[120,150]],"boneflesh":[[100,120],[108,116]],"bonehew":[[270,320]],"boneshade":[[1,2],[2,3],[4,5]],"boneslayer blade":[[180,220]],"bonesnap":[[200,300]],"brainhew":[[10,13],[50,80]],"bramble":[[25,50]],"brand":[[260,340],[280,330]],"breath of the dying":[[12,15],[350,400]],"bul-kathos wedding band":[[3,5]],"bulwark":[[4,6],[10,15],[75,100]],"buriza-do kyanon":[[75,150],[150,200]],"butchers pupil":[[150,200]],"bverrit keep":[[22,25],[80,100],[80,120]],"call to arms":[[1,4],[1,6],[2,6],[250,290]],"carrion wind":[[6,9],[100,160]],"cerebus bite":[[1,2],[7,10],[60,120],[101,145],[130,140]],"chance guards":[[8,9],[20,30],[25,40]],"chaos":[[290,340]],"chieftain":[[10,20]],"cliffkiller":[[5,10],[20,30],[190,230]],"cloudcrack":[[150,200]],"coif of glory":[[15,18]],"coldkill":[[150,190]],"corpsemourn":[[150,180],[417,450]],"coven":[[1,5],[26,40],[30,50]],"crainte vomir":[[160,200]],"cranebeak":[[20,50],[240,300]],"cranium basher":[[200,240]],"crescent moon":[[3,6],[11,15]],"crow caw":[[150,180],[176,190]],"crown of ages":[[10,15],[20,30],[100,150],[111,165]],"crown of thieves":[[9,12],[78,113],[80,100],[160,200]],"crushflange":[[50,60]],"cure":[[40,60],[75,100]],"darkforce spawn":[[103,148],[140,180]],"darksight helm":[[20,40],[75,84]],"death":[[300,385]],"death cleaver":[[6,9],[230,280]],"deaths fathom":[[15,30],[25,40]],"deaths web":[[7,12],[40,50]],"demon limb":[[7,13],[15,20],[180,230]],"demonhorns edge":[[3,6],[55,77],[111,156],[120,160]],"demons arch":[[6,12],[160,210]],"djinn slayer":[[3,6],[3,7],[100,150],[190,240],[200,300]],"doom":[[40,60],[330,370]],"doombringer":[[5,7],[180,250]],"doomslinger":[[60,100]],"draculs grasp":[[5,10],[7,10],[10,15],[56,65],[90,120]],"dragon":[[3,5]],"dream":[[5,20],[12,25],[20,30],[150,220]],"duress":[[10,20],[150,200]],"duriels shell":[[160,200],[188,202]],"duskdeep":[[10,20],[23,26],[30,50]],"dwarf star":[[12,15]],"earth shifter":[[250,300]],"edge":[[5,10],[320,380]],"endlesshail":[[3,5],[180,220]],"enigma":[[750,775]],"eschutas temper":[[10,20],[20,30]],"eternity":[[260,310]],"ethereal edge":[[5,10],[10,12],[150,180],[150,200],[270,350]],"executioners justice":[[240,290]],"exile":[[220,260]],"eye of etlich":[[1,5],[3,7],[10,40]],"face of horror":[[9,27]],"faith":[[1,2]],"famine":[[320,370]],"felloak":[[70,80]],"firelizards talons":[[1,2],[40,70],[200,270]],"flamebellow":[[5,10],[10,20],[12,18],[20,30],[170,240]],"fleshripper":[[5,10],[200,300]],"flickering flame":[[10,15],[50,75]],"fortitude":[[25,30]],"frostburn":[[10,20],[12,15]],"frostwind":[[7,14],[7,15],[180,230]],"gavel of pain":[[130,160]],"generals tan do li ga":[[50,60]],"gheeds fortune":[[10,15],[20,40],[80,160]],"ghostflame":[[10,15],[190,240]],"ghoulhide":[[4,5],[37,44],[150,190]],"giant skull":[[25,35],[100,157],[250,320]],"gimmershred":[[160,210]],"ginthers rift":[[7,12],[100,150]],"gladiators bane":[[15,20],[150,200],[375,481]],"gloom":[[200,260]],"glooms trap":[[35,40],[120,150]],"gnasher":[[60,70]],"goblin toe":[[9,11],[50,60]],"goldskin":[[120,150],[150,161]],"goldstrike arch":[[100,150],[100,200],[200,250]],"goldwrap":[[40,60],[50,80]],"gore rider":[[43,53],[160,200]],"gorefoot":[[5,6],[20,30]],"grandfather":[[150,250]],"gravenspine":[[25,50]],"gravepalm":[[33,39],[100,200],[140,180]],"greyform":[[8,11]],"grief":[[10,15],[20,25],[30,40],[340,400]],"griffons eye":[[10,15],[15,20],[50,60],[100,200]],"ground":[[10,15],[40,60],[75,100]],"guardian angel":[[180,200],[252,274]],"halaberds reign":[[1,2],[15,23],[114,159],[140,170]],"hand of blessed light":[[130,160]],"hand of broc":[[2,3],[10,20]],"hand of justice":[[280,330]],"harlequin crest":[[98,141]],"harmony":[[2,6],[200,275]],"hawkmail":[[57,60],[80,100]],"head hunters glory":[[5,7],[20,30],[30,40],[158,173],[300,350],[320,420]],"heart carver":[[190,240]],"heart of the oak":[[30,40]],"hearth":[[10,15],[40,60],[75,100]],"heavenly garb":[[90,107]],"heavens light":[[15,20],[250,300]],"hellclap":[[50,75],[70,90]],"hellmouth":[[43,53],[150,200]],"hellrack":[[100,150],[180,230]],"hexfire":[[140,160]],"homunculus":[[58,70],[150,200]],"hone sundan":[[160,200]],"hotspur":[[2,3],[10,20]],"howltusk":[[30,35]],"ice":[[25,30],[140,210]],"iceblink":[[70,80],[90,95]],"impaler":[[140,170]],"infernostride":[[28,35],[40,70],[120,150]],"infinity":[[45,55],[255,325]],"insight":[[1,6],[180,250],[200,260]],"ironstone":[[100,150]],"islestrike":[[170,190]],"jade talon":[[10,15],[40,50],[190,240]],"jade tan do":[[100,150]],"jalals mane":[[73,98],[150,200]],"kingslayer":[[230,270]],"kiras guardian":[[40,50],[50,70],[50,120]],"kuko shakaku":[[150,180]],"lacerator":[[150,210]],"lance guard":[[58,78],[70,120]],"last wish":[[60,70],[330,375]],"lava gout":[[39,47],[150,200]],"lawbringer":[[200,250]],"leviathan":[[15,25],[40,50],[100,150],[170,200],[417,523]],"lidless wall":[[3,5],[50,150],[80,130]],"lightsabre":[[5,7],[150,200]],"lycanders aim":[[5,8],[150,200]],"lycanders flank":[[5,9],[150,200]],"maelstrom":[[1,3]],"magefist":[[9,11],[20,30]],"magewrath":[[9,13],[120,150],[200,250]],"manald heal":[[4,7],[5,8]],"mang songs lesson":[[7,15]],"mania":[[180,200]],"maras kaleidoscope":[[20,30]],"marrowwalk":[[1,2],[10,20],[59,67],[170,200]],"meat scraper":[[150,200]],"metalgrid":[[25,35],[300,350],[400,450]],"metamorphosis":[[50,80]],"minotaur":[[15,20],[140,200]],"mist":[[325,375]],"mosaic":[[8,15],[200,250]],"mosers blessed circle":[[47,55],[180,220]],"nagelring":[[15,30],[50,75]],"natures peace":[[7,11],[20,30]],"nightsmoke":[[30,50]],"nightwings veil":[[5,9],[8,15],[10,20],[90,120],[114,159]],"nords tenderizer":[[2,4],[5,15],[150,180],[270,330]],"nosferatus coil":[[5,7],[56,63]],"oath":[[10,15],[210,340]],"obedience":[[20,30],[200,300]],"obsession":[[15,25],[15,30],[60,70]],"ondals wisdom":[[2,4],[5,8],[40,50],[450,550]],"ormus robes":[[10,15],[10,20],[36,60],[361,467]],"passion":[[50,80],[160,210]],"patriarch":[[100,120]],"pattern":[[40,80]],"peasant crown":[[6,12],[45,53]],"pelta lunata":[[4,6],[8,12],[30,40]],"phoenix":[[15,21],[350,400]],"pierre tombale couant":[[100,200],[160,220]],"plague":[[1,2],[220,320]],"pompeiis wrath":[[140,170]],"pride":[[260,300]],"principle":[[100,150]],"prudence":[[25,35],[140,170]],"pus spitter":[[150,220]],"que-hegans wisdom":[[6,10],[140,160],[225,261]],"rain":[[100,150]],"rattlecage":[[128,135]],"raven claw":[[60,70]],"raven frost":[[15,20],[150,250]],"ravenlore":[[10,20],[15,25],[20,30],[103,155],[120,150]],"razors edge":[[175,225]],"razortail":[[31,36],[120,150]],"reapers toll":[[11,15],[190,240]],"redeemer":[[2,4],[200,250],[250,300]],"ribcracker":[[200,300]],"rift":[[5,10]],"riphook":[[7,10],[180,220]],"ritual":[[3,5],[150,250],[200,260],[250,320]],"rockfleece":[[100,130],[101,105]],"rockstopper":[[20,40],[20,50],[52,62],[160,220]],"rogues bow":[[40,60]],"sanctuary":[[50,70],[130,160]],"sandstorm trek":[[10,15],[40,70],[56,65],[140,170]],"saracens chance":[[15,25]],"schaefers hammer":[[100,130]],"seraphs hymn":[[25,50],[150,250]],"serpent lord":[[30,40]],"shadow dancer":[[15,25],[62,71],[70,100]],"shadow killer":[[10,15],[170,220]],"shaftstop":[[180,220],[198,213]],"silks of the victor":[[100,120],[218,233]],"silkweave":[[37,44],[150,190]],"skin of the flayed one":[[5,7],[15,25],[122,136],[150,190]],"skin of the vipermagi":[[9,13],[20,35],[111,126]],"skullders ire":[[160,200],[225,243]],"skystrike":[[150,200]],"snakecord":[[20,30]],"snowclash":[[37,42],[130,170]],"soul drainer":[[4,7],[59,67],[90,120]],"soulfeast tine":[[150,190],[150,250]],"sparking mail":[[10,14],[72,75],[75,85]],"spellsteel":[[12,15]],"spike thorn":[[15,20],[120,150],[147,163]],"spire of honor":[[150,200]],"spirit":[[3,8],[25,35],[89,112]],"spirit forge":[[120,160],[158,172]],"spirit keeper":[[9,14],[15,25],[30,40],[107,152],[170,190]],"spirit shroud":[[7,11],[102,117]],"spirit ward":[[6,11],[20,30],[30,40],[130,180],[153,170]],"splendor":[[60,100]],"stealskull":[[30,50],[63,72],[200,240]],"steel carapace":[[9,14],[10,15],[40,60],[190,220],[446,557]],"steel pillar":[[50,80],[210,260]],"steel shade":[[4,8],[5,11],[10,18],[100,130],[105,149]],"steelclash":[[15,20],[16,18],[60,100]],"steeldriver":[[150,250]],"steelrend":[[15,20],[30,60],[62,71],[170,210]],"stone":[[250,290]],"stoneraven":[[30,50],[230,280],[400,600]],"stormchaser":[[53,61],[160,220]],"stormguild":[[10,15],[12,14],[50,60]],"stormlash":[[3,9],[240,300]],"stormshield":[[133,148]],"stormspire":[[150,250]],"stormstrike":[[70,90]],"stoutnail":[[3,10]],"string of ears":[[6,8],[10,15],[29,34],[150,180]],"swordguard":[[10,20],[170,180]],"tarnhelm":[[8,11],[25,50]],"tearhaunch":[[12,15],[60,80]],"temper":[[10,15],[40,60],[75,100]],"templars might":[[10,15],[40,50],[170,220],[250,300],[487,600]],"thundergods vigor":[[41,52],[160,200]],"thunderstroke":[[150,200]],"tiamats rebuke":[[25,35],[59,67],[140,200]],"titans revenge":[[5,9],[150,200]],"todesfaelle flamme":[[120,160]],"tomb reaver":[[10,14],[30,50],[50,80],[150,230],[200,280],[250,350]],"toothrow":[[20,40],[40,60],[160,220],[242,258]],"treads of cthon":[[8,9],[30,40]],"twitchthroe":[[32,35]],"tyraels might":[[20,30],[50,100],[120,150],[487,600]],"umbral disk":[[8,10],[10,15],[40,50]],"unbending will":[[8,10],[20,30],[300,350]],"undead crown":[[25,45],[30,60],[50,100]],"valkyrie wing":[[2,4],[85,98],[150,200]],"vampire gaze":[[6,8],[10,15],[15,20],[60,125]],"veil of steel":[[114,159]],"venom grip":[[15,25],[28,35],[130,160]],"venom ward":[[60,100],[65,68]],"verdungos hearty cord":[[10,13],[10,15],[30,40],[58,65],[90,140],[100,120]],"vigilance":[[20,40],[25,35],[75,100]],"vile husk":[[150,200]],"visceratuant":[[41,49],[100,150]],"voice of reason":[[220,350],[355,375]],"void":[[1,3],[8,12],[10,15]],"wall of the eyeless":[[10,30],[30,40]],"war traveler":[[5,10],[30,50],[39,47],[150,190]],"ward":[[30,35],[30,50]],"waterwalk":[[33,39],[45,65],[180,210]],"widowmaker":[[3,5],[150,200]],"wilhelms pride":[[37,42]],"wind":[[120,160]],"windforce":[[6,8]],"windhammer":[[180,230]],"wisdom":[[4,8],[15,25]],"wisp projector":[[10,20]],"witchwild string":[[150,170]],"witherstring":[[40,50]],"wizendraw":[[20,35],[50,100],[70,80]],"wolfhowl":[[3,6],[8,15],[105,150],[120,150]],"wormskull":[[33,36]],"wraith flight":[[9,13],[150,190]],"wrath":[[250,300]]};
/* ⟦D2JSP ROLLS END⟧ */

/* the table's key: no trailing "(...)", no leading "The ", no apostrophes, lower case (tv/d2jsp_rolls.py canon) */
function d2jspRollKey(itemName) {
  return String(itemName || '').replace(/\s*\([^)]*\)\s*$/, '').trim().replace(/^the\s+/i, '')
    .replace(/['\u2019`]/g, '').replace(/\s+/g, ' ').toLowerCase();
}

/* v3885 - IS THIS POST'S ROLL PERFECT? Every roll it STATES (a slash tuple's numbers, a number on a stat word: "141def",
   "@20") that falls inside one of the item's variable ranges must sit at that range's maximum. -> true | false | null (the
   line states no roll the table knows, or the item has no variable roll: the words may say it). GrokBot 11-08: "137 DEF"
   is not a perfect Shako (141 is), "15/0/775" is a perfect Enigma, "20/-20" a perfect Griffon's Eye. */
/* REG-3627 - a number in a roll range standing immediately before the item's name counts ("141 Shako");
   a total-defense number after the name ("eth perf shako 211", "mage plate 995 def") is not that roll. */
function d2jspNumsBeforeName(text, itemName, ranges) {
  if (!text || !ranges) return [];
  var forms = d2jspSearchWords(itemName).forms, low = ' ' + d2jspFoldPrice(text) + ' ', nums = [], seen = {};
  forms.forEach(function (f) {
    if (!f) return;
    var pat = '(?:^|[^a-z0-9])(\\d{1,4})\\s+' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+') + '(?=$|[^a-z0-9])';
    var re = new RegExp(pat, 'gi'), m;
    while ((m = re.exec(low))) {
      var v = Number(m[1]);
      if (seen[v]) continue;
      if (ranges.some(function (r) { return v >= r[0] && v <= r[1]; })) { seen[v] = 1; nums.push(v); }
    }
  });
  return nums;
}

function d2jspRollPerfect(itemName, note, line) {
  var R = D2JSP_ROLLS[d2jspRollKey(itemName)];
  if (!R || !note) return null;
  var nums = [];
  (note.tuples || []).forEach(function (t) { t.forEach(function (v) { nums.push(Math.abs(v)); }); });
  (note.statNums || []).forEach(function (v) { nums.push(Math.abs(v)); });
  d2jspNumsBeforeName(line || (note && note.text) || '', itemName, R).forEach(function (v) { nums.push(v); });
  var hit = false, all = true;
  nums.forEach(function (v) {
    var inside = R.filter(function (r) { return v >= r[0] && v <= r[1]; });
    if (!inside.length) return;                       /* not a roll of this item (a quantity, a +skills, a socket count) */
    hit = true;
    if (!inside.some(function (r) { return v === r[1]; })) all = false;
  });
  return hit ? all : null;
}

function d2jspSlangOf(itemName) {
  var f = d2jspFoldPrice(itemName);
  for (var k in D2JSP_SLANG) {
    if (Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k) && d2jspFoldPrice(k) === f) return D2JSP_SLANG[k].slice();
  }
  return [];
}

/* the simplified name: no apostrophes, no leading "The", no "'s" */
function d2jspSimpleName(itemName) {
  return d2jspFoldPrice(String(itemName || '').replace(/['\u2018\u2019\u02BC`]s\b/gi, '')).replace(/^the\s+/, '').replace(/[^a-z0-9 \-]/g, ' ').replace(/\s+/g, ' ').trim();
}

/* the search words like a search box takes them: the slang form when traders have one, else the simplified name;
   every form a price line may name it by rides along in `forms` */
/* REG-3628 - official rune names, so a search for Ber is the bare name and 'ber' is a whole word, never a syllable */
var D2JSP_RUNE_NAMES = 'el eld tir nef eth ith tal ral ort thul amn sol shael dol hel io lum ko fal lem pul um mal ist gul vex ohm lo sur ber jah cham zod';
function d2jspRuneWord(itemName) {
  var m = /^([a-z]+)\s+rune$/.exec(d2jspSimpleName(itemName));
  if (!m) return '';
  return (' ' + D2JSP_RUNE_NAMES + ' ').indexOf(' ' + m[1] + ' ') >= 0 ? m[1] : '';
}
var D2JSP_ITEM_TOKENS = null;
function d2jspItemTokens() {
  if (D2JSP_ITEM_TOKENS) return D2JSP_ITEM_TOKENS;
  var seen = {}, out = [];
  function add(w) {
    w = d2jspFoldPrice(w).replace(/[^a-z0-9]+/g, ' ').trim();
    if (!w || seen[w] || (' ' + D2JSP_RUNE_NAMES + ' ').indexOf(' ' + w + ' ') >= 0) return;
    seen[w] = 1;
    out.push(w);
  }
  for (var k in D2JSP_SLANG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k)) continue;
    add(k);
    add(d2jspSimpleName(k));
    (D2JSP_SLANG[k] || []).forEach(add);
  }
  D2JSP_ITEM_TOKENS = out;
  return out;
}
function d2jspRuneFormOk(folded, rune) {
  if (folded.indexOf(' ' + rune + ' rune ') >= 0) return true;
  if (rune === 'eth') {
    if (/\beth (?:\d+\s*os|\d+os|os)\b/.test(folded)) return false;
    if (d2jspItemTokens().some(function (w) { return w && folded.indexOf(' ' + w + ' ') >= 0; })) return false;
  }
  return true;
}

function d2jspSearchWords(itemName) {
  itemName = d2jspResolveItem(itemName).item || itemName;   /* v3847 - "gt", "anni", "jmod" search as their item */
  var slang = d2jspSlangOf(itemName), simple = d2jspSimpleName(itemName), full = d2jspFoldPrice(itemName);
  var forms = [];
  [full, simple].concat(slang).forEach(function (w) { if (w && forms.indexOf(w) < 0) forms.push(w); });
  var rune = d2jspRuneWord(itemName);
  if (rune) {
    if (forms.indexOf(rune) < 0) forms.push(rune);
    /* REG-3628 query: the bare rune name (Ber, Jah, ...), never the phrase "ber rune" */
    return { query: rune.charAt(0).toUpperCase() + rune.slice(1), slang: slang, simple: simple, forms: forms };
  }
  return { query: slang.length ? slang[0] : simple, slang: slang, simple: simple, forms: forms };
}

/* the notation parser: "Anni 20/20/10 eth 2os @30 perf" -> slash tuples, socket count, ethereal, all res, perfect,
   upgraded, random, and each known short word in plain words */
function d2jspNotation(text) {
  var t = String(text || '');
  var out = { tuples: [], statNums: [], sockets: null, eth: false, perfect: false, upgraded: false, random: false, allRes: null, words: [], text: t };
  /* v3885 - a tuple's numbers may be signed: "12/-20" is a Griffon's Eye's roll (the unsigned form read nothing) */
  var m, re = /(-?\d+(?:\s*\/\s*-?\d+)+)/g;
  while ((m = re.exec(t))) out.tuples.push(m[1].split('/').map(function (x) { return Number(String(x).trim()); }));
  /* v3885 - a number on a stat word is a roll too ("141def", "141 def", "40ed", "@20") - never an fg price */
  var sre = /(\d+)\s*(?:def|defense|ed|%\s*ed|res)\b/gi;
  while ((m = sre.exec(t))) out.statNums.push(Number(m[1]));
  if ((m = /\b(\d)\s*os\b/i.exec(t))) out.sockets = Number(m[1]);
  if ((m = /@\s*(\d+)|(\d+)\s*@/.exec(t))) { out.allRes = Number(m[1] || m[2]); out.statNums.push(out.allRes); }
  out.eth = /\beth\b/i.test(t);
  /* v3885 - "Perfect Topaz" / "PRuby" is a socketed GEM, not the item's roll (GrokBot: "Shako 137 DEF / Perfect Topaz" read perfect) */
  out.perfect = /\bperf(?:ect)?\b(?!\s*(?:topaz|ruby|amethyst|sapphire|emerald|diamond|skull|gem)s?\b)/i.test(t);
  out.upgraded = /\bup'?d\b|\bupped\b/i.test(t);
  out.random = /\brand\b/i.test(t);
  String(t).toLowerCase().replace(/'/g, '').split(/[^a-z@]+/).forEach(function (w) {
    if (w && Object.prototype.hasOwnProperty.call(D2JSP_NOTATION, w) && out.words.indexOf(D2JSP_NOTATION[w]) < 0) out.words.push(D2JSP_NOTATION[w]);
  });
  return out;
}

var D2JSP_MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec';
/* the UTC day (ms) a line dates its post by, or null: "Oct 12, 2026", "12 Oct 2026", "2026-10-12", or Today /
   Yesterday (counted from nowMs) */
function d2jspLineDate(line, nowMs) {
  var t = String(line || ''), mon = D2JSP_MONTHS.split('|');
  var m = new RegExp('\\b(' + D2JSP_MONTHS + ')[a-z]*\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(20\\d\\d)\\b', 'i').exec(t);
  if (m) return Date.UTC(Number(m[3]), mon.indexOf(m[1].toLowerCase()), Number(m[2]));
  m = new RegExp('\\b(\\d{1,2})\\s+(' + D2JSP_MONTHS + ')[a-z]*\\.?,?\\s+(20\\d\\d)\\b', 'i').exec(t);
  if (m) return Date.UTC(Number(m[3]), mon.indexOf(m[2].toLowerCase()), Number(m[1]));
  m = /\b(20\d\d)-(\d\d)-(\d\d)\b/.exec(t);
  if (m) return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (/\btoday\b/i.test(t)) return nowMs;
  if (/\byesterday\b/i.test(t)) return nowMs - D2JSP_DAY_MS;
  return null;
}
/* the reading's own clock: its readAt when that is a time, else now */
function d2jspNowMs(readAt) {
  var t = Date.parse(String(readAt || ''));
  return isFinite(t) ? t : Date.now();
}
/* a post dated `when` is recent for a reading at nowMs: inside the window, and not in the future past a day of clock skew */
function d2jspRecent(when, nowMs) {
  return when != null && when <= nowMs + D2JSP_DAY_MS && when >= nowMs - D2JSP_QUOTE_WINDOW_DAYS * D2JSP_DAY_MS;
}

function d2jspFoldPrice(text) {
  return String(text || '').replace(/['\u2018\u2019\u02BC`]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();
}

/* v3843 - THE FG AMOUNTS ON A LINE, LARGE ONES INCLUDED. "300fg", "300 fg", "1,500 fg", "30,000fg", "1.5k", "25k fg",
   "10K". A comma groups thousands (before this "1,500 fg" read as 500). A bare "k" amount counts: the trade forum writes
   tens-of-thousands prices that way. Anything at or above 10,000,000 is not a price. */
function d2jspFgAmounts(line) {
  var out = [], m, re = /(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k\b|k(?=\s*fg)|)\s*(fg\b)?/ig;
  while ((m = re.exec(String(line || '')))) {
    if (!m[2] && !m[3]) continue;
    var n = Number(m[1].replace(/,/g, ''));
    if (m[2]) n = Math.round(n * 1000);
    if (n > 0 && n < 10000000) out.push(n);
  }
  return out;
}

/* v3844 - 2026 POSTS ONLY (Elad, 2026-10-30): on top of the rolling window, no post dated before this day prices an item. */
var D2JSP_QUOTE_SINCE_MS = Date.UTC(2026, 0, 1);

/* v3844 - THE POST A PRICE CAME FROM. Before the tags are stripped, a link to a forum topic or post is kept as a marker,
   so every price line knows the post it sits under and the evidence drawer can open it. */
var D2JSP_LINK_MARK = /\u27e6L:([^\u27e7]*)\u27e7/g;
function d2jspAbsLink(href) {
  var h = String(href || '').replace(/&amp;/g, '&').trim();
  if (!h) return '';
  if (/^https:\/\/forums\.d2jsp\.org\//i.test(h)) return h;
  if (/^https?:/i.test(h)) return '';
  return 'https://forums.d2jsp.org/' + h.replace(/^\/+/, '');
}

/* v3844 - WHICH AMOUNTS ON A LINE ARE THIS ITEM'S. A line that names one thing and carries one price is that price. A
   line listing several items ("anni 5 ist, pc 2000 fg, torch 300 fg") is split into its clauses, and only an amount in
   a clause that names the item counts - before this, Annihilus read 5-2000 off other items' prices. v3845 (second eye
   on v3844): when the split tears the name itself apart so that NO clause names the item, though the line does, the
   line's amounts are not dropped - the line names the item, so they are its. */
function d2jspNamed(text, forms) {
  var folded = ' ' + d2jspFoldPrice(text).replace(/[^a-z0-9]+/g, ' ') + ' ';
  return forms.some(function (f) {
    var key = ' ' + f.replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
    if (key === '  ' || folded.indexOf(key) < 0) return false;
    var word = key.trim();
    /* REG-3628 match: a bare rune name is a whole word; 'ber' never matches berry/number, and bare 'eth' is not ethereal */
    if ((' ' + D2JSP_RUNE_NAMES + ' ').indexOf(' ' + word + ' ') >= 0 && word.indexOf(' ') < 0)
      return d2jspRuneFormOk(folded, word);
    return true;
  });
}

/* v3845 - COMPACT ROLL COLUMNS (Elad, 2026-10-30 09:29): "guardian's thunder +8 -9 4 40 28 140fg" is the item, then
   its rolls as bare numbers in the item's own mod order (signs and % kept), then the price. Each clause that names the
   item gives its price with the numbers written between the name and that price; the desk maps them onto the mods. */
function d2jspAfterName(clause, forms) {
  var low = d2jspFoldPrice(clause), at = -1, len = 0;
  forms.forEach(function (f) {
    var re = new RegExp('(^|[^a-z0-9])' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+') + '(?=$|[^a-z0-9])');
    var m = re.exec(low);
    if (m && (at < 0 || m.index < at)) { at = m.index + m[1].length; len = m[0].length - m[1].length; }
  });
  return at < 0 ? null : low.slice(at + len);
}
function d2jspClauseCols(clause, forms) {
  var rest = d2jspAfterName(clause, forms);
  if (rest == null) return null;
  var cut = /(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:k\b|k(?=\s*fg)|fg\b)/i.exec(rest);
  var head = cut ? rest.slice(0, cut.index) : rest, toks = head.trim().split(/\s+/), cols = [];
  for (var i = 0; i < toks.length; i++) {
    var m = /^([+-]?\d{1,4})%?$/.exec(toks[i]);
    if (!m) { if (cols.length) break; else continue; }
    cols.push(Number(m[1]));
  }
  return cols.length >= 2 && cols.length <= 8 ? cols : null;
}
function d2jspLineRows(line, forms) {
  var all = d2jspFgAmounts(line);
  if (!all.length) return [];
  var clauses = all.length <= 1 ? [String(line)] : String(line).split(/\s*(?:[;|\u2022]|,(?!\d{3}(?!\d)))\s*/), out = [];
  clauses.forEach(function (c) {
    if (all.length > 1 && !d2jspNamed(c, forms)) return;
    var cols = d2jspClauseCols(c, forms);
    d2jspFgAmounts(c).forEach(function (n) { out.push({ fg: n, cols: cols, text: c }); });   /* v3885 - its own clause */
  });
  if (!out.length && d2jspNamed(line, forms) && !clauses.some(function (c) { return d2jspNamed(c, forms); })) {
    var cols = d2jspClauseCols(line, forms);
    all.forEach(function (n) { out.push({ fg: n, cols: all.length === 1 ? cols : null, text: String(line) }); });
  }
  return out;
}

/* each price with its evidence: the post's link, its day, the fg and the roll as read (the slash
   notation). The post's own words stay on the forum - the link opens them. */
/* v3847 - the page's HTML entities, decoded once, after the tags are gone (so a decoded "<" can never open a tag). */
function d2jspDecodeEntities(t) {
  var named = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', rsquo: '\u2019', lsquo: '\u2018',
                ldquo: '\u201c', rdquo: '\u201d', ndash: '-', mdash: '-', hellip: '...' };
  return String(t).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, function (all, k) {
    if (k[0] === '#') {
      var n = k[1] === 'x' || k[1] === 'X' ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10);
      return n > 0 && n < 0x110000 ? String.fromCodePoint(n) : all;
    }
    var v = named[k.toLowerCase()];
    return v == null ? all : v;
  });
}

function d2jspPosts(text, itemName, nowMs) {
  if (nowMs == null) nowMs = Date.now();
  var forms = d2jspSearchWords(itemName).forms;
  if (!forms.length) return [];
  var plain = String(text || '')
    .replace(/<a\s[^>]*href\s*=\s*["']([^"']*(?:topic\.php|[?&]t=\d|[?&]p=\d)[^"']*)["'][^>]*>/gi, ' \u27e6L:$1\u27e7 ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(?:p|div|tr|li|h\d)>/gi, '\n')
    /* v3847 (Elad 15:27, Guardian's Thunder read 0 posts) - search highlighting wraps the matched word in an inline tag
       (<b>guardian</b>'s); turning that tag into a space made "guardian 's", which no item form matches. An inline tag
       is unwrapped with NO space; every other tag still becomes one. */
    .replace(/<\/?(?:b|i|u|em|strong|span|font|mark|small|big)(?:\s[^>]*)?>/gi, '')
    /* v3893 (#180, REG-3554) - a signed-out readable user.php name, when a post shows exactly one,
       is the seller. Two names in one card stay unknown (do not invent which is the seller). */
    .replace(/<a\s[^>]*href\s*=\s*["']([^"']*user\.php[^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi, function (_, href, name) {
      var n = String(name || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      if (!n || n.length > 32) return ' ';
      return ' \u27e6A:' + n + '\u27e7 ';
    })
    .replace(/<[^>]+>/g, ' ');
  plain = d2jspDecodeEntities(plain);   /* v3847 - &#39; / &rsquo; / &amp; arrive raw: Guardian&#39;s matched nothing */
  var rows = [], when = null, link = '', explicit = false, used = false, pending = '', seen = {}, authors = [];
  function rememberUndated() {
    pending = '';
  }
  plain.split('\n').forEach(function (raw) {
    var m, re = new RegExp(D2JSP_LINK_MARK.source, 'g');
    var here = '';
    while ((m = re.exec(raw))) { var a = d2jspAbsLink(m[1]); if (a) here = a; }
    var hereWho = [], wm, whoRe = /\u27e6A:([^\u27e7]*)\u27e7/g;
    while ((wm = whoRe.exec(raw))) { if (wm[1]) hereWho.push(wm[1]); }
    var line = raw.replace(new RegExp(D2JSP_LINK_MARK.source, 'g'), ' ')
      .replace(/\u27e6A:[^\u27e7]*\u27e7/g, ' ');
    var d = d2jspLineDate(line, nowMs);
    /* v3845 (second eye on v3844) - a new post's date line starts a new post: the last post's link does not carry over */
    /* v3845 - a post's own written date beats a relative "Today" / "Yesterday" (the search page's last-activity
       stamp): Simsalara's Oct 7 post read as the reading's day. A relative stamp dates a post only when that post has
       no written date of its own. */
    /* a search card puts the topic link and the date on different lines. The date keeps the link that
       opened this post until a row is priced. A later date, with no new link, does not keep it. A link that
       arrives after the date and before any row belongs to that same post. */
    var rel = d != null && !/\b20\d\d\b/.test(line) && /\b(?:today|yesterday)\b/i.test(line);
    if (d != null && !rel) {
      var kept = pending;
      if (here && pending && here !== pending) { rememberUndated(); kept = ''; authors = []; }
      when = d; explicit = true; used = false;
      link = here || kept || '';
      pending = '';
      authors = [];
    } else if (here && here !== link) {
      /* v3894 - reset authors whenever the topic link changes: a new undated topic must not inherit the last seller */
      if (when != null && !used) { link = here; pending = ''; authors = []; }
      else { rememberUndated(); link = here; pending = here; when = rel ? d : null; explicit = false; used = false; authors = []; }
    } else if (rel && !explicit) when = d;
    else if (here) link = here;
    /* v3843 - a price counts only under a recently dated post; v3844 - and only a 2026 one */
    /* A line that names the item and has no fg is skipped. It is not a post and it keeps no link.
       The same for a line with no date, or a date outside the window. used only closes this card
       so the next topic does not inherit the link. */
    var named = d2jspNamed(line, forms) && !d2jspOtherReading(line, d2jspResolveItem(itemName).item || itemName);
    /* v3894 - a user.php mention in a post body is not the seller (the seller's name may be plain text).
       Collect authors from header-ish lines only: not a line that names the item or carries a price. */
    if (!named && !/\bfg\b/i.test(line)) {
      hereWho.forEach(function (n) { authors.push(n); });
    }
    if (!d2jspRecent(when, nowMs) || when < D2JSP_QUOTE_SINCE_MS) {
      if (when == null && pending && named) return;
      if (named) used = true;
      return;
    }
    if (!named) return;
    var lr = d2jspLineRows(line, forms);
    if (!lr.length) used = true;
    lr.forEach(function (x) {
      /* v3885 (GrokBot 11-08) - each clause read on its own: "Wire Fleece 15/0/775 2000 ; Wyrmhide 1850" gave both rows the
         first clause's roll */
      var note = d2jspNotation(x.text || line);
      /* v3885 - the same words at the same price in one post is a bump or a quote, never a second listing */
      var dup = (link || '') + '\u0001' + d2jspFoldPrice(x.text || line) + '\u0001' + x.fg;
      if (seen[dup]) { used = true; return; }
      seen[dup] = 1;
      var row = { fg: x.fg, day: new Date(when).toISOString().slice(0, 10), link: link,
        roll: note.tuples, mods: note.words.slice(0, 12), w: 1 };
      var who = d2jspAuthorOf(authors);
      if (who) row.author = who;
      if (x.cols) row.cols = x.cols;
      /* v3885 - PERFECT IS READ FROM THE ROLLS (d2jspRollPerfect); only a line stating no roll the item's table knows
         falls back to its words (v3849's "perf"/"perfect", gem-safe now) */
      var byRoll = d2jspRollPerfect(d2jspResolveItem(itemName).item || itemName, note, x.text || line);
      if (byRoll === true || (byRoll === null && note.perfect)) row.perfect = true;
      rows.push(row);
      used = true;
    });
  });
  rememberUndated();
  return d2jspOneVotePerPost(d2jspTrim(rows));
}

/* v3885 (GrokBot 11-08: one shop post supplied 9 of the 10 Griffon's Eye prices) - ONE VOTE PER POST. The rows of one post
   (one link) share a weight of 1 between them; a row with no link is its own post. An outlier's 0 stays 0. */
/* v3893 (#180, REG-3554) - THE SAME SELLER IS ONE POST AND ONE PRICE. When a readable author is on
   the row (signed-out user.php, or a stored author), every topic from that seller shares one vote.
   An unknown author stays one vote per link. Topics are never hard-deleted or merged by id. */
function d2jspAuthorOf(names) {
  var seen = {}, uniq = [];
  (names || []).forEach(function (n) {
    var k = String(n || '').trim();
    if (!k) return;
    var fold = k.toLowerCase();
    if (seen[fold]) return;
    seen[fold] = 1;
    uniq.push(k);
  });
  return uniq.length === 1 ? uniq[0] : '';
}
function d2jspVoteKey(r) {
  var a = r && r.author && String(r.author).trim();
  if (a) return 'seller:' + a.toLowerCase();
  if (r && r.link) return 'link:' + r.link;
  return '';
}
function d2jspOneVotePerPost(rows) {
  var n = {};
  rows.forEach(function (r) { var k = d2jspVoteKey(r); if (k && r.w > 0) n[k] = (n[k] || 0) + 1; });
  rows.forEach(function (r) { var k = d2jspVoteKey(r); if (k && r.w > 0 && n[k] > 1) r.w = Math.round((r.w / n[k]) * 1000) / 1000; });
  return rows;
}

/* v3844 - A FAR PRICE IS SET ASIDE. With five or more prices, one more than three times off the middle (a 2000 fg
   bundle beside 18 fg singles) is kept in the evidence, marked out, and does not move the price. */
function d2jspTrim(rows) {
  if (rows.length < 5) return rows;
  var mid = d2jspMedian(rows.map(function (r) { return r.fg; }));
  /* v3845 - a post that writes its roll is not judged by the middle: its roll may be why it is far (the -10 jewel at
     390 fg). The desk fits price against roll and sets such a post aside only when its roll does not explain it. */
  /* v3847 (#230 6524232951) - THE SAME RULE FOR A SLASH ROLL. "anni 20/20/10 1200fg" was set aside as far from the
     middle while its roll was why. A post that writes a slash roll is judged against a price-by-roll fit over the posts
     that write a roll of the same shape, and set aside only when its roll does not explain its price (3x off the fit).
     Too few such posts to fit: it is kept, never judged by the middle. */
  var fit = d2jspSlashFit(rows);
  rows.forEach(function (r) {
    if (r.cols) return;
    var t = d2jspSlashOf(r);
    if (t) {
      var f = fit[t.length];
      if (!f) return;
      var e = f.at(t);
      if (r.fg > e * 3 || r.fg * 3 < e) { r.w = 0; r.out = 'far from the middle: its roll does not explain its price (fit ' + Math.round(e) + ' fg)'; }
      return;
    }
    if (r.fg > mid * 3 || r.fg * 3 < mid) { r.w = 0; r.out = 'far from the middle ' + mid + ' fg'; }
  });
  return rows;
}

/* v3849 - A NO-ROLL PRICE 10x OFF THE CLOSE FIT. The 3x rule above still marks a far price out loud.
   This one is quiet and extra: only posts that wrote a roll (columns or a slash) set the middle, and
   only when at least three of them did. A post with no roll that is more than 10x off that middle, or
   under a tenth of it, is set aside (w 0) and counted. It does not grow a new "far from the middle"
   label. The price line says "n lines skipped" once. */
function d2jspGrossSkip(rows) {
  var close = (rows || []).filter(function (r) { return r && (r.cols || d2jspSlashOf(r)); });
  if (close.length < 3) return 0;
  var mid = d2jspMedian(close.map(function (r) { return r.fg; }));
  if (!(mid > 0)) return 0;
  var n = 0;
  rows.forEach(function (r) {
    if (r.cols || d2jspSlashOf(r)) return;
    if (r.fg > mid * 10 || r.fg * 10 < mid) { r.w = 0; n++; }
  });
  return n;
}

/* the post's first slash roll (2+ numbers), or null */
function d2jspSlashOf(r) {
  var t = (r.roll || []).filter(function (x) { return x && x.length >= 2; })[0];
  return t ? t.map(Number) : null;
}

/* {length: {at(t)}} - per roll shape with 5+ posts: ln(fg) = a + b * place, place = the roll's mean position between
   the lowest and highest value each column takes in these posts (0..1). */
function d2jspSlashFit(rows) {
  var by = {}, out = {};
  rows.forEach(function (r) { var t = d2jspSlashOf(r); if (t && r.fg > 0) (by[t.length] = by[t.length] || []).push({ t: t, fg: r.fg }); });
  Object.keys(by).forEach(function (L) {
    var pts = by[L];
    if (pts.length < 5) return;
    var lo = [], hi = [];
    for (var i = 0; i < +L; i++) {
      lo.push(Math.min.apply(null, pts.map(function (p) { return p.t[i]; })));
      hi.push(Math.max.apply(null, pts.map(function (p) { return p.t[i]; })));
    }
    var place = function (t) {
      var s = 0, n = 0;
      for (var i = 0; i < t.length; i++) if (hi[i] > lo[i]) { s += Math.max(0, Math.min(1, (t[i] - lo[i]) / (hi[i] - lo[i]))); n++; }
      return n ? s / n : 0.5;
    };
    var xs = pts.map(function (p) { return place(p.t); }), ys = pts.map(function (p) { return Math.log(p.fg); });
    /* fit, drop the one point furthest past 3x, refit: one 2000 fg bundle must not drag the line onto the others */
    var keep = xs.map(function () { return true; }), a = 0, b = 0;
    for (;;) {
      var ix = [], k;
      for (k = 0; k < xs.length; k++) if (keep[k]) ix.push(k);
      var mx = ix.reduce(function (s, k) { return s + xs[k]; }, 0) / ix.length, my = ix.reduce(function (s, k) { return s + ys[k]; }, 0) / ix.length;
      var sxx = 0, sxy = 0;
      ix.forEach(function (k) { sxx += (xs[k] - mx) * (xs[k] - mx); sxy += (xs[k] - mx) * (ys[k] - my); });
      b = sxx > 1e-9 ? sxy / sxx : 0; a = my - b * mx;
      var worst = -1, far = Math.log(3);
      ix.forEach(function (k) { var d = Math.abs(ys[k] - (a + b * xs[k])); if (d > far) { far = d; worst = k; } });
      if (worst < 0 || ix.length <= 4) break;
      keep[worst] = false;
    }
    out[L] = { at: function (t) { return Math.exp(a + b * place(t)); } };
  });
  return out;
}

function d2jspPrices(text, itemName, nowMs) {
  return d2jspPosts(text, itemName, nowMs).filter(function (r) { return r.w > 0; }).map(function (r) { return r.fg; });
}

function d2jspMedian(nums) {
  if (!nums || !nums.length) return null;
  var s = nums.slice().sort(function (a, b) { return a - b; });
  var mid = Math.floor(s.length / 2);
  if (s.length % 2) return s[mid];
  return Math.round((s[mid - 1] + s[mid]) / 2);
}

function d2jspSpan(nums) {
  if (!nums || !nums.length) return { low: null, high: null };
  var s = nums.slice().sort(function (a, b) { return a - b; });
  return { low: s[0], high: s[s.length - 1] };
}

function d2jspRead(html, item, readAt) {
  var text = String(html || '');
  var base = {
    item: String(item || ''), fg: null, low: null, high: null,
    n: 0, readAt: readAt, reason: 'unread', board: D2JSP_QUOTE_BOARD
  };
  if (!text || /Just a moment/i.test(text) || /cf-browser-verification/i.test(text)) return base;
  if (/do not have permission/i.test(text) || /not currently logged in/i.test(text)) {
    base.reason = 'need-login';
    return base;
  }
  var posts = d2jspPosts(text, item, d2jspNowMs(readAt));
  var skipped = d2jspGrossSkip(posts);
  var nums = posts.filter(function (r) { return r.w > 0; }).map(function (r) { return r.fg; });
  var fg = d2jspMedian(nums);
  if (fg == null) {
    base.reason = 'no prices';
    base.posts = posts.slice(0, 40);
    if (skipped > 0) base.skipped = skipped;
    return base;
  }
  var span = d2jspSpan(nums);
  var read = {
    item: String(item || ''), fg: fg, low: span.low, high: span.high,
    n: nums.length, readAt: readAt, reason: 'read', board: D2JSP_QUOTE_BOARD,
    posts: posts.slice(0, 40)
  };
  if (skipped > 0) read.skipped = skipped;
  return read;
}
/* ⟦D2JSP QUOTE END⟧ */

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const item = (url.searchParams.get('item') || '').trim().slice(0, 80);
  const readAt = new Date().toISOString();
  if (!item) return json({ item: '', fg: null, n: 0, readAt: readAt, reason: 'no item', board: BOARD });
  const keywords = d2jspSearchWords(item).query || String(item).replace(/['\u2018\u2019\u02BC`]/g, '');
  const search = 'https://forums.d2jsp.org/search.php?sr=posts&search_keywords='
    + encodeURIComponent(keywords) + '&fid%5B%5D=' + BOARD;
  try {
    const r = await fetch(search, {
      headers: {
        'User-Agent': 'KonyoD2RBible/1.0 (+https://bull-4-u.com/d2r/)',
        Accept: 'text/html',
      },
    });
    if (!r.ok) return json(d2jspRead('', item, readAt));
    const html = await r.text();
    return json(d2jspRead(html.slice(0, 200000), item, readAt));
  } catch (e) {
    return json(d2jspRead('', item, readAt));
  }
}
