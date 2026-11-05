# -*- coding: utf-8 -*-
"""Post one priced draft to d2jsp board 268 (271 on a ladder console) through the Chrome login on this machine.

The desk in bible.html calls POST /api/d2jsp_send. This module reads the d2jsp
cookies from the local Chrome profile at that moment, opens the board's own New
Trade form in a scratch Chrome, and submits only when that form is the one this
desk knows and the browser is logged in. The cookie is not stored, not logged,
and not returned, and the cookie database is read in memory, never copied to
disk. A missing login, an unreadable cookie, or a form this desk does not know
returns a status word and does not claim a post.

One send runs at a time. A submit that was clicked and not receipted is
maybe-sent, never "nothing was posted", and the same draft is not sent again
for 30 minutes after it was posted or may have been, unless a later send
changed that topic. Every answer's reason is one of SEND_REASONS.

Windows reads the Chrome profile on that machine through the current user key.
A cookie Chrome locks to the browser itself stays unread. A public page has no
route and stays unposted. Linux reads the Chrome profile on that machine.
"""
from __future__ import annotations

import atexit
import base64
import contextlib
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BOARD = 268
LADDER_BOARD = 271
POST_BOARDS = (BOARD, LADDER_BOARD)
QUOTE_BOARD = 268
COMPOSE_URL = "https://forums.d2jsp.org/post.php?mode=post&f=268"
LOGIN_URL = "https://forums.d2jsp.org/login.php"

#: v3861 - WHY WINDOWS SIGNS IN THROUGH A CHROME PROFILE THIS CONSOLE OWNS. MEASURED 2026-11-05 on the work ALT (Chrome 156):
#: the d2jsp cookies in Chrome's main profile are v20, app-bound encryption (Chrome 127+) that only Chrome itself opens, so
#: the lamp read "could not read the Chrome login" signed in or not, on every up-to-date Windows PC. A cookie Chrome writes
#: under any OTHER --user-data-dir is v10 (measured the same hour on a throwaway profile with a fake cookie): the DPAPI key
#: in that profile's own Local State opens it, with the reader this file already has. So the lamp opens the forum in this
#: profile, he signs in there once, and the console reads it. Chrome's app-bound key is never touched. ⚠ Windows locks a
#: profile's cookie file while its Chrome runs (measured: "unable to open database file" at 0 s and at 35 s, read fine
#: after close), so an open sign-in window reads as "login-open", never as signed out.
LOGIN_PROFILE_PARTS = ("TVD", "d2jsp-login")


def login_profile_dir(platform=None, env=None):
    """The Chrome profile this console owns for its d2jsp sign-in. -> path | None (none on this platform)"""
    plat = sys.platform if platform is None else platform
    env = os.environ if env is None else env
    if plat == "win32":
        local = env.get("LOCALAPPDATA")
        return os.path.join(local, *LOGIN_PROFILE_PARTS) if local else None
    return None
_HOST = "forums.d2jsp.org"
_PRICE_LINE = re.compile(r"^\d+(?:\.\d+)? fg$")
_CHROME_EPOCH = 11644473600  # seconds from 1601-01-01 to 1970-01-01

# REG-2490 - every reason d2jsp_send answers with. The desk in bible.html names each one.
SEND_REASONS = (
    "submitted",            # ok: the board shows the new topic (topic)
    "already-posted",       # submitted from this console in the last 30 min, so not sent again (topic, at)
    "maybe-sent",           # the submit was clicked and no receipt came back (board, at)
    "maybe-sent-recently",  # maybe-sent in the last 30 min, so not sent again (at)
    "busy",                 # another send is running on this console
    "not-posted",           # no click happened, or the board sent the compose form back
    "unread",               # the forum could not be read before the click
    "chrome-start",         # the scratch Chrome could not start (why)
    "chrome-unread",        # the Chrome login could not be read
    "need-login",           # Chrome is not logged into d2jsp (opened)
    "form-unknown",         # the form is not the one this desk fills
    "wrong-board",
    "no-price",
    "title",
    "long",
    "origin",
)


def console_may_post(origin, host, port, sec_fetch_site=None):
    """True only for this console's own page. A foreign Origin never may, and a cross-site request
    with NO Origin never may either.

    REG-2188 — A NO-ORIGIN GET WAS TRUSTED ON HOST ALONE. A browser sends no Origin on a cross-site
    <img>, iframe or window.open GET, but it DOES send the target's Host — so any page he visited
    could reach /api/d2jsp_login and /api/d2jsp_quote (read the keychain, decrypt his cookies, start
    a scratch Chrome, pull his real Chrome to the login page). It could not read the reply, but the
    side effects fired. Sec-Fetch-Site is sent by the browser and cannot be forged by the page: a
    cross-site embed is `cross-site`, a page on another local port is `same-site`, the console's own
    fetch is `same-origin`, and a user typing the URL is `none`. So a no-Origin request is refused
    when it is EXPLICITLY cross-site or same-site, and still allowed when the header is same-origin,
    none or absent — the console's own request is never broken, even on a client that omits it.
    POST is already safe (browsers always send Origin on POST); the arg defaults to None there.
    [[the-unjoined-end]] [[unknown-stays-unknown]]"""
    allowed = {"http://127.0.0.1:%d" % port, "http://localhost:%d" % port}
    if origin:
        return origin in allowed
    if str(sec_fetch_site or "").strip().lower() in {"cross-site", "same-site"}:
        return False
    bare = (host or "").split(",")[0].strip()
    return bare in {"127.0.0.1:%d" % port, "localhost:%d" % port}


def _d2jsp_host(host):
    h = str(host or "").lstrip(".").lower()
    return h == "d2jsp.org" or h.endswith(".d2jsp.org")


def _chrome_now(now_utc):
    """Chrome stores expiry as microseconds since 1601-01-01."""
    if now_utc is None:
        import time
        now_utc = time.time()
    return int((float(now_utc) + _CHROME_EPOCH) * 1000000)


def _seal_v10_raw(password, raw, rounds=1003):
    """Encrypt one cookie plaintext. None when the cipher library is absent.

    Mac Chrome derives the key with 1003 rounds. Linux Chrome uses 1 round.
    """
    try:
        from hashlib import pbkdf2_hmac
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception:
        return None
    try:
        pad = 16 - (len(raw) % 16)
        block = bytes(raw) + bytes([pad]) * pad
        key = pbkdf2_hmac("sha1", str(password).encode("utf-8"), b"saltysalt", int(rounds), 16)
        enc = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).encryptor()
        return b"v10" + enc.update(block) + enc.finalize()
    except Exception:
        return None


def seal_v10(password, text):
    """The inverse of decrypt_v10 for a plain value. None when the cipher library is absent."""
    return _seal_v10_raw(password, str(text).encode("utf-8"))


def _cookie_text(body, host=None):
    """The cookie value inside unpadded Chrome plaintext.

    Database version 24 stores SHA256(host_key) in front of the value. An older
    cookie is the value alone. A digest that is not this host is not the value.
    """
    if host is not None and len(body) > 32:
        digest = hashlib.sha256(str(host).encode("utf-8")).digest()
        if body[:32] == digest:
            body = body[32:]
    text = body.decode("utf-8")
    if not text or any(c in text for c in (";", "\r", "\n")):
        return None
    return text


def decrypt_v10(blob, password, host=None, rounds=1003):
    """Open one Chrome v10 cookie. Any other prefix, or a failed open, is None.

    host is the row host_key. Later Chrome stores bind the value to SHA256 of
    that host. Without the host, only a plain value opens. rounds is 1003 on
    Mac Chrome and 1 on Linux Chrome.
    """
    if not isinstance(blob, (bytes, bytearray)) or blob[:3] != b"v10" or not password:
        return None
    try:
        from hashlib import pbkdf2_hmac
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception:
        return None
    try:
        key = pbkdf2_hmac("sha1", str(password).encode("utf-8"), b"saltysalt", int(rounds), 16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(b" " * 16))
        dec = cipher.decryptor()
        raw = dec.update(bytes(blob[3:])) + dec.finalize()
        pad = raw[-1]
        if not isinstance(pad, int):
            pad = ord(pad)
        if pad < 1 or pad > 16 or raw[-pad:] != bytes([pad]) * pad:
            return None
        text = _cookie_text(raw[:-pad], host)
    except Exception:
        return None
    return text


def _aes_sbox():
    """The AES S-box, built once. The first byte is 0x63."""
    box = getattr(_aes_sbox, "_box", None)
    if box is not None:
        return box

    def mul(a, b):
        p = 0
        for _ in range(8):
            if b & 1:
                p ^= a
            a = ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF
            b >>= 1
        return p

    out = [0] * 256
    for x in range(256):
        inv = 0 if x == 0 else next(i for i in range(256) if mul(x, i) == 1)
        y = inv
        for shift in (1, 2, 3, 4):
            y ^= ((inv << shift) | (inv >> (8 - shift))) & 0xFF
        out[x] = y ^ 0x63
    box = bytes(out)
    _aes_sbox._box = box
    return box


