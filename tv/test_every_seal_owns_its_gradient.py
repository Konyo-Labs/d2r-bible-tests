"""v3855 — a page draws many seals; each one must carry its own gradient id, or the first hidden seal blanks the rest."""
import os, re, subprocess, unittest
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()
HERE = os.path.dirname(os.path.abspath(__file__))
def _page(): return open(os.path.join(HERE, "..", "bible.html"), encoding="utf-8", errors="replace").read()
def _drawer(s):
    i = s.index("var _CHX_SEAL = {"); j = s.index("function _proof(t){", i); return s[i:j]
JS = r"""
var esc=function(x){return String(x)},_bars=function(){return null},_ago=function(){return ''},window={};
%s
var out=[_chxSeal('HARDENED',20,20,0,true),_chxSeal('PROVEN',3,9,0),_chxSeal('WATCHED',1,2,0),_chxSeal(null)].join('');
console.log(out);
"""
class EverySealOwnsItsGradient(unittest.TestCase):
    def _ids(self, drawer):
        words = "var _CHX_WORD = { HARDENED: 'Confirmed', PROVEN: 'Not confirmed yet', WATCHED: 'Not confirmed yet' };"
        r = subprocess.run(["node", "-"], input=JS % (words + drawer), capture_output=True, text=True, timeout=30)  # stdin: a page-sized program overflows one argv string on Linux
        self.assertEqual(r.returncode, 0, r.stderr)
        html = r.stdout
        ids = re.findall(r'id="([^"]+)"', html); refs = re.findall(r'url\(#([^)]+)\)', html)
        return ids, refs
    def test_ids_unique_and_refs_resolve(self):
        ids, refs = self._ids(_drawer(_page()))
        self.assertEqual(len(ids), 4); self.assertEqual(len(set(ids)), len(ids), "two seals share a gradient id")
        for r in refs: self.assertIn(r, ids, "a seal points at another seal's gradient")
    def test_red_proof_shared_ids_fail(self):
        d = _drawer(_page()).replace(".replace(/chxSeal([YN])/g, '$&' + '-' + (++_chxSealSeq))", "")
        ids, _ = self._ids(d)
        self.assertNotEqual(len(set(ids)), len(ids), "red-proof: without the counter the ids must collide")
if __name__ == "__main__": unittest.main()
