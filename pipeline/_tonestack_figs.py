#!/usr/bin/env python3
"""One-off generator for the two schematic-fragment figures in
reference/studies/tone-stack-ladder.md.

Drawn here from the corpus's own reading of the published sheets — original
artwork in the site's schematic idiom (IEC rectangles, two-plate capacitors,
pot = track + wiper arrow). Nothing is traced from any factory drawing.

    python3 pipeline/_tonestack_figs.py             # one <svg> per line, for the page
    python3 pipeline/_tonestack_figs.py --standalone  # + palette + ground, for rsvg
"""
from __future__ import annotations

import sys

# ---- primitives -------------------------------------------------------------


def wire(x1, y1, x2, y2, cls="wire"):
    return f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'


def poly(pts, cls="wire"):
    d = " ".join(f"{x},{y}" for x, y in pts)
    return f'<polyline class="{cls}" points="{d}"/>'


def jn(x, y):
    return f'<circle class="jn" cx="{x}" cy="{y}" r="3"/>'


def res_v(cx, cy, cls="e-lead"):
    """Vertical resistor, terminals at cy±30."""
    return (f'<rect class="{cls}" x="{cx - 8}" y="{cy - 20}" width="16" height="40"/>'
            + wire(cx, cy - 30, cx, cy - 20, cls) + wire(cx, cy + 20, cx, cy + 30, cls))


def cap_v(cx, cy, cls="e-lead"):
    """Vertical capacitor, terminals at cy±30."""
    return (wire(cx - 16, cy - 6, cx + 16, cy - 6, cls)
            + wire(cx - 16, cy + 6, cx + 16, cy + 6, cls)
            + wire(cx, cy - 30, cx, cy - 6, cls) + wire(cx, cy + 6, cx, cy + 30, cls))


def cap_h(cx, cy, cls="e-lead"):
    """Horizontal capacitor, terminals at cx±30."""
    return (wire(cx - 6, cy - 16, cx - 6, cy + 16, cls)
            + wire(cx + 6, cy - 16, cx + 6, cy + 16, cls)
            + wire(cx - 30, cy, cx - 6, cy, cls) + wire(cx + 6, cy, cx + 30, cy, cls))


def pot_v(cx, cy, side="right", cls="e-lead", wcls=None):
    """Vertical pot: track terminals at cy±30, wiper terminal at cx±40."""
    wcls = wcls or cls
    s = 1 if side == "right" else -1
    tri = (f'<polygon class="{wcls}-fill" points="{cx + s * 26},{cy} '
           f'{cx + s * 14},{cy + 6} {cx + s * 14},{cy - 6}"/>')
    return (res_v(cx, cy, cls) + wire(cx + s * 40, cy, cx + s * 26, cy, wcls) + tri)


def gnd(x, y):
    return ('<g class="gndsym">' + wire(x, y, x, y + 8, "g")
            + wire(x - 11, y + 8, x + 11, y + 8, "g")
            + wire(x - 6.5, y + 13, x + 6.5, y + 13, "g")
            + wire(x - 3, y + 18, x + 3, y + 18, "g") + '</g>')


def arrow_r(x, y, length=44):
    """Signal arrow pointing right, tail at x."""
    return (wire(x, y, x + length - 10, y)
            + f'<polygon class="wire-fill" points="{x + length},{y} '
              f'{x + length - 11},{y + 5} {x + length - 11},{y - 5}"/>')


def arrow_in(x, y, length=44):
    """Signal arrow pointing right, head at x."""
    return (wire(x - length, y, x - 10, y)
            + f'<polygon class="wire-fill" points="{x},{y} '
              f'{x - 11},{y + 5} {x - 11},{y - 5}"/>')


def val(x, y, t, anchor="start"):
    return f'<text class="cl" x="{x}" y="{y}" text-anchor="{anchor}">{t}</text>'


def nd(x, y, t, anchor="start"):
    return f'<text class="ndl" x="{x}" y="{y}" text-anchor="{anchor}">{t}</text>'


def io(x, y, t, anchor="start"):
    return f'<text class="io-lbl" x="{x}" y="{y}" text-anchor="{anchor}">{t}</text>'