def _aes_encryptor(key):
    """AES block encrypt for a 16 or 32 byte key. -> one 16-byte block in, one out."""
    nk = len(key) // 4
    nr = {4: 10, 8: 14}[nk]
    sbox = _aes_sbox()
    rcon = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)
    words = [list(key[i:i + 4]) for i in range(0, len(key), 4)]
    for i in range(nk, 4 * (nr + 1)):
        temp = words[i - 1][:]
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [sbox[b] for b in temp]
            temp[0] ^= rcon[i // nk]
        elif nk > 6 and i % nk == 4:
            temp = [sbox[b] for b in temp]
        words.append([a ^ b for a, b in zip(words[i - nk], temp)])

    def encrypt(block):
        st = [[block[r + 4 * c] for c in range(4)] for r in range(4)]

        def add(rnd):
            for c in range(4):
                for r in range(4):
                    st[r][c] ^= words[rnd * 4 + c][r]

        def mix_col(col):
            return (
                _gcm_mul8(col[0], 2) ^ _gcm_mul8(col[1], 3) ^ col[2] ^ col[3],
                col[0] ^ _gcm_mul8(col[1], 2) ^ _gcm_mul8(col[2], 3) ^ col[3],
                col[0] ^ col[1] ^ _gcm_mul8(col[2], 2) ^ _gcm_mul8(col[3], 3),
                _gcm_mul8(col[0], 3) ^ col[1] ^ col[2] ^ _gcm_mul8(col[3], 2),
            )

        add(0)
        for rnd in range(1, nr):
            for r in range(4):
                for c in range(4):
                    st[r][c] = sbox[st[r][c]]
            st = [st[r][r:] + st[r][:r] for r in range(4)]
            for c in range(4):
                mixed = mix_col([st[r][c] for r in range(4)])
                for r in range(4):
                    st[r][c] = mixed[r]
            add(rnd)
        for r in range(4):
            for c in range(4):
                st[r][c] = sbox[st[r][c]]
        st = [st[r][r:] + st[r][:r] for r in range(4)]
        add(nr)
        out = bytearray(16)
        for r in range(4):
            for c in range(4):
                out[r + 4 * c] = st[r][c]
        return bytes(out)

    return encrypt


def _gcm_mul8(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        a = ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF
        b >>= 1
    return p


def _gcm_mul128(x, y):
    z = 0
    v = x
    poly = 0xE1000000000000000000000000000000
    for i in range(128):
        if (y >> (127 - i)) & 1:
            z ^= v
        if v & 1:
            v = (v >> 1) ^ poly
        else:
            v >>= 1
    return z


def _aes_gcm_open(key, nonce, ciphertext, tag):
    """Open one AES-GCM blob. A bad tag is None. No extra library.

    The nonce is 12 bytes and the tag is 16. Chrome on Windows seals a v10
    cookie this way, with the raw key, not with a password.
    """
    if len(key) not in (16, 32) or len(nonce) != 12 or len(tag) != 16:
        return None
    if not isinstance(ciphertext, (bytes, bytearray)):
        return None
    encrypt = _aes_encryptor(bytes(key))
    auth = int.from_bytes(encrypt(b"\x00" * 16), "big")
    y = 0
    data = bytes(ciphertext)
    if len(data) % 16:
        data = data + (b"\x00" * (16 - len(data) % 16))
    for i in range(0, len(data), 16):
        # Sixteen bytes is the cipher block. Take the tail so this is not a guessed window.
        block = data[i:][:16]
        y = _gcm_mul128(y ^ int.from_bytes(block, "big"), auth)
    length = (0).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    y = _gcm_mul128(y ^ int.from_bytes(length, "big"), auth)
    expect = int.from_bytes(encrypt(nonce + b"\x00\x00\x00\x01"), "big") ^ y
    if expect.to_bytes(16, "big") != bytes(tag):
        return None
    out = bytearray()
    counter = 2
    body = bytes(ciphertext)
    for i in range(0, len(body), 16):
        stream = encrypt(nonce + counter.to_bytes(4, "big"))
        chunk = body[i:][:16]
        out += bytes(a ^ b for a, b in zip(chunk, stream))
        counter += 1
    return bytes(out)


def decrypt_windows_gcm(blob, key, host=None):
    """Open one Windows Chrome v10 or v11 cookie. Any other prefix is None.

    The key is the raw AES key. A v20 blob stays closed: that seal belongs to
    Chrome itself, and this desk does not pretend to be Chrome. The key and
    the value are not logged.
    """
    if not isinstance(blob, (bytes, bytearray)) or not isinstance(key, (bytes, bytearray)):
        return None
    if bytes(blob[:3]) not in (b"v10", b"v11") or len(blob) < 31 or len(key) not in (16, 32):
        return None
    try:
        raw = _aes_gcm_open(bytes(key), bytes(blob[3:15]), bytes(blob[15:-16]), bytes(blob[-16:]))
        if raw is None:
            return None
        return _cookie_text(raw, host)
    except Exception:
        return None


def cookie_header_from_rows(rows, password, now_utc=None, decrypt=None, rounds=1003):
    """Build a Cookie header from rows whose host is d2jsp. Other hosts are ignored.

    rows are (host_key, name, encrypted_value, expires_utc). An expired row is
    dropped. decrypt defaults to decrypt_v10. -> (header or None, reason)
    reason is ok, need-login, or chrome-unread.
    """
    def open_one(blob, host):
        if decrypt is not None:
            return decrypt(blob)
        return decrypt_v10(blob, password, host, rounds=rounds)

    now = _chrome_now(now_utc)
    pairs = []
    saw_host = False
    failed = False
    for host, name, blob, expires in rows:
        if not _d2jsp_host(host):
            continue
        saw_host = True
        try:
            exp = int(expires or 0)
        except (TypeError, ValueError):
            exp = 0
        if exp and exp <= now:
            continue
        value = open_one(blob, host)
        if not value:
            failed = True
            continue
        nm = str(name or "")
        if not nm or any(c in nm for c in ("=", ";", " ", "\r", "\n")):
            continue
        pairs.append(nm + "=" + value)
    if pairs:
        return "; ".join(pairs), "ok"
    if saw_host and failed:
        return None, "chrome-unread"
    if saw_host:
        return None, "need-login"
    return None, "need-login"


def _cookie_db_path():
    if sys.platform != "darwin":
        return None
    root = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Google", "Chrome", "Default")
    for rel in ("Cookies", os.path.join("Network", "Cookies")):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return None


def _read_rows(db_path):
    """Read the cookie database with no copy on disk. -> rows

    Chrome keeps the live file locked, so the file is opened read-only and
    immutable and backed up into an in-memory database, which is read there.
    REG-2492: the backup used to go to a d2jsp-cookies-*.db file in $TMPDIR,
    removed only in a finally, so a console killed mid-read left every site's
    encrypted cookies on disk.
    """
    uri = "file:" + urllib.parse.quote(db_path, safe="/") + "?immutable=1"
    src = sqlite3.connect(uri, uri=True)
    try:
        dst = sqlite3.connect(":memory:")
        try:
            src.backup(dst)
            rows = list(dst.execute(
                "select host_key, name, encrypted_value, expires_utc from cookies"
            ))
        finally:
            dst.close()
    finally:
        src.close()
    return rows


def _linux_cookie_dbs():
    """Cookie databases under the Linux Chrome and Chromium profiles. Default first."""
    home = os.path.expanduser("~")
    roots = (
        os.path.join(home, ".config", "google-chrome"),
        os.path.join(home, ".config", "chromium"),
    )
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            names = list(os.listdir(root))
        except OSError:
            continue
        names.sort(key=lambda name: (name != "Default", name))
        for name in names:
            base = os.path.join(root, name)
            for rel in ("Cookies", os.path.join("Network", "Cookies")):
                path = os.path.join(base, rel)
                if os.path.isfile(path):
                    found.append(path)
                    break
    return found


def _linux_chrome_passwords(run=None, tool=None):
    """Keyring secrets for Chrome, then Chrome's own published fallback.

    The fallback word is the one Chromium uses when the keyring has no secret.
    It is not a password this desk chooses. Nothing returned here is logged.
    """
    found = []
    if tool is None:
        tool = shutil.which("secret-tool")
    if tool:
        runner = run or subprocess.run
        for app in ("chrome", "chromium"):
            try:
                proc = runner(
                    [tool, "lookup", "application", app],
                    capture_output=True, timeout=8,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if getattr(proc, "returncode", 1) != 0:
                continue
            text = (getattr(proc, "stdout", b"") or b"").decode("utf-8", "replace").strip("\n")
            if text and text not in found:
                found.append(text)
    if "peanuts" not in found:
        found.append("peanuts")
    return found


def _linux_cookie_header(now_utc=None, paths=None, passwords=None):
    """A d2jsp cookie header from a Linux Chrome profile, or a reason."""
    stores = _linux_cookie_dbs() if paths is None else list(paths)
    if not stores:
        return None, "chrome-unread"
    secrets = _linux_chrome_passwords() if passwords is None else list(passwords)
    saw_fail = False
    saw_rows = False
    for path in stores:
        try:
            rows = _read_rows(path)
        except (OSError, sqlite3.Error):
            continue
        if rows:
            saw_rows = True
        for password in secrets:
            header, reason = cookie_header_from_rows(
                rows, password, now_utc=now_utc, rounds=1,
            )
            if header:
                return header, "ok"
            if reason == "chrome-unread":
                saw_fail = True
    if saw_fail:
        return None, "chrome-unread"
    if saw_rows:
        return None, "need-login"
    return None, "chrome-unread"


def _dpapi_unprotect(blob):
    """Open one current-user DPAPI blob. None off Windows, or when it fails.

    The plaintext is a key or an old cookie value. It is not logged.
    """
    if sys.platform != "win32" or not isinstance(blob, (bytes, bytearray)) or not blob:
        return None
    try:
        import ctypes
        raw = bytes(blob)
        held = ctypes.create_string_buffer(raw, len(raw))

        class _Blob(ctypes.Structure):
            _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_char))]

        incoming = _Blob(len(raw), ctypes.cast(held, ctypes.POINTER(ctypes.c_char)))
        outgoing = _Blob()
        crypt32 = ctypes.windll.crypt32
        crypt32.CryptUnprotectData.restype = ctypes.c_int
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(incoming), None, None, None, None, 0, ctypes.byref(outgoing),
        )
        if not ok:
            return None
        try:
            return ctypes.string_at(outgoing.pbData, outgoing.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(outgoing.pbData)
    except Exception:
        return None


def _windows_key_from_state(state_text, unprotect):
    """The raw AES key inside Chrome Local State. The app-bound key is ignored."""
    try:
        data = json.loads(state_text)
    except Exception:
        return None
    enc = (data.get("os_crypt") or {}).get("encrypted_key")
    if not isinstance(enc, str) or not enc:
        return None
    try:
        raw = base64.b64decode(enc)
    except Exception:
        return None
    if raw.startswith(b"DPAPI"):
        raw = raw[5:]
    if not raw:
        return None
    try:
        key = unprotect(raw)
    except Exception:
        return None
    if not isinstance(key, (bytes, bytearray)) or len(key) not in (16, 32):
        return None
    return bytes(key)


def _windows_cookie_dbs(root=None):
    """Cookie databases under the Windows Chrome profile. Default first.

    An absent profile is an empty list. A list that fails is None, so a caller
    can tell could-not-ask from a profile that holds nothing.
    """
    if root is None:
        if sys.platform != "win32":
            return []
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            return []
        root = os.path.join(local, "Google", "Chrome", "User Data")
    if not os.path.isdir(root):
        return []
    try:
        names = list(os.listdir(root))
    except OSError:
        return None
    names.sort(key=lambda name: (name != "Default", name))
    found = []
    for name in names:
        base = os.path.join(root, name)
        if not os.path.isdir(base):
            continue
        for rel in (os.path.join("Network", "Cookies"), "Cookies"):
            path = os.path.join(base, rel)
            if os.path.isfile(path):
                found.append(path)
                break
    return found


def _windows_aes_key(unprotect):
    local = os.environ.get("LOCALAPPDATA") or ""
    path = os.path.join(local, "Google", "Chrome", "User Data", "Local State")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    return _windows_key_from_state(text, unprotect)


def _open_windows_value(blob, key, host, unprotect):
    if isinstance(blob, (bytes, bytearray)) and bytes(blob[:3]) in (b"v10", b"v11"):
        if not key:
            return None
        return decrypt_windows_gcm(blob, key, host)
    if isinstance(blob, (bytes, bytearray)) and bytes(blob[:4]) == b"\x01\x00\x00\x00":
        try:
            raw = unprotect(bytes(blob))
        except Exception:
            return None
        if not isinstance(raw, (bytes, bytearray)):
            return None
        return _cookie_text(bytes(raw), host)
    return None


def _windows_rows_to_header(rows, key, now_utc, unprotect):
    now = _chrome_now(now_utc)
    pairs = []
    saw_host = False
    failed = False
    locked = True
    for host, name, blob, expires in rows:
        if not _d2jsp_host(host):
            continue
        saw_host = True
        try:
            exp = int(expires or 0)
        except (TypeError, ValueError):
            exp = 0
        if exp and exp <= now:
            continue
        value = _open_windows_value(blob, key, host, unprotect)
        if not value:
            failed = True
            locked = locked and isinstance(blob, (bytes, bytearray)) and bytes(blob[:3]) == b"v20"
            continue
        nm = str(name or "")
        if not nm or any(c in nm for c in ("=", ";", " ", "\r", "\n")):
            continue
        pairs.append(nm + "=" + value)
    if pairs:
        return "; ".join(pairs), "ok"
    if saw_host and failed:
        return None, ("chrome-locked" if locked else "chrome-unread")   # v3861 - v20: Chrome keeps it to itself
    if saw_host:
        return None, "need-login"
    return None, "need-login"


def _own_login_header(now_utc=None, root=None, unprotect=None):
    """v3861 - the d2jsp cookie header from the profile this console owns. -> (header | None, reason)

    reason: ok · need-login (the profile is there, no d2jsp sign-in in it) · login-open (its Chrome holds the cookie file:
    the sign-in window is open) · no-profile (never opened on this PC)"""
    root = login_profile_dir() if root is None else root
    if not root or not os.path.isdir(root):
        return None, "no-profile"
    dbs = _windows_cookie_dbs(root=root) or []
    if not dbs:
        return None, "need-login"
    opener = unprotect or _dpapi_unprotect
    try:
        with open(os.path.join(root, "Local State"), encoding="utf-8") as fh:
            key = _windows_key_from_state(fh.read(), opener)
    except OSError:
        key = None
    try:
        rows = _read_rows(dbs[0])
    except (OSError, sqlite3.Error):
        return None, "login-open"
    header, reason = _windows_rows_to_header(rows, key, now_utc, opener)
    return (header, "ok") if header else (None, reason)


def _windows_cookie_header(now_utc=None, paths=None, key=None, unprotect=None, state_text=None):
    """A d2jsp cookie header from a Windows Chrome profile, or a reason."""
    own = None
    if paths is None and key is None and state_text is None:
        # v3861 - the profile this console owns is asked first: its cookies are the ones it can open
        own_header, own = _own_login_header(now_utc, unprotect=unprotect)
        if own_header:
            return own_header, "ok"
        if own == "login-open":
            return None, "login-open"
    stores = list(paths) if paths is not None else _windows_cookie_dbs()
    if not stores:
        return None, ("need-login" if own == "need-login" else "chrome-unread")
    opener = unprotect or _dpapi_unprotect
    if key is None and state_text is not None:
        key = _windows_key_from_state(state_text, opener)
    elif key is None and paths is None:
        key = _windows_aes_key(opener)
    saw_fail = False
    saw_rows = False
    saw_locked = False
    for path in stores:
        try:
            rows = _read_rows(path)
        except (OSError, sqlite3.Error):
            continue
        header, reason = _windows_rows_to_header(rows, key, now_utc, opener)
        if header:
            return header, "ok"
        if reason == "chrome-unread":
            saw_fail = True
        elif reason == "chrome-locked":
            saw_locked = True
        elif reason == "need-login":
            saw_rows = True
    if saw_locked:
        return None, "chrome-locked"        # v3861 - the actionable word: sign in through the console's own window
    if saw_fail:
        return None, "chrome-unread"
    if saw_rows or own == "need-login":
        return None, "need-login"
    return None, "chrome-unread"


def _mac_cookie_header(now_utc=None):
    """The d2jsp cookie header from this Mac's Chrome, or a reason it could not be read."""
    path = _cookie_db_path()
    if not path:
        return None, "chrome-unread"
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage", "-a", "Chrome"],
            capture_output=True, timeout=60,
        )
    except Exception:
        return None, "chrome-unread"
    if proc.returncode != 0:
        return None, "chrome-unread"
    password = proc.stdout.decode("utf-8", "replace").strip()
    if not password:
        return None, "chrome-unread"
    try:
        rows = _read_rows(path)
    except Exception:
        return None, "chrome-unread"
    return cookie_header_from_rows(rows, password, now_utc=now_utc)


