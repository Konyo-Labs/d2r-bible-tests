// v3772 (REG-2293) - what a node child of a gate read, in sitecustomize.py's trace format.
//
// gate_ledger.trace_env() puts `--require <this file>` in NODE_OPTIONS next to the python hook.
// It wraps the fs calls that read, list, stat or write a path, and every child_process call.
// Lines are `KIND<TAB>PID<TAB>TEXT`, repo-relative, appended to TV_GATE_TRACE. A child that is
// not node or python, and an ES module loaded from this checkout (its imports do not go through
// fs), are a U line: that run is never carried.
//
// REG-3319 (v3877, board #92 - his 11-06 "these shards and these tests need to be smooth and work fast") - THE SAME
// HOOK ALSO WRITES HEART2'S PROOF TRACE. heart2 (REG-2640) keys a PROVEN by what its traced run opened, and a node child
// used to be a `U` there - untraced - so every law that runs node kept the byte-for-byte key over its whole closure
// (measured at 219a4846c: 1,555 of the 4,067 proofs keyed on >1,500 files had a node child and nothing else). When
// HEART2_TRACE_LOG is set, this hook writes heart2's own format beside the gate's, to that log:
//   `H <pid> <ppid>`  its hello - heart2 counts a node child it was told about (`P`) and needs this line from it;
//   `N node`          a node ran in this law's run - heart2 then never drops a JavaScript-family input (.js .mjs .cjs
//                     .json .ts .wasm), whatever this node version's module loader shows, so an import() that a loader
//                     reads past fs can never leave a stale key;
//   `R|S <basename>`  every path read, written or stat'd (and its real path's basename), like the python hook;
//   `L <realpath>`    every directory listed;
//   `P spawn <exe>`   a node or python child that inherits both traces (it must say its own hello);
//   `A spawn node`    `node --version` / `-v`: it reads nothing, and exits before any preload could say hello;
//   `U <why>`         anything else (a shell, git, Chrome, an ES module entry point): heart2 then drops nothing.
'use strict';
(function () {
  if (global.__tvNodeTraceOn) return;          // one hook per process, however many --require flags named it
  global.__tvNodeTraceOn = true;
  const out = process.env.TV_GATE_TRACE;
  const root = process.env.TV_GATE_TRACE_ROOT;
  const h2out = process.env.HEART2_TRACE_LOG;
  if (!(out && root) && !h2out) return;
  const fs = require('fs');
  const path = require('path');
  const url = require('url');
  const writeSync = fs.writeSync;
  const realpath = (fs.realpathSync && fs.realpathSync.native) || fs.realpathSync;   // taken before any wrap
  const roots = [];
  let fd = null;
  if (out && root) {
    roots.push(path.normalize(root));
    try { const r = fs.realpathSync(root); if (!roots.includes(r)) roots.push(r); } catch (e) { /* keep one */ }
    try { fd = fs.openSync(out, 'a'); } catch (e) { fd = null; }
  }
  let fd2 = null;
  if (h2out) {
    try { fd2 = fs.openSync(h2out, 'a'); } catch (e) { fd2 = null; }
  }
  if (fd === null && fd2 === null) return;
  const seen = new Set();
  const seen2 = new Set();
  let busy = false;
  function emit(kind, text, once) {
    if (fd === null) return;
    const key = kind + '\t' + text;
    if (once !== false) { if (seen.has(key)) return; seen.add(key); }
    try { writeSync(fd, kind + '\t' + process.pid + '\t' + String(text).replace(/[\t\n]/g, ' ') + '\n'); } catch (e) { /* lost */ }
  }
  function emit2(tag, text, once) {
    if (fd2 === null) return;
    const line = tag + ' ' + String(text).replace(/\n/g, ' ');
    if (once !== false) { if (seen2.has(line)) return; seen2.add(line); }
    try { writeSync(fd2, line + '\n'); } catch (e) { /* lost: heart2 then sees no hello, and drops nothing */ }
  }
  function abs(p) {
    try {
      if (p == null || typeof p === 'number') return null;
      if (p instanceof URL) p = url.fileURLToPath(p);
      if (Buffer.isBuffer(p)) p = p.toString();
      if (typeof p !== 'string') return null;
      return path.resolve(p);
    } catch (e) { return null; }
  }
  function rel(p) {
    const a = abs(p);
    if (a === null) return null;
    for (const b of roots) {
      if (a === b) return '';
      if (a.startsWith(b + path.sep)) {
        const r = a.slice(b.length + 1).split(path.sep).join('/');
        if (r.startsWith('tv/gate_trace/') || r.split('/').includes('node_modules')) return null;
        return r;
      }
    }
    return null;
  }
  function note(kind, p) { const r = rel(p); if (r !== null) emit(kind, r); }
  // heart2 keys by BASENAME, as its python hook does: the name and the real path's name, never filtered by tree
  function base2(tag, p) {
    if (fd2 === null) return;
    const a = abs(p);
    if (a === null) { emit2('U', 'unreadable path in ' + tag); return; }
    emit2(tag, path.basename(a.replace(/[\\/]+$/, '')));
    try { emit2(tag, path.basename(realpath(a).replace(/[\\/]+$/, ''))); } catch (e) { /* absent: its name is enough */ }
  }
  function writes(flags) {
    return typeof flags === 'string' ? /[wax+]/.test(flags)
      : (typeof flags === 'number' && (flags & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_CREAT)) !== 0);
  }
  function wrap(obj, name, before) {
    const real = obj && obj[name];
    if (typeof real !== 'function') return;
    obj[name] = function () {
      if (!busy) { busy = true; try { before.apply(null, arguments); } catch (e) { /* never break the call */ } finally { busy = false; } }
      return real.apply(this, arguments);
    };
  }
  const R = (p) => { note('R', p); base2('R', p); };
  const W = (p) => { note('W', p); base2('R', p); };        // a file this run wrote stays a byte input for heart2
  const L = (p) => {
    note('L', p);
    if (fd2 === null) return;
    const a = abs(p);
    if (a === null) return;
    try { emit2('L', realpath(a)); } catch (e) { emit2('L', a); }
  };
  const realLstat = fs.lstatSync;
  const S = (p) => {
    base2('S', p);
    const r = rel(p);
    if (r === null) return;
    let there = true;
    try { realLstat(p); } catch (e) { there = false; }
    emit(there ? 'S' : 'A', r);
  };
  const P = fs.promises;
  for (const n of ['readFileSync', 'readFile', 'createReadStream']) wrap(fs, n, R);
  for (const n of ['readFile']) wrap(P, n, R);
  for (const n of ['openSync', 'open']) wrap(fs, n, (p, flags) => (writes(flags) ? W(p) : R(p)));
  wrap(P, 'open', (p, flags) => (writes(flags) ? W(p) : R(p)));
  for (const n of ['readdirSync', 'readdir', 'opendirSync', 'opendir']) wrap(fs, n, L);
  for (const n of ['readdir', 'opendir']) wrap(P, n, L);
  for (const n of ['existsSync', 'statSync', 'lstatSync', 'stat', 'lstat', 'accessSync', 'access', 'exists', 'realpathSync']) wrap(fs, n, S);
  for (const n of ['stat', 'lstat', 'access']) wrap(P, n, S);
  for (const n of ['writeFileSync', 'writeFile', 'appendFileSync', 'appendFile', 'mkdirSync', 'mkdir', 'createWriteStream']) wrap(fs, n, W);
  for (const n of ['writeFile', 'appendFile', 'mkdir']) wrap(P, n, W);
  for (const n of ['renameSync', 'rename']) wrap(fs, n, (a, b) => W(b));
  wrap(P, 'rename', (a, b) => W(b));
  for (const n of ['copyFileSync', 'copyFile']) wrap(fs, n, (a, b) => { R(a); W(b); });
  let kids = 0;
  function versionOnly(args) {
    return Array.isArray(args) && args.length === 1 && (args[0] === '--version' || args[0] === '-v');
  }
  function child(file, env, args) {
    const head = path.basename(String(file || ''));
    const source = env || process.env;
    const isNode = head === 'node' || head === 'nodejs' || file === process.execPath;
    const isPy = head.startsWith('python');
    const hooked = String(source.NODE_OPTIONS || '').includes('node_trace.cjs');
    if (fd !== null) {
      const traced = source.TV_GATE_TRACE === out;
      if (traced && (isPy || (isNode && hooked))) {
        kids += 1;
        emit('P', String(kids), false);
      } else {
        emit('U', 'started ' + (head || 'a process'));
      }
    }
    if (fd2 !== null) {
      const traced2 = source.HEART2_TRACE_LOG === h2out;
      if (isNode && versionOnly(args)) emit2('A', 'spawn ' + head, false);
      else if (traced2 && (isPy || (isNode && hooked))) emit2('P', 'spawn ' + head, false);   // it says its own hello
      else emit2('U', 'spawn ' + (head || 'a process'), false);
    }
  }
  const cp = require('child_process');
  for (const n of ['spawn', 'spawnSync', 'execFile', 'execFileSync']) {
    wrap(cp, n, (file, args, opts) => {
      if (args && !Array.isArray(args) && typeof args === 'object') { opts = args; args = []; }
      child(file, opts && opts.env, args);
    });
  }
  for (const n of ['exec', 'execSync']) wrap(cp, n, () => { emit('U', 'started a shell'); emit2('U', 'spawn a shell', false); });
  wrap(cp, 'fork', (mod, args, opts) => {
    if (args && !Array.isArray(args) && typeof args === 'object') { opts = args; args = []; }
    child(process.execPath, opts && opts.env, ['fork']);
  });
  emit('B', String(process.ppid));
  emit2('H', process.pid + ' ' + process.ppid, false);
  emit2('N', 'node', false);
  const main = process.argv[1];
  const esm = process.execArgv.some((a) => a.startsWith('--input-type=module') || a.startsWith('--experimental-loader') || a.startsWith('--import'));
  if (esm || (main && rel(main) !== null && /\.mjs$/.test(main))) {
    emit('U', 'ran an ES module, whose imports do not go through fs');
  }
  if (esm || (main && /\.mjs$/.test(main))) emit2('U', 'ran an ES module entry point', false);
  if (main) R(main);
})();