# ---- figure 1: the joined ("textbook") network -------------------------------

def joined() -> tuple[str, int, int]:
    W, H = 780, 560
    g = []
    # top rail: IN — treble cap — N3
    g += [arrow_in(100, 60), wire(100, 60, 300, 60), cap_h(330, 60),
          wire(360, 60, 560, 60), jn(100, 60)]
    # slope resistor down to the N2 bus
    g += [wire(100, 60, 100, 120), res_v(100, 150), wire(100, 180, 100, 250)]
    # treble pot: top lug N3, BOTTOM LUG ON THE SLOPE FOOT (the difference)
    g += [wire(560, 60, 560, 130), pot_v(560, 160),
          wire(560, 190, 560, 250, "wire hl"), jn(560, 250)]
    # output: treble wiper AND bass wiper meet here
    g += [wire(600, 160, 700, 160), jn(700, 160), arrow_r(700, 160)]
    # N2 bus
    g += [wire(100, 250, 560, 250), jn(180, 250), jn(430, 250)]
    # bass leg: cap to N4, pot from N4 to N5
    g += [wire(430, 250, 430, 260), cap_v(430, 290), wire(430, 320, 430, 365),
          pot_v(430, 395), wire(430, 425, 430, 455)]
    # bass wiper up to the shared output node (the difference)
    g += [poly([(470, 395), (700, 395), (700, 160)], "wire hl")]
    # mid cap from the slope foot onto the TOP of the mid leg (the difference)
    g += [wire(180, 250, 180, 322, "wire hl"), cap_v(180, 352, "e-lead hl"),
          wire(180, 382, 180, 455, "wire hl")]
    # N5 bus and the rheostat-wired mid pot
    g += [wire(180, 455, 430, 455), jn(210, 455), jn(250, 455)]
    g += [wire(250, 455, 250, 460), pot_v(250, 490, "left"),
          wire(210, 490, 210, 455, "wire hl"), wire(250, 520, 250, 524), gnd(250, 524)]
    # labels
    g += [io(56, 44, "From the cathode follower"),
          val(120, 155, "56 kΩ slope"),
          val(330, 40, "250 pF", "middle"),
          val(540, 165, "250 kΩ Treble", "end"),
          val(410, 295, "0.02 µF", "end"),
          val(410, 400, "1 MΩ Bass", "end"),
          val(162, 357, "0.02 µF", "end"),
          val(272, 495, "25 kΩ Middle"),
          nd(110, 242, "N2 · slope foot"),
          nd(568, 48, "N3"),
          nd(440, 345, "N4"),
          nd(300, 447, "N5"),
          nd(700, 140, "OUT", "middle")]
    return "".join(g), W, H


# ---- figure 2: the ladder the sheets draw ------------------------------------

def ladder() -> tuple[str, int, int]:
    W, H = 780, 490
    g = []
    # top rail: IN — treble cap — N3
    g += [arrow_in(100, 60), wire(100, 60, 300, 60), cap_h(330, 60),
          wire(360, 60, 560, 60), jn(100, 60)]
    # slope resistor down to the N2 bus
    g += [wire(100, 60, 100, 100), res_v(100, 130), wire(100, 160, 100, 185)]
    # treble pot: top lug N3, bottom lug on the FAR side of the bass cap
    g += [wire(560, 60, 560, 130), pot_v(560, 160),
          wire(560, 190, 560, 245, "wire hl")]
    # output: the treble wiper, alone
    g += [wire(600, 160, 700, 160), arrow_r(700, 160)]
    # N2 bus
    g += [wire(100, 185, 430, 185), jn(180, 185)]
    # bass cap down to the N4 bus
    g += [cap_v(430, 215, "e-lead hl"), wire(430, 245, 560, 245, "wire hl"),
          jn(430, 245), jn(470, 245)]
    # bass pot as a rheostat: wiper strapped into the treble-lug node
    g += [wire(430, 245, 430, 280), pot_v(430, 310),
          wire(470, 310, 470, 245, "wire hl"), wire(430, 340, 430, 385)]
    # N5 bus and the mid pot, its full track always in the leg
    g += [wire(250, 385, 430, 385), jn(250, 385)]
    g += [pot_v(250, 415, "left"), wire(250, 445, 250, 449), gnd(250, 449)]
    # mid cap onto the mid pot's WIPER
    g += [wire(210, 415, 180, 415, "wire hl"), wire(180, 415, 180, 330, "wire hl"),
          cap_v(180, 300, "e-lead hl"), wire(180, 270, 180, 185, "wire hl")]
    # labels
    g += [io(56, 44, "From the cathode follower"),
          val(120, 135, "56 kΩ slope"),
          val(330, 40, "250 pF", "middle"),
          val(540, 165, "250 kΩ Treble", "end"),
          val(410, 220, "0.02 µF", "end"),
          val(410, 315, "1 MΩ Bass", "end"),
          val(160, 305, "0.02 µF", "end"),
          val(272, 420, "25 kΩ Middle"),
          nd(110, 177, "N2 · slope foot"),
          nd(568, 48, "N3"),
          nd(500, 266, "N4 · the treble pot's lower lug"),
          nd(300, 377, "N5"),
          nd(700, 140, "OUT", "middle")]
    return "".join(g), W, H