def live_cookie_header(now_utc=None):
    """The d2jsp cookie header from this machine's Chrome, or a reason it could not be read."""
    if sys.platform == "darwin":
        return _mac_cookie_header(now_utc)
    if sys.platform.startswith("linux"):
        return _linux_cookie_header(now_utc)
    if sys.platform == "win32":
        return _windows_cookie_header(now_utc)
    return None, "chrome-unread"


def d2jsp_login_status(now_utc=None):
    """Whether this machine's own Chrome is signed into d2jsp.

    The cookie header is read and dropped. It is not returned, logged, or stored.
    Another console reads the Chrome of the person at that computer. The room
    asks this every time it opens, so the scratch Chromes and cookie copies a
    killed console left behind are swept here too (REG-2492).
    """
    try:
        _sweep_stale_scratch()
    except Exception:
        pass
    _header, reason = live_cookie_header(now_utc)
    if reason == "ok":
        return {
            "ok": True,
            "state": "on",
            "kind": "on",
            "why": "Signed into d2jsp through the Chrome login on this machine.",
        }
    if reason == "need-login":
        return {
            "ok": True,
            "state": "off",
            "kind": "signed-out",
            "needsLogin": True,
            "why": "This machine is not signed into d2jsp. Click the lamp to sign in"
                   + (" - then close that window: Chrome saves the sign-in when it closes." if sys.platform == "win32"
                      else "."),
        }
    if reason == "chrome-locked":
        return {
            "ok": True,
            "state": "off",
            "kind": "signed-out",
            "needsLogin": True,
            "why": "This PC's Chrome keeps its d2jsp sign-in locked to Chrome itself, so the console signs in through its "
                   "own d2jsp window. Click the lamp, sign in there once, then close that window.",
        }
    if reason == "login-open":
        return {
            "ok": True,
            "state": "off",
            "kind": "signing-in",
            "needsLogin": True,
            "why": "The console's d2jsp window is open. Sign in there, then close it - the lamp turns green once it is "
                   "closed.",
        }
    return {
        "ok": True,
        "state": "unknown",
        "kind": "unread",
        "why": "This machine could not read the Chrome login.",
    }


class _Compose(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.has_logout = False
        self.has_subject = False
        self.has_message = False
        self.has_post = False
        self.post_value = "Post"

    def handle_starttag(self, tag, attrs):
        d = {}
        for key, val in attrs:
            d[key] = val or ""
        if tag == "a" and "mode=logout" in d.get("href", ""):
            self.has_logout = True
        if tag == "input":
            name = d.get("name", "")
            if name == "subject":
                self.has_subject = True
            if name == "post":
                self.has_post = True
                if d.get("value"):
                    self.post_value = d["value"]
            if name and d.get("type", "text") == "hidden" and len(self.hidden) < 30:
                self.hidden.append((name, d.get("value", "")))
        if tag == "textarea" and d.get("name") == "message":
            self.has_message = True
        if tag == "button" and d.get("name") == "post":
            self.has_post = True
            if d.get("value"):
                self.post_value = d["value"]


def parse_compose(html):
    """The compose page. -> {reason, fields?, post_value?}

    reason is unread, need-login, form-unknown, or ready.
    """
    if isinstance(html, (bytes, bytearray)):
        text = html.decode("utf-8", "replace")
    else:
        text = str(html or "")
    low = text.lower()
    if (not text) or ("just a moment" in low) or ("cf-browser-verification" in low):
        return {"reason": "unread"}
    if "not currently logged in" in low:
        return {"reason": "need-login"}
    form = _Compose()
    try:
        form.feed(text)
    except Exception:
        return {"reason": "form-unknown"}
    if not form.has_logout:
        return {"reason": "need-login"}
    if not (form.has_subject and form.has_message and form.has_post):
        return {"reason": "form-unknown"}
    return {"reason": "ready", "fields": form.hidden, "post_value": form.post_value}


def _priced(subject, body):
    # A sale says Selling. WTS remains a sale from a page that has not reloaded.
    head = str(subject or "")
    if not (head.startswith("Selling ") or head.startswith("WTS ")):
        return False
    if len(subject) > 140 or len(body) > 4000:
        return False
    lines = [ln.strip() for ln in str(body or "").splitlines() if ln.strip()]
    if not lines or not _PRICE_LINE.match(lines[-1]):
        return False
    try:
        return float(lines[-1].split()[0]) > 0
    except ValueError:
        return False


def _on_forum(url):
    if not url:
        return False
    if url.startswith("/") and not url.startswith("//"):
        return True
    try:
        parts = urllib.parse.urlparse(url)
    except Exception:
        return False
    return parts.scheme in ("https", "") and parts.netloc in (_HOST, "")


def _topic(url):
    if not _on_forum(url):
        return False
    path = url
    try:
        path = urllib.parse.urlparse(url).path or url
    except Exception:
        path = url
    return "topic.php" in path


def _transport(method, url, headers, data):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=25) as resp:
            return resp.status, {k: v for k, v in resp.headers.items()}, resp.read(200000)
    except urllib.error.HTTPError as exc:
        # None is "this header was not read". An empty page is not a receipt.
        loc = None
        try:
            loc = exc.headers.get("Location")
        except Exception:
            loc = None
        raw = None
        try:
            raw = exc.read(200000)
        except Exception:
            raw = None
        return exc.code, {"Location": loc or ""}, raw or b""


def _chrome_bin(platform=None, which=None):
    """The Chrome executable on this machine. None when it is not installed."""
    plat = sys.platform if platform is None else platform
    if plat == "darwin":
        path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.isfile(path):
            return path
        return None
    if str(plat).startswith("linux"):
        look = which or shutil.which
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            found = look(name)
            if found:
                return found
        return None
    if plat == "win32":
        if which is not None:
            return which("chrome") or None
        if plat != sys.platform:
            return None
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            path = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(path):
                return path
    return None


