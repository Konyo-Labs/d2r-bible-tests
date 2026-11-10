# -*- coding: utf-8 -*-
"""v3895 (#22, REG-3587) - ONE CALIBRATION FILM FOR EVERY READER.

stash_eye and chronicle_template each carried their own copy of the same Mac film
(2940 x 1912). A re-measure that updated one silently left the other reading a screen
shape that no longer exists (surfaces.py already named this drift). The film lives here;
both readers import it. Re-measuring later is the rest of the calibration phase.
"""

# The film every stash and chronicle band was measured on (Konyo's Mac).
FILM = (2940, 1912)


def film():
    """(width, height) of the shared calibration film."""
    return FILM


def aspect():
    """width / height of the shared calibration film. The exact ratio, not a rounded 1.538."""
    w, h = FILM
    return w / float(h)