PALETTE = (
    '<style>'
    'text{font-family:"Avenir Next Condensed",Arial,sans-serif}'
    '.wire,.e-lead,.gndsym line{fill:none;stroke:#eee2c8;stroke-width:1.8;'
    'stroke-linecap:round;stroke-linejoin:round}'
    'rect.e-lead{fill:none}'
    '.hl{stroke:#e89b3f}'
    '.hl-fill{fill:#e89b3f}'
    '.wire-fill,.e-lead-fill{fill:#eee2c8}'
    '.gndsym line{stroke:#7a6a54}'
    '.jn{fill:#eee2c8;stroke:none}'
    '.cl{font-family:"SF Mono",Menlo,monospace;font-size:15px;fill:#a3927b}'
    '.ndl{font-size:14.5px;fill:#7a6a54;letter-spacing:.08em}'
    '.io-lbl{font-size:14.5px;fill:#a3927b;letter-spacing:.14em;text-transform:uppercase}'
    
    '</style>')


def svg(body, w, h, title, desc, standalone):
    head = (f'<svg class="fig-sch" viewBox="0 0 {w} {h}" role="img" '
            f'xmlns="http://www.w3.org/2000/svg" aria-labelledby="' +
            title[0] + '-t ' + title[0] + '-d">')
    inner = (f'<title id="{title[0]}-t">{title[1]}</title>'
             f'<desc id="{title[0]}-d">{desc}</desc>')
    bg = f'<rect x="0" y="0" width="{w}" height="{h}" fill="#211a14"/>' if standalone else ""
    return head + (PALETTE if standalone else "") + inner + bg + body + "</svg>"


def main():
    standalone = "--standalone" in sys.argv
    jb, jw, jh = joined()
    lb, lw, lh = ladder()
    figs = [
        ("fig-joined", "The joined network — the textbook redrawing",
         "Schematic fragment of the three-knob tone stack in its joined form: the "
         "treble capacitor and the slope resistor both leave the input; the treble "
         "pot's lower lug sits on the slope resistor's foot; the bass capacitor "
         "feeds the bass pot from that same foot; the treble and bass wipers meet "
         "at one output node; and the mid capacitor lands on the top of a "
         "rheostat-wired middle pot.", jb, jw, jh),
        ("fig-ladder", "The ladder — what the published sheets draw",
         "Schematic fragment of the same seven parts wired as a ladder: the treble "
         "capacitor and the slope resistor both leave the input; the bass capacitor "
         "runs from the slope foot to a node that carries the treble pot's lower "
         "lug and the hot end of the bass pot; the bass pot is a rheostat with its "
         "wiper strapped to that node; the middle capacitor lands on the middle "
         "pot's wiper; and the stack's output is the treble wiper alone.", lb, lw, lh),
    ]
    for slug, title, desc, body, w, h in figs:
        print(svg(body, w, h, (slug, title), desc, standalone))


if __name__ == "__main__":
    main()