def _windows_chrome_version(binary, listdir=None):
    """v3862 - the installed Chrome's version on Windows, WITHOUT running Chrome. -> "156.0.8078.80" | None

    ⚠ `chrome.exe --version` DOES NOT PRINT A VERSION ON WINDOWS - IT OPENS A BROWSER WINDOW. MEASURED 2026-11-05 on
    the old ALT: his console's background proof ran the d2jsp desk law, the law reached this read, and every run launched
    `chrome.exe --version` as a real browser (pid 10684, the user's own profile, ~20 renderers); run()'s 5 s timeout
    then killed it, so Chrome kept opening and closing a page - "chrome keeps reopening a page randomly" (Elad). The
    same read sat under every d2jsp price on every Windows PC. The installer keeps one folder per version beside
    chrome.exe (Application\\156.0.8078.80 on that PC), so the version is a directory listing; the newest wins
    during an update, and nothing readable is None (the caller keeps its fallback)."""
    if not binary:
        return None
    try:
        names = (listdir or os.listdir)(os.path.dirname(binary))
    except OSError:
        return None
    vers = [n for n in names if re.fullmatch(r"\d+(?:\.\d+){2,3}", str(n))]
    if not vers:
        return None
    return max(vers, key=lambda v: tuple(int(x) for x in v.split(".")))


def chrome_user_agent(platform=None, version=None):
    """The installed Chrome's own signature. A clearance cookie is bound to it.

    When the version cannot be read, the header still names Chrome and a
    challenge page stays unread. It is not reported as a post. Mac, Linux and
    Windows name themselves, because a cookie from one does not travel as another.

    REG-2575: a version read that does not answer in 5 s is a version that cannot be read. Only
    OSError was caught, so subprocess.TimeoutExpired rose through _headers: the send answered
    "unread" before any page was fetched, and the quote raised. CI's loaded runner, where
    `google-chrome --version` took longer than 5 s, failed the desk law that way.
    """
    plat = sys.platform if platform is None else platform
    if version is None:
        version = "131.0.0.0"
        if plat == "darwin" and plat == sys.platform:
            try:
                proc = subprocess.run(
                    ["defaults", "read",
                     "/Applications/Google Chrome.app/Contents/Info.plist",
                     "CFBundleShortVersionString"],
                    capture_output=True, timeout=5, text=True,
                    encoding="utf-8", errors="replace",
                )
            except (OSError, subprocess.SubprocessError):
                proc = None
            if proc is not None and proc.returncode == 0:
                got = (proc.stdout or "").strip()
                if re.fullmatch(r"\d+(?:\.\d+){2,3}", got):
                    version = got
        elif str(plat).startswith("linux") and plat == sys.platform:
            binary = _chrome_bin(platform=plat)
            if binary:
                try:
                    proc = subprocess.run(
                        [binary, "--version"],
                        capture_output=True, timeout=5, text=True,
                        encoding="utf-8", errors="replace",
                    )
                except (OSError, subprocess.SubprocessError):
                    proc = None
                if proc is not None and proc.returncode == 0:
                    got = (proc.stdout or "").strip().rsplit(" ", 1)[-1]
                    if re.fullmatch(r"\d+(?:\.\d+){2,3}", got):
                        version = got
        elif plat == "win32" and plat == sys.platform:
            version = _windows_chrome_version(_chrome_bin(platform=plat)) or version
    if str(plat).startswith("linux"):
        system = "X11; Linux x86_64"
    elif plat == "win32":
        system = "Windows NT 10.0; Win64; x64"
    else:
        system = "Macintosh; Intel Mac OS X 10_15_7"
    return (
        "Mozilla/5.0 (%s) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36"
    ) % (system, version)


def _open_chrome_login(platform=None, run=None, which=None, popen=None, env=None):
    """Open the forum login in this machine's own Chrome.

    Nothing from a draft is in the URL. The page opens in the Chrome this
    console already reads, not a debug port and not another computer's login.
    On Windows that is the profile this console owns (login_profile_dir, v3861).

    v3861 - ⚠ STARTED AND LEFT RUNNING. MEASURED 2026-11-05 on the work ALT: run(argv, timeout=5) on a Chrome that was not
    already open made THAT process the browser, which never exits, so the timeout killed it (TimeoutExpired after 6.6 s,
    headless, a throwaway profile) - "it opened a login but it was bugged it kept closing" (Elad). Only `open -a` (the
    Mac) returns at once and is still waited on.
    """
    plat = sys.platform if platform is None else platform
    runner = run or subprocess.run
    if plat == "darwin":
        argv = ["open", "-a", "Google Chrome", LOGIN_URL]
        try:
            proc = runner(argv, capture_output=True, timeout=5)
            return getattr(proc, "returncode", 1) == 0
        except Exception:
            return False
    if str(plat).startswith("linux"):
        binary = _chrome_bin(platform=plat, which=which)
        if not binary:
            return False
        argv = [binary, "--no-first-run", LOGIN_URL]
        kw = {"start_new_session": True}
    elif plat == "win32":
        binary = _chrome_bin(platform=plat, which=which)
        if not binary:
            return False
        own = login_profile_dir(platform=plat, env=env)
        if own and popen is None:
            try:
                os.makedirs(own, exist_ok=True)        # the real launch only: a law hands its own popen and env
            except OSError:
                pass
        argv = [binary] + (["--user-data-dir=%s" % own, "--no-first-run", "--no-default-browser-check"] if own else []) \
            + [LOGIN_URL]
        kw = {"creationflags": 0x00000008 | 0x00000200}          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        return False
    try:
        (popen or subprocess.Popen)(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, **kw)
        return True
    except Exception:
        return False

def open_d2jsp_login():
    """Open this machine's d2jsp login. The answer says whether the page opened."""
    try:
        opened = bool(_open_chrome_login())
    except Exception:
        opened = False
    if opened:
        return {
            "ok": True,
            "opened": True,
            "why": "The d2jsp login is open in Chrome on this machine.",
        }
    return {
        "ok": False,
        "opened": False,
        "why": "This machine could not open the d2jsp login.",
    }


def _headers(cookie):
    return {
        "User-Agent": chrome_user_agent(),
        "Accept": "text/html",
        "Cookie": cookie,
        "Referer": COMPOSE_URL,
    }


_QUOTE_JS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "functions", "api", "d2jsp_quote.js",
)


def _quote_unknown(item, read_at, reason):
    return {
        "item": str(item or ""),
        "fg": None,
        "low": None,
        "high": None,
        "n": 0,
        "readAt": read_at,
        "reason": reason,
        "board": QUOTE_BOARD,
    }


def _read_quote_parser():
    with open(_QUOTE_JS, encoding="utf-8") as fh:
        src = fh.read()
    mark = "/* ⟦D2JSP QUOTE BEGIN⟧ */\n"
    start = src.index(mark) + len(mark)
    end = src.index("\n/* ⟦D2JSP QUOTE END⟧ */", start)
    return src[start:end]


def _public_posts(raw):
    """v3844 - the evidence under a reading, cleaned for the desk: at most 40 posts, each with its fg, its day, a link
    only when it is a forums.d2jsp.org address, the roll as read, and its weight. The post's own words stay on the forum (the answer is the reading, never the page): the link opens
    them."""
    out = []
    for r in (raw if isinstance(raw, list) else [])[:40]:
        if not isinstance(r, dict):
            continue
        try:
            fg = float(r.get("fg"))
            w = float(r.get("w", 1))
        except (TypeError, ValueError):
            continue
        if fg <= 0:
            continue
        link = str(r.get("link") or "")
        if not link.startswith("https://forums.d2jsp.org/"):
            link = ""
        roll = []
        for t in (r.get("roll") or [])[:4]:
            if isinstance(t, list) and all(isinstance(x, (int, float)) for x in t):
                roll.append([int(x) for x in t[:6]])
        row = {"fg": int(fg) if fg == int(fg) else fg, "day": str(r.get("day") or "")[:10], "link": link,
               "roll": roll, "w": max(0.0, min(1.0, w))}
        # v3845 - the compact roll columns ("+8 -9 4 40 28"), signed, in the item's own mod order; the desk maps them
        cols = r.get("cols")
        if (isinstance(cols, list) and 2 <= len(cols) <= 8
                and all(isinstance(x, (int, float)) and not isinstance(x, bool) and abs(x) < 10000 for x in cols)):
            row["cols"] = [int(x) for x in cols]
        mods = [str(x)[:30] for x in (r.get("mods") or [])[:12] if isinstance(x, str)]
        if mods:
            row["mods"] = mods
        if r.get("perfect") is True:   # v3849 - only a real True is the perfect tier
            row["perfect"] = True
        _o = r.get("out")
        if isinstance(_o, str) and _o.strip():   # v3845 second eye: only a real reason string is a label (True/1/{} are not)
            row["out"] = _o.strip()[:80]
        out.append(row)
    return out


def _public_fields(parsed, item, read_at):
    if not isinstance(parsed, dict):
        return _quote_unknown(item, read_at, "unread")
    reason = parsed.get("reason")
    if reason not in ("read", "no prices", "need-login", "unread"):
        reason = "unread"
    fg = None
    low = None
    high = None
    n = 0
    if reason == "read":
        try:
            fg = float(parsed.get("fg"))
        except (TypeError, ValueError):
            return _quote_unknown(item, read_at, "unread")
        if fg <= 0:
            return _quote_unknown(item, read_at, "unread")
        if fg == int(fg):
            fg = int(fg)
        low = parsed.get("low")
        high = parsed.get("high")
        try:
            n = int(parsed.get("n"))
        except (TypeError, ValueError):
            return _quote_unknown(item, read_at, "unread")
    out = {
        "item": str(item or ""),
        "fg": fg,
        "low": low,
        "high": high,
        "n": n,
        "readAt": parsed.get("readAt") or read_at,
        "reason": reason,
        "board": QUOTE_BOARD,
        "posts": _public_posts(parsed.get("posts")) if reason == "read" else [],
    }
    try:
        skipped = int(parsed.get("skipped"))
    except (TypeError, ValueError):
        skipped = 0
    if skipped > 0:
        out["skipped"] = skipped
    return out


