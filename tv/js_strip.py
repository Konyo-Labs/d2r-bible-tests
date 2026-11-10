# -*- coding: utf-8 -*-
"""v3886 (#152) - THE LAWS' ONE COMMENT STRIPPER.

A law that greps bible.html or tv/control_ui.html for code strips comments first, or it reads its own explanations
(feedback-comments-vs-code). Each law carried its own copy of the stripper - 186 regex sites in tv/ on 11-08 - and they
drift: v3885's first GitHub round went red because two copies in test_control read `accept="image/*"` (a MIME wildcard
in an <input>) as a comment opener; once the Chronicle buttons left, the next "*/" was inside the cap and the strip ate
#funi-body, #tab-fsets, #fsets-body and the Characters ids - live markup.

strip_js_comments(src, cap) is that stripper, once:
  · a block comment is "/*" .. "*/" no longer than `cap` characters - an unbounded match spanning thousands of
    characters is a string or a regex literal that happens to hold the tokens (v1873: an unbounded one deleted 16.9% of
    bible.html and 170 of its 444 ids);
  · a "/*" inside a string literal is never a comment (accept="image/*", var s = "hello /* not a comment */");
  · a line comment is a line that STARTS with // (a // inside a URL or a string stays).
test_one_comment_stripper_for_the_laws holds it to those three and holds the count of private copies so it can only fall.
"""
import re

#: the bound: a real comment in this repo is long but not unbounded (v1873: 0 of 444 ids lost at 4000)
CAP = 4000


def _strip_block_comments(src, cap):
    """Replace `/* ... */` (body at most `cap` chars) with a space; leave `/*` inside a string alone."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            q = c
            out.append(c)
            i += 1
            while i < n:
                ch = src[i]
                out.append(ch)
                if ch == "\\" and i + 1 < n:
                    out.append(src[i + 1])
                    i += 2
                    continue
                if ch == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            if end != -1 and (end - (i + 2)) <= cap:
                out.append(" ")
                i = end + 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_js_comments(src, cap=CAP):
    """`src` with its block and line comments replaced by a space. Pure.
    A `/*` inside a string literal (or a MIME wildcard like accept="image/*") is not a comment."""
    src = _strip_block_comments(str(src), int(cap))
    return re.sub(r"(?m)^\s*//.*$", " ", src)