def parse_public_quote(html, item, read_at, node_run=None):
    """Run the quote parser in functions/api/d2jsp_quote.js. No number is filled in here."""
    if node_run is None:
        node = shutil.which("node")
        if not node:
            return _quote_unknown(item, read_at, "unread")

        def node_run(prog, page):
            return subprocess.run(
                [node, "-e", prog],
                input=page,
                capture_output=True,
                timeout=20,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
    try:
        parser = _read_quote_parser()
    except (OSError, ValueError):
        return _quote_unknown(item, read_at, "unread")
    prog = (
        parser
        + "\nprocess.stdout.write(JSON.stringify(d2jspRead("
        + "require('fs').readFileSync(0,'utf8'),"
        + json.dumps(str(item or "")) + ","
        + json.dumps(str(read_at or ""))
        + ")));\n"
    )
    try:
        proc = node_run(prog, str(html or ""))
    except (OSError, subprocess.SubprocessError):
        # REG-2576: a node that does not answer in 20 s is a page that was not read, never a raise.
        return _quote_unknown(item, read_at, "unread")
    if getattr(proc, "returncode", 1) != 0:
        return _quote_unknown(item, read_at, "unread")
    try:
        parsed = json.loads(getattr(proc, "stdout", "") or "")
    except (TypeError, ValueError):
        return _quote_unknown(item, read_at, "unread")
    return _public_fields(parsed, item, read_at)


def _search_keywords(item, node_run=None):
    """v3843 - the words the search asks with, from the quote block's lexicon (d2jspSearchWords): the slang form
    traders write when there is one ("Harlequin Crest" -> "shako"), else the simplified name. With no node to run
    it, the name without its apostrophes, as before."""
    plain = re.sub(r"['’ʼ`]", "", str(item or ""))
    node = shutil.which("node") if node_run is None else None
    if node_run is None and not node:
        return plain
    try:
        prog = _read_quote_parser() + "\nprocess.stdout.write(String(d2jspSearchWords(" + json.dumps(str(item or "")) + ").query || ''));\n"
        if node_run is None:
            proc = subprocess.run([node, "-e", prog], capture_output=True, timeout=20, text=True,
                                  encoding="utf-8", errors="replace")
        else:
            proc = node_run(prog, "")
        if getattr(proc, "returncode", 1) == 0 and (getattr(proc, "stdout", "") or "").strip():
            return proc.stdout.strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return plain


def _search_url(item):
    """The forum's own post search for the Softcore non-ladder trading board (v3843; it was Switch Ladder)."""
    return "https://forums.d2jsp.org/search.php?c=7&f=%d&t=0" % QUOTE_BOARD


def _search_body(item):
    return urllib.parse.urlencode({"stext": _search_keywords(item)}).encode("utf-8")


def _challenge_page(page):
    text = str(page or "")
    if not text.strip():
        return True
    if re.search(r"Just a moment", text, re.I):
        return True
    return "cf-browser-verification" in text


def _cdp_call(ws, ident, method, params=None, wait=15):
    ws.send(json.dumps({"id": ident, "method": method, "params": params or {}}))
    end = time_now() + wait
    while time_now() < end:
        msg = json.loads(ws.recv())
        if msg.get("id") == ident:
            return msg
    raise OSError(method)


def time_now():
    import time
    return time.time()


_SCRATCH_PREFIXES = ("d2jsp-quote-", "d2jsp-post-")
_COOKIE_COPY_PREFIX = "d2jsp-cookies-"
_SCRATCH_STALE_S = 300  # 5 min — far beyond a normal op (under 2 min), so an in-flight profile is never swept
_ERE_SPECIAL = frozenset(".[]()*+?{}|^$\\")


def _ere(text):
    """text as a POSIX extended regular expression that matches it literally."""
    return "".join("\\" + c if c in _ERE_SPECIAL else c for c in str(text))


def _kill_profile_holders(profile):
    """SIGKILL every process whose command line names exactly this --user-data-dir.
    -> pids signalled, or None when pgrep could not be asked

    REG-2493: the pattern goes after `--`. Without it pgrep read `--user-data-dir=...` as an
    option of its own, printed its usage, exited 2 and listed nothing, so the REG-2190 sweep never
    killed a Chrome. The pattern ends at a space or at the end of the command line, so a profile
    whose path only starts with this one is not a match. Matched by that argument, never by a
    name, so his real Chrome can never be a target.

    REG-2498: a pgrep that could not run (none on this PC, or no answer in 5 s) is None, never [].
    [] says "no Chrome held it", which nobody measured."""
    try:
        out = subprocess.run(
            ["pgrep", "-f", "--", "--user-data-dir=" + _ere(profile) + "( |$)"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        ).stdout
    except Exception:
        return None
    hit = []
    for word in str(out or "").split():
        try:
            pid = int(word)
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            hit.append(pid)
        except Exception:
            pass
    return hit


def _stale(path, now):
    """True when path was last changed _SCRATCH_STALE_S or more before now."""
    try:
        return now - os.lstat(path).st_mtime >= _SCRATCH_STALE_S
    except OSError:
        return False


def _sweep_stale_scratch(now=None, tmp=None):
    """REG-2190 / REG-2492 — SWEEP WHAT A KILLED CONSOLE LEFT HOLDING HIS COOKIES. -> how many are gone

    Each op mkdtemps a d2jsp-quote-* / d2jsp-post-* profile and cleans it in its `finally`. But a
    console killed mid-op (kill -9, a relaunch) never reaches that finally, so the headless Chrome —
    which holds his decrypted d2jsp session — keeps running and its profile stays on disk. A console
    before REG-2492 also left d2jsp-cookies-* copies of the whole Chrome cookie database the same
    way. This runs before each scratch Chrome, whenever the room asks for the login state, and at
    console boot. It removes any of them last changed _SCRATCH_STALE_S or more ago (an in-flight
    one, seconds old, is never touched): a Chrome still holding a profile is SIGKILLed first, a
    cookie copy is removed with os.remove (rmtree cannot remove a file), and only what is actually
    gone afterwards is counted."""
    import glob as _glob
    now = time.time() if now is None else now
    root = tmp if tmp is not None else tempfile.gettempdir()
    base = _glob.escape(root)
    removed = 0
    for pref in _SCRATCH_PREFIXES:
        for d in _glob.glob(os.path.join(base, pref + "*")):
            if os.path.islink(d) or not os.path.isdir(d) or not _stale(d, now):
                continue
            _kill_profile_holders(d)
            shutil.rmtree(d, ignore_errors=True)
            if not os.path.lexists(d):
                removed += 1
    for f in _glob.glob(os.path.join(base, _COOKIE_COPY_PREFIX + "*")):
        if (os.path.isdir(f) and not os.path.islink(f)) or not _stale(f, now):
            continue
        try:
            os.remove(f)
        except OSError:
            pass
        if not os.path.lexists(f):
            removed += 1
    return removed


_IN_FLIGHT = {}
_IN_FLIGHT_LOCK = threading.Lock()


def _track_scratch(proc, profile):
    """Hold a scratch Chrome and its profile while it is in flight. -> the key _untrack_scratch takes"""
    key = object()
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT[key] = (proc, profile)
    return key


def _untrack_scratch(key):
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT.pop(key, None)


def _end_chrome(proc):
    """Kill a scratch Chrome with its renderers, and reap it.

    Its process group is its own pid (start_new_session). A browser that has already exited is
    only reaped: its pid may belong to another process by now."""
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def _reap_in_flight():
    """At interpreter exit: end every scratch Chrome this process started that is still in flight,
    and remove its profile, which holds his d2jsp session. -> how many there were

    REG-2492. atexit runs on a normal exit only. An os.execv relaunch, os._exit and kill -9 skip
    it; _sweep_stale_scratch takes what those leave, at the next boot or room open."""
    with _IN_FLIGHT_LOCK:
        held = list(_IN_FLIGHT.values())
        _IN_FLIGHT.clear()
    for proc, profile in held:
        _end_chrome(proc)
        shutil.rmtree(profile, ignore_errors=True)
    return len(held)


atexit.register(_reap_in_flight)


_START_WHY = {
    "websocket": "the websocket-client module is not installed for this console's Python",
    "no-chrome": "Chrome is not installed on this machine",
    "launch": "Chrome would not start",
    "devtools": "Chrome did not open its DevTools connection",
}


class ChromeStart(Exception):
    """The scratch Chrome did not come up, so nothing was opened and nothing was clicked.

    REG-2491: a missing websocket module raised ImportError out of the route, and a missing Chrome
    or a DevTools port that never answered read 'unread'. Now each is reason 'chrome-start' with
    a short why."""

    def __init__(self, key):
        Exception.__init__(self, key)
        self.key = str(key)
        self.why = _START_WHY.get(self.key, "Chrome did not start")


_SNAPSHOT_JS = (
    "JSON.stringify({href:location.href,ready:document.readyState,"
    "mark:!!window.__d2jspClicked,"
    "html:document.documentElement?document.documentElement.outerHTML:''})"
)


class _ErrorReply(OSError):
    """DevTools answered a script with a protocol error in place of a result.

    REG-2496: Chrome answers "Execution context was destroyed" when the page navigates away while
    the call is in flight, which a submit's own navigation can do. The script may have run, so this
    is no answer, never an empty one."""


class _Page(object):
    """The one tab of a scratch Chrome, driven over its DevTools socket. Nothing sent or read is logged.

    goto, act and snapshot are all a flow uses, so a law drives the same flow with a page made of
    strings and no browser."""

    def __init__(self, ws):
        self._ws = ws
        self._n = 0

    def call(self, method, params=None, wait=15):
        self._n += 1
        return _cdp_call(self._ws, self._n, method, params, wait=wait)

    def goto(self, url):
        self.call("Page.navigate", {"url": str(url)})

    def act(self, name, script):
        """Run one of the flow's scripts. -> its string answer, '' when the script threw

        Raises when the browser does not answer, which is not the same as answering nothing, and
        raises _ErrorReply when it answers with a protocol error: a fill answered that way may have
        clicked (REG-2496 - it used to read '', no click, and a post the board took read
        form-unknown)."""
        got = self.call("Runtime.evaluate", {"expression": script, "returnByValue": True}, wait=8)
        if not isinstance(got.get("result"), dict):
            raise _ErrorReply(str(name))
        res = got["result"]
        if res.get("exceptionDetails"):
            return ""
        val = (res.get("result") or {}).get("value")
        return val if isinstance(val, str) else ""

    def snapshot(self):
        """-> {href, ready, mark, html}; None when the page answered something else"""
        try:
            snap = json.loads(self.act("snapshot", _SNAPSHOT_JS) or "")
        except (ValueError, _ErrorReply):
            return None
        if not isinstance(snap, dict):
            return None
        return {
            "href": str(snap.get("href") or ""),
            "ready": str(snap.get("ready") or ""),
            "mark": bool(snap.get("mark")),
            "html": str(snap.get("html") or ""),
        }


def _free_port():
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _devtools_up(base, proc, wait_s=12):
    """True once Chrome's DevTools answers; False when it has not in wait_s, or the browser exited."""
    end = time.monotonic() + wait_s
    while time.monotonic() < end:
        if proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(base + "/json/version", timeout=2).close()
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _cookie_pairs(cookie):
    """(name, value) for each part of a Cookie header."""
    pairs = []
    for part in str(cookie or "").split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        if name:
            pairs.append((name, value))
    return pairs


@contextlib.contextmanager
def _scratch_chrome(cookie, prefix):
    """One headless Chrome on its own profile and its own port, with the d2jsp cookie set. -> its _Page

    The one start the search, the edit and the post share (REG-2490: it was copied three times).
    His open Chrome is not the one this starts, and no port is fixed. Raises ChromeStart before
    anything is opened when the websocket-client module is missing, Chrome is not installed or
    will not start, or its DevTools connection is not up in 12 s. The browser and its profile are
    held for the exit reaper while in flight, and killed and removed when the block ends."""
    try:
        import websocket
    except ImportError:
        raise ChromeStart("websocket")
    browser = _chrome_bin()
    if not browser:
        raise ChromeStart("no-chrome")
    _sweep_stale_scratch()
    prof = tempfile.mkdtemp(prefix=prefix)
    proc = None
    held = None
    ws = None
    try:
        port = _free_port()
        try:
            proc = subprocess.Popen(
                [browser, "--headless=new", "--disable-gpu", "--no-first-run",
                 "--no-default-browser-check", "--disable-blink-features=AutomationControlled",
                 "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % prof,
                 "--remote-allow-origins=*", "--window-size=1100,800", "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
            )
        except OSError:
            raise ChromeStart("launch")
        held = _track_scratch(proc, prof)
        base = "http://127.0.0.1:%d" % port
        if not _devtools_up(base, proc):
            raise ChromeStart("devtools")
        try:
            tab = json.loads(urllib.request.urlopen(
                urllib.request.Request(base + "/json/new?about:blank", method="PUT"),
                timeout=10,
            ).read().decode("utf-8", "replace"))
            ws = websocket.create_connection(
                tab["webSocketDebuggerUrl"], timeout=20, origin=base,
            )
            page = _Page(ws)
            page.call("Network.enable")
            page.call("Network.setUserAgentOverride", {"userAgent": chrome_user_agent()})
            for name, value in _cookie_pairs(cookie):
                page.call("Network.setCookie", {
                    "name": name,
                    "value": value,
                    "url": "https://forums.d2jsp.org/",
                    "domain": ".d2jsp.org",
                    "path": "/",
                    "secure": True,
                })
            page.call("Page.enable")
        except Exception:
            raise ChromeStart("devtools")
        yield page
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if proc is not None:
            _end_chrome(proc)
        shutil.rmtree(prof, ignore_errors=True)
        _untrack_scratch(held)


def _open_link_js(label):
    """Follow the page's own link whose text is exactly `label`, when it opens post.php.
    -> 'opened' | 'no-link'"""
    return (
        "(function(){var as=document.querySelectorAll('a');"
        "for(var i=0;i<as.length;i++){"
        "var label=(as[i].textContent||'').replace(/\\s+/g,' ').trim();"
        "if(label!==" + json.dumps(str(label)) + ")continue;"
        "var href=as[i].href||'';"
        "if(href.indexOf('/post.php')<0)continue;"
        "location.href=href;return 'opened';}"
        "return 'no-link';})()"
    )


def _fill_js(subject, text):
    """The board's form filled as a sale with no paid extras, and sent by its own button.
    -> 'clicked' | 'title' | 'no-form' | 'no-sell' | 'no-submit'

    A title past 50 characters is the board's own limit, so the form is not sent with one. The
    page is marked just before the click, so a document that loads after it is known to be new."""
    return (
        "(function(){var box=document.querySelector("
        + json.dumps('textarea[name="Post"]') + ");"
        "var title=document.querySelector("
        + json.dumps('input[name="ttitle"]') + ");"
        "if(!box||!title||!box.form)return 'no-form';"
        "var subject=" + json.dumps(str(subject or "")) + ";"
        "if(subject.length>50)return 'title';"
        "title.value=subject;box.value=" + json.dumps(str(text or "")) + ";"
        "var picked=false;var labs=document.querySelectorAll('label');"
        "for(var i=0;i<labs.length;i++){"
        "if((labs[i].textContent||'').indexOf('Selling Item')<0)continue;"
        "var input=document.getElementById(labs[i].htmlFor||'');"
        "if(input&&input.name==='sType'){input.checked=true;picked=true;}}"
        "if(!picked)return 'no-sell';"
        "var paid=['sItalic','sBold','sRed'];"
        "for(var p=0;p<paid.length;p++){"
        "var extra=box.form.querySelector('input[name=\"'+paid[p]+'\"]');"
        "if(extra)extra.checked=false;}"
        "var btn=box.form.querySelector("
        + json.dumps('input[name="submit"]') + ");"
        "if(!btn)return 'no-submit';"
        "window.__d2jspClicked=1;btn.click();return 'clicked';})()"
    )


_FORM_S = 25.0      # load the board, open the form, fill it and click
_RECEIPT_S = 35.0   # after the click, for the board to land on the new topic
_CHECK_S = 20.0     # then, for the board list to load once more
_TICK_S = 0.8
_NO_ANSWER = "?"    # a script was sent and the browser did not answer


def _board_url(board):
    return "https://forums.d2jsp.org/forum.php?f=%d" % int(board)


def _on_board(href, board):
    """The board's own topic list: forum.php?f=<board> on the forum host."""
    try:
        parts = urllib.parse.urlparse(str(href or ""))
        found = (urllib.parse.parse_qs(parts.query).get("f") or [""])[0]
        return (parts.scheme == "https" and parts.netloc == _HOST
                and parts.path.endswith("/forum.php") and int(found) == int(board))
    except (TypeError, ValueError):
        return False


def _compose_page(href, html):
    """The board's trade form, on the forum, with the title and message boxes this desk fills."""
    return _on_forum(href) and 'name="Post"' in html and 'name="ttitle"' in html


def _topic_id(url):
    try:
        return int((urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("t") or [""])[0])
    except (TypeError, ValueError):
        return None


class _Links(HTMLParser):
    """Every <a href> on a page with the text inside it."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._at = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = ""
            for key, val in attrs:
                if key == "href":
                    href = val or ""
            self._at = [href, []]

    def handle_data(self, data):
        if self._at is not None:
            self._at[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._at is not None:
            self.links.append((self._at[0], "".join(self._at[1])))
            self._at = None


def _board_read(html, base, subject, board=None):
    """One read of a board's topic list.
    -> (the newest topic id it lists or None, {topic id: topic url} for links whose text is exactly subject)

    A same-subject link that names another board (a sidebar, a cross-link) is never a candidate;
    every topic link still counts toward the newest id, since all of them existed before the click."""
    links = _Links()
    try:
        links.feed(str(html or ""))
        links.close()
    except Exception:
        return None, {}
    want = " ".join(str(subject or "").split())
    top = None
    same = {}
    for href, text in links.links:
        url = _public_topic(urllib.parse.urljoin(base or _board_url(BOARD), href))
        tid = _topic_id(url) if url else None
        if tid is None:
            continue
        top = tid if top is None else max(top, tid)
        try:
            fid = int((urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("f") or [""])[0])
        except (TypeError, ValueError):
            fid = None
        if board is not None and fid is not None and fid != int(board):
            continue
        if " ".join(text.split()) == want and tid not in same:
            same[tid] = url
    return top, same


def _flow_begin(kind, subject, board, start):
    """A post (kind 'post': board list, New Trade, form, receipt, board list again) or an edit
    (kind 'edit': topic, Edit, form, receipt), before its first step."""
    return {
        "kind": kind, "subject": str(subject or ""), "board": int(board or BOARD),
        "start": str(start or ""), "phase": "open", "t0": None, "asked": False, "seen": False,
        "landed": "", "top": None, "before": None, "word": "", "clicked": False,
        "click_at": None, "back": False, "check_at": None, "result": None,
    }


def _flow_done(st, topic="", stop=""):
    st["phase"] = "done"
    clicked = bool(st["clicked"])
    st["result"] = {
        "landed": st["landed"],
        "clicked": clicked,
        "topic": topic,
        "back": bool(st["back"]) and not topic,
        "stop": "" if clicked else (stop or "not-posted"),
    }
    return st, ("done",)


def _flow_step(st, snap, now, said=None):
    """ONE DECISION of a post or an edit, over one page snapshot. -> (state, action)

    Pure: a snapshot in, the next action out, and no browser, clock or I/O, so a law drives the
    same decisions with a page made of strings. `snap` is {href, ready, mark, html}, or None when
    the page did not answer. `said` is (script name, its answer) for the script the last action
    ran, the answer _NO_ANSWER when the browser did not answer. Actions are ("wait",),
    ("run", name), ("goto", url) and ("done",), with st["result"] = {landed, clicked, topic,
    back, stop}.

    REG-2490. Reaching the form and the receipt have their own budgets (_FORM_S, and _RECEIPT_S,
    over 30 s): one 25 s deadline used to cover both, so a slow board that took the post read as
    not posted. Once the fill script has been SENT, the run is clicked unless the page answered
    that it did not click, because an unanswered submit may have gone out. A post with no receipt
    reads the board list again. A topic whose text is exactly the subject, that was not on the
    list before the click and is newer than every topic the list showed then, is the receipt; an
    older one never is.
    """
    st = dict(st)
    if st["t0"] is None:
        st["t0"] = now
    snap = snap if isinstance(snap, dict) else None
    href = str((snap or {}).get("href") or "")
    html = str((snap or {}).get("html") or "")
    ready = (snap or {}).get("ready") in ("interactive", "complete")
    readable = bool(html) and not _challenge_page(html)
    if href:
        st["landed"] = href
    if readable and href.startswith("https://") and _on_forum(href):
        st["seen"] = True
    name, word = said if said else (None, None)
    if name == "fill" and not st["clicked"]:
        if word in ("clicked", _NO_ANSWER):
            st.update(phase="receipt", clicked=True, click_at=now)
        elif word == "title":
            return _flow_done(st, stop="title")
        else:
            st["word"] = word or "no-form"
    elif name in ("open-trade", "open-edit") and word == "opened" and st["phase"] == "open":
        st["phase"] = "form"

    if st["phase"] in ("open", "form"):
        if href and _on_forum(href) and "login" in href.lower():
            return _flow_done(st, stop="need-login")
        if now - st["t0"] >= _FORM_S:
            if st["word"]:
                return _flow_done(st, stop="form-unknown")
            return _flow_done(st, stop="not-posted" if st["seen"] else "unread")
        compose = readable and ready and _compose_page(href, html)
        if st["phase"] == "open" and st["asked"] and compose:
            st["phase"] = "form"
        if st["phase"] == "form":
            return st, (("run", "fill") if compose else ("wait",))
        if not (readable and ready):
            return st, ("wait",)
        if st["kind"] == "post" and _on_board(href, st["board"]) and "New Trade" in html:
            if st["before"] is None:
                st["top"], st["before"] = _board_read(html, href, st["subject"], st["board"])
            st["asked"] = True
            return st, ("run", "open-trade")
        if st["kind"] == "edit" and _topic(href):
            st["asked"] = True
            return st, ("run", "open-edit")
        return st, ("wait",)

    if st["phase"] == "receipt":
        fresh = snap is not None and not snap.get("mark")
        if fresh and readable and _topic(href):
            got = _public_topic(href)
            if got:
                return _flow_done(st, topic=got)
        if fresh and readable and ready and _compose_page(href, html):
            st["back"] = True
        if not st["back"] and now - st["click_at"] < _RECEIPT_S:
            return st, ("wait",)
        if st["kind"] != "post":
            return _flow_done(st)
        st.update(phase="check", check_at=now)
        return st, ("goto", _board_url(st["board"]))

    if st["phase"] == "check":
        if readable and ready and _on_board(href, st["board"]):
            _newest, same = _board_read(html, href, st["subject"], st["board"])
            before = st["before"] or {}
            new = sorted(url for tid, url in same.items()
                         if tid not in before and st["top"] is not None and tid > st["top"])
            if len(new) == 1:
                return _flow_done(st, topic=new[0])
            if new:
                st["back"] = False      # more than one new topic carries the subject: which is his is unknown
            return _flow_done(st)
        if now - st["check_at"] >= _CHECK_S:
            return _flow_done(st)
        return st, ("wait",)

    return _flow_done(st)


def _run_flow(page, st, scripts, clock, nap):
    """Carry out _flow_step's decisions on `page` until it is done. -> the run's result

    Never raises. A browser that stops answering is a step with no snapshot, and a run that may
    have clicked is carried to its verdict, never dropped as a transport error."""
    act = ("goto", st["start"])
    said = None
    while True:
        if act[0] == "goto":
            try:
                page.goto(act[1])
            except Exception:
                pass
        elif act[0] == "run":
            try:
                word = page.act(act[1], scripts[act[1]])
            except Exception:
                word = _NO_ANSWER
            said = (act[1], word if isinstance(word, str) else "")
        nap(_TICK_S)
        try:
            snap = page.snapshot()
        except Exception:
            snap = None
        try:
            st, act = _flow_step(st, snap, clock(), said)
        except Exception:
            st, act = _flow_done(dict(st), stop="unread")
        said = None
        if act[0] == "done":
            return st["result"]


def _chrome_search(item, cookie, chrome=None, clock=None, nap=None):
    """Load the Switch Ladder search in a scratch Chrome. The cookie is not logged.

    The forum answers a scripted request with a challenge page. A separate Chrome,
    on its own profile and its own port, can submit the board's own search form.
    His open Chrome is not the one this starts. Raises ChromeStart or OSError when
    that load fails.
    """
    clock = clock or time.monotonic
    nap = nap or time.sleep
    submit = (
        "(function(){var f=document.querySelector('form[action*=\"search.php\"]');"
        "if(!f||!f.stext)return 'no-form';f.stext.value=%s;f.submit();return 'sent';})()"
    ) % json.dumps(_search_keywords(item))
    with (chrome or _scratch_chrome)(cookie, "d2jsp-quote-") as page:
        page.goto("https://forums.d2jsp.org/forum.php?f=%d" % QUOTE_BOARD)
        sent = False
        html = ""
        end = clock() + 20
        while clock() < end:
            nap(0.8)
            try:
                snap = page.snapshot()
            except Exception:
                continue
            html = (snap or {}).get("html") or ""
            if not sent and "search.php" in html and "stext" in html:
                try:
                    page.act("search", submit)
                except _ErrorReply:
                    pass        # an error in place of a result: the search may have gone out
                except Exception:
                    continue
                sent = True
            if sent and "Search Results" in html and not _challenge_page(html):
                return html
        if sent and html and not _challenge_page(html):
            return html
        raise OSError("search")


def _chrome_edit(topic, subject, text, cookie, chrome=None, clock=None, nap=None):
    """Replace the saved topic through its own Edit link. -> the run's result (see _flow_step)

    The link has to say Edit and open post.php. A topic with no such link is
    not posted to, and no new trade starts. A title longer than 50 characters is
    not sent. Raises ChromeStart before anything is opened, and nothing after.
    The cookie is not logged. His open Chrome is not the one this starts.
    """
    scripts = {"open-edit": _open_link_js("Edit"), "fill": _fill_js(subject, text)}
    with (chrome or _scratch_chrome)(cookie, "d2jsp-post-") as page:
        return _run_flow(page, _flow_begin("edit", subject, BOARD, topic), scripts,
                         clock or time.monotonic, nap or time.sleep)


def _chrome_post(subject, text, cookie, forum=None, chrome=None, clock=None, nap=None):
    """Submit a board 268 (or 271) trade from the board's own New Trade link. -> the run's result

    The trading board does not open on the old compose address. That address
    answers Invalid Action. The form that does open names the title ttitle, the
    message Post, and the button submit. A title longer than 50 characters
    is the board's own limit, and this function does not send it. The run is
    _flow_step's: the board list is read before the click and again when no
    receipt comes. Raises ChromeStart before anything is opened, and nothing
    after. The cookie is not logged. His open Chrome is not the one this starts.
    """
    board = _post_board(forum) or BOARD
    scripts = {"open-trade": _open_link_js("New Trade"), "fill": _fill_js(subject, text)}
    with (chrome or _scratch_chrome)(cookie, "d2jsp-post-") as page:
        return _run_flow(page, _flow_begin("post", subject, board, _board_url(board)), scripts,
                         clock or time.monotonic, nap or time.sleep)


def d2jsp_quote(item, origin, host, port, cookie_get=None, transport=None, node_run=None, chrome_fetch=None, sec_fetch_site=None):
    """Read one item's fg range from the Switch Ladder search. -> (http code, dict)

    The dict is the reading. It never carries the cookie or the page.
    No login, a challenge page, or no fg on a line that names the item stays unknown.
    """
    import datetime
    read_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    item = str(item or "").strip()[:80]
    if not console_may_post(origin, host, port, sec_fetch_site):
        return 403, _quote_unknown(item, read_at, "origin")
    if not item:
        return 200, _quote_unknown(item, read_at, "no item")
    get_cookie = cookie_get or live_cookie_header
    try:
        cookie, cookie_reason = get_cookie()
    except Exception:
        cookie, cookie_reason = None, "chrome-unread"
    if not cookie:
        return 200, _quote_unknown(item, read_at, cookie_reason or "need-login")
    fetch = transport or _transport
    headers = _headers(cookie)
    headers["Referer"] = "https://forums.d2jsp.org/forum.php?f=%d" % QUOTE_BOARD
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        status, hdrs, raw = fetch("POST", _search_url(item), headers, _search_body(item))
    except Exception:
        return 200, _quote_unknown(item, read_at, "unread")
    if status in (301, 302, 303, 307, 308):
        loc = ""
        if isinstance(hdrs, dict):
            loc = hdrs.get("Location") or hdrs.get("location") or ""
        if "login" in str(loc).lower():
            return 200, _quote_unknown(item, read_at, "need-login")
        return 200, _quote_unknown(item, read_at, "unread")
    if isinstance(raw, (bytes, bytearray)):
        page = raw.decode("utf-8", "replace")
    else:
        page = str(raw or "")
    if _challenge_page(page) and chrome_fetch is not False:
        opener = chrome_fetch or _chrome_search
        try:
            opened = opener(item, cookie)
        except Exception:
            opened = page
        if isinstance(opened, str) and opened and not _challenge_page(opened):
            page = opened
    return 200, parse_public_quote(page, item, read_at, node_run=node_run)


def open_quote_login_once():
    """A price read opens no window. -> False, always

    REG-2491. The room asks for prices as it opens, with no click, and a need-login answer used to
    open the forum login in his Chrome, which came to the front over the console (GrokBot, #230,
    v3707). The lamp click (open_d2jsp_login) and a Post click (d2jsp_send) are the only doors that
    open the login; the price stays need-login, and the page says the forum search needs the
    Chrome login on this machine.
    """
    return False


def _post_board(forum):
    """268 is RotW softcore. 271 is RotW softcore ladder. Anything else is refused."""
    try:
        n = int(forum)
    except (TypeError, ValueError):
        return None
    return n if n in POST_BOARDS else None


def _topic_on_board(url, forum):
    """A saved topic is edited only when it is the board this post is for.

    A topic with no f= belongs to board 268, which is the only board a post
    could have saved before the ladder board existed. A 268 topic is not
    edited as a 271 trade.
    """
    public = _public_topic(url)
    if not public:
        return False
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(public).query)
        raw = (query.get("f") or [None])[0]
        found = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        found = None
    if found is None:
        return int(forum) == BOARD
    return found == int(forum)


def _public_topic(url):
    """A topic URL that is safe to show. Anything else is empty."""
    if not _topic(url):
        return ""
    raw = str(url or "").strip()
    if raw.startswith("/") and not raw.startswith("//"):
        raw = "https://%s%s" % (_HOST, raw.split("#", 1)[0])
    try:
        parts = urllib.parse.urlparse(raw)
    except Exception:
        return ""
    if parts.scheme != "https" or parts.netloc != _HOST:
        return ""
    if "topic.php" not in (parts.path or ""):
        return ""
    return urllib.parse.urlunparse(("https", _HOST, parts.path, "", parts.query, ""))


def _open_door(open_login):
    """The login door a Post click opens. -> whether it opened"""
    door = open_login or _open_chrome_login
    try:
        return bool(door())
    except Exception:
        return False


def _as_result(got):
    """A run's result as {landed, clicked, topic, back, stop}.

    The Chrome flows return that dict. A bare URL (an older seam) is read for what it can prove: a
    forum topic is the receipt, a forum login page stopped the run before the click, and 'no-edit'
    or nothing at all never clicked. Any other page cannot prove the submit was not sent, so its
    click is unknown, and an unknown click is read as a click."""
    if isinstance(got, dict):
        clicked = got.get("clicked")
        return {
            "landed": str(got.get("landed") or ""),
            "clicked": None if clicked is None else bool(clicked),
            "topic": str(got.get("topic") or ""),
            "back": bool(got.get("back")),
            "stop": str(got.get("stop") or ""),
        }
    url = str(got or "").strip()
    out = {"landed": url, "clicked": None, "topic": "", "back": False, "stop": ""}
    if not url:
        out.update(clicked=False, stop="unread")
    elif url == "no-edit":
        out.update(landed="", clicked=False, stop="not-posted")
    elif _public_topic(url):
        out.update(clicked=True, topic=url)
    elif _on_forum(url) and "login" in url.lower():
        out.update(clicked=False, stop="need-login")
    return out


def _send_verdict(got, board, at, open_login):
    """THE ONE PLACE A SEND'S OUTCOME BECOMES A REASON. -> (200, answer)

    REG-2490. A topic on the forum is the only receipt: submitted. A run that clicked, or that
    nobody can say did not, is maybe-sent with the board and the time, unless the board sent the
    compose form back (not-posted). A click that landed on post.php used to read 'not-posted' and an
    error after the click 'unread', and both told him nothing was posted. Only a run that provably
    never clicked says not-posted, unread, title, form-unknown or need-login."""
    res = _as_result(got)
    topic = _public_topic(res["topic"])
    if topic:
        return 200, {"ok": True, "reason": "submitted", "topic": topic}
    if res["clicked"] is not False:
        if res["back"]:
            return 200, {"ok": False, "reason": "not-posted"}
        return 200, {"ok": False, "reason": "maybe-sent", "board": int(board), "at": at}
    if res["stop"] == "need-login":
        return 200, {"ok": False, "reason": "need-login", "opened": _open_door(open_login)}
    if res["stop"] in ("title", "form-unknown", "unread"):
        return 200, {"ok": False, "reason": res["stop"]}
    return 200, {"ok": False, "reason": "not-posted"}


def _run_opener(call):
    """Run one Chrome flow. -> (its result, None), or (None, the answer for a run that never started)

    The flows raise only before anything was opened: a Chrome that could not start is chrome-start
    with its why, and anything else is unread."""
    try:
        return call(), None
    except ChromeStart as stop:
        return None, {"ok": False, "reason": "chrome-start", "why": stop.why}
    except Exception:
        return None, {"ok": False, "reason": "unread"}


def _send_edit(subject, text, cookie, topic, edit_post, open_login, forum=None, at=""):
    """Update one saved topic. A missing Edit door does not start a new trade."""
    opener = edit_post or _chrome_edit
    got, refused = _run_opener(lambda: opener(topic, subject, text, cookie))
    if refused is not None:
        return 200, refused
    return _send_verdict(got, _post_board(forum) or BOARD, at, open_login)


def _send_through_chrome(subject, text, cookie, chrome_post, open_login, forum=None, at=""):
    """One scratch-Chrome submit. A topic URL is the only submitted receipt."""
    opener = chrome_post or _chrome_post
    board = _post_board(forum) or BOARD
    if opener is _chrome_post:
        got, refused = _run_opener(lambda: opener(subject, text, cookie, board))
    else:
        got, refused = _run_opener(lambda: opener(subject, text, cookie))
    if refused is not None:
        return 200, refused
    return _send_verdict(got, board, at, open_login)


_SEND_LOCK = threading.Lock()
# (board, subject, sha256 of the body) -> {reason, t, at, topic, on}; this process only. `on` holds the
# topics the send changed or made (_topic_ref); a maybe-sent new post holds none, since its topic is unknown.
_SENT = {}
_RESEND_S = 30 * 60


def _stamp(t):
    """An instant as the desk reads it: UTC, to the millisecond."""
    return datetime.datetime.fromtimestamp(float(t), datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sent_key(board, subject, text):
    return (int(board), str(subject), hashlib.sha256(str(text).encode("utf-8")).hexdigest())


def _topic_ref(url):
    """The topic a URL names, as one value two links to it share: its t= id, else the public URL.
    None for no topic."""
    public = _public_topic(url)
    if not public:
        return None
    tid = _topic_id(public)
    return public if tid is None else tid


def _sent_before(key, t, target=""):
    """The answer to an identical re-send inside 30 minutes, or None. -> dict | None

    REG-2490. The record lives in this process: a console restart forgets it. A new post (no
    target) is answered by any record of the same draft, since posting it again would make a
    second topic. An edit is answered only by a record of the topic it edits (REG-2495): another
    topic's record says nothing about what this one shows, and an edit never makes a second topic."""
    for old in [k for k, v in _SENT.items() if t - v["t"] >= _RESEND_S]:
        del _SENT[old]
    prior = _SENT.get(key)
    if not prior:
        return None
    ref = _topic_ref(target)
    if ref is not None and ref not in prior["on"]:
        return None
    if prior["reason"] == "submitted":
        return {"ok": False, "reason": "already-posted", "topic": prior["topic"], "at": prior["at"]}
    return {"ok": False, "reason": "maybe-sent-recently", "at": prior["at"]}


def _remember_send(key, out, t, at, target=""):
    """Record a send that went up or may have, under its draft.

    REG-2495 (A, B, A): the record was keyed on the draft alone, so a shop list posted as A, edited
    to B and edited back to A inside 30 minutes answered the third send already-posted with A's old
    receipt: the edit never ran and the board still showed B. A send that changed or made a topic
    now drops every other draft's record on that topic, because the topic no longer shows them."""
    reason = out.get("reason")
    if reason not in ("submitted", "maybe-sent"):
        return
    topic = str(out.get("topic") or "") if reason == "submitted" else ""
    on = set(ref for ref in (_topic_ref(target), _topic_ref(topic)) if ref is not None)
    for gone in [k for k, v in _SENT.items() if k != key and v["on"] & on]:
        del _SENT[gone]
    _SENT[key] = {"reason": reason, "t": t, "at": at, "topic": topic, "on": on}


def d2jsp_send(body, origin, host, port, cookie_get=None, transport=None, open_login=None, chrome_post=None, edit_post=None, sec_fetch_site=None, now=None):
    """Post one desk draft. -> (http code, {ok, reason, ...}); the reason is one of SEND_REASONS

    One send runs at a time on this console: a second one while a send runs is busy, and it reads
    no cookie and starts no Chrome (REG-2490: the page's own `posting` flag guarded one tab, and
    the server is threaded). The dict never carries the cookie, the page, or the draft.
    """
    if not console_may_post(origin, host, port, sec_fetch_site):
        return 403, {"ok": False, "reason": "origin"}
    body = body if isinstance(body, dict) else {}
    try:
        forum = int(body.get("forum"))
    except (TypeError, ValueError):
        forum = 0
    if _post_board(forum) is None:
        return 200, {"ok": False, "reason": "wrong-board"}
    subject = str(body.get("subject") or "").strip()
    text = str(body.get("body") or "").strip()
    if len(text) > 4000:
        return 200, {"ok": False, "reason": "long"}
    if not _priced(subject, text):
        return 200, {"ok": False, "reason": "no-price"}
    if len(subject) > 50:
        return 200, {"ok": False, "reason": "title"}
    if not _SEND_LOCK.acquire(False):
        return 200, {"ok": False, "reason": "busy"}
    try:
        return _send_locked(body, forum, subject, text, cookie_get, transport, open_login,
                            chrome_post, edit_post, now)
    finally:
        _SEND_LOCK.release()


def _send_locked(body, forum, subject, text, cookie_get, transport, open_login, chrome_post, edit_post, now):
    """d2jsp_send under the send lock: the re-send record first, then one route, then the record.

    REG-2490. The same draft (board, subject and body) within 30 minutes of a submit is
    already-posted, and within 30 minutes of a maybe-sent is maybe-sent-recently; neither reads the
    cookie or starts Chrome. An edit is held back only by a record of its own topic, and a send that
    changes a topic retires the other drafts' records on it (REG-2495)."""
    t = time.time() if now is None else float(now)
    at = _stamp(t)
    target = _public_topic(str(body.get("topic") or ""))
    if target and not _topic_on_board(target, forum):
        target = ""
    key = _sent_key(forum, subject, text)
    prior = _sent_before(key, t, target)
    if prior is not None:
        return 200, prior
    code, out = _send_route(forum, subject, text, target, cookie_get, transport, open_login,
                            chrome_post, edit_post, at)
    _remember_send(key, out, t, at, target)
    return code, out


def _send_route(forum, subject, text, target, cookie_get, transport, open_login, chrome_post, edit_post, at):
    """Read the cookie, then edit the saved topic (target), post through Chrome, or (a law's seam)
    post through urllib."""
    get_cookie = cookie_get or live_cookie_header
    try:
        cookie, cookie_reason = get_cookie()
    except Exception:
        cookie, cookie_reason = None, "chrome-unread"
    if not cookie:
        if cookie_reason == "need-login":
            return 200, {"ok": False, "reason": "need-login", "opened": _open_door(open_login)}
        return 200, {"ok": False, "reason": "chrome-unread"}
    if target:
        opener = edit_post
        if opener is None and chrome_post is False:
            opener = lambda *args: "no-edit"
        return _send_edit(subject, text, cookie, target, opener, open_login, forum, at)
    if transport is None and chrome_post is not False:
        return _send_through_chrome(subject, text, cookie, chrome_post, open_login, forum, at)
    fetch = transport or _transport
    try:
        status, hdrs, raw = fetch("GET", COMPOSE_URL, _headers(cookie), None)
    except Exception:
        return 200, {"ok": False, "reason": "unread"}
    if status in (301, 302, 303, 307, 308):
        loc = ""
        if isinstance(hdrs, dict):
            loc = hdrs.get("Location") or hdrs.get("location") or ""
        if _on_forum(loc) and "login" in loc.lower():
            return 200, {"ok": False, "reason": "need-login", "opened": _open_door(open_login)}
        return 200, {"ok": False, "reason": "form-unknown"}
    raw_text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
    if _challenge_page(raw_text) and chrome_post is not False:
        return _send_through_chrome(subject, text, cookie, chrome_post, open_login, forum, at)
    parsed = parse_compose(raw)
    if parsed["reason"] != "ready":
        out = {"ok": False, "reason": parsed["reason"]}
        if parsed["reason"] == "need-login":
            out["opened"] = _open_door(open_login)
        return 200, out
    fields = list(parsed["fields"])
    fields.append(("subject", subject))
    fields.append(("message", text))
    fields.append(("post", parsed.get("post_value") or "Post"))
    encoded = urllib.parse.urlencode(fields).encode("utf-8")
    sent_headers = _headers(cookie)
    sent_headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        status, hdrs, raw = fetch("POST", COMPOSE_URL, sent_headers, encoded)
    except Exception:
        # The POST may have reached the board before its answer was lost.
        return _send_verdict({"clicked": True}, forum, at, open_login)
    loc = ""
    if isinstance(hdrs, dict):
        loc = hdrs.get("Location") or hdrs.get("location") or ""
    if status in (301, 302, 303, 307, 308) and _topic(loc):
        return _send_verdict({"clicked": True, "topic": urllib.parse.urljoin(COMPOSE_URL, loc)},
                             forum, at, open_login)
    if status in (301, 302, 303, 307, 308) and _on_forum(loc) and "login" in loc.lower():
        return 200, {"ok": False, "reason": "need-login", "opened": _open_door(open_login)}
    came_back = parse_compose(raw)
    if came_back["reason"] == "need-login":
        return 200, {"ok": False, "reason": "need-login", "opened": _open_door(open_login)}
    # The board answered the POST with its compose form again: it did not take the post. Any other
    # answer (a challenge, an error page, an unknown 200) cannot prove the post was refused, and the
    # draft is never sent a second time once its POST went out.
    return _send_verdict({"clicked": True, "back": came_back["reason"] == "ready"}, forum, at, open_login)
