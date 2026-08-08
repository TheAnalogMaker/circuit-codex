#!/usr/bin/env python3
"""Cross-surface value-consistency gate.

A single part in this corpus states its value on up to four surfaces, each
written by a different hand for a different reader:

    schematic.kicad_sch  symbol Value property   "0.02u", "100k", "470 1W"
    bom.yaml             house units string      "0.02 µF · 600 V"
    layout.yaml          label / value fields    "V1 · 12AX7", "27 kΩ"
    the era sheet render era lettering           ".02-600", "100K", "470-5"
                         (render_layouts.era_pair(), fed from bom.yaml)

Nothing made them agree. validate.py proves the *designators* line up; nothing
proved the *quantities* do. That is exactly the failure this project cannot
ship: a page that states 100 kΩ in the parts list, 10 kΩ on the schematic, and
lets a reader build the wrong amp with total confidence in both.

This script normalises every surface to a physical quantity — ohms, farads,
henries, volts, watts, or (for tubes, transformers, diodes) a designation
token — and reports every reference designator whose surfaces disagree.

It is deliberately conservative in one direction only. A surface it cannot
resolve to a single unambiguous quantity is REPORTED (as AMBIGUOUS), never
quietly passed: "20-600" and "30-450u" are the factory's value-voltage
shorthand, both of which have previously reached the live site reinterpreted as
picofarads and as a double voltage claim. A string that cannot be read whole is
a string this corpus must not claim agreement about.

    python3 pipeline/check_value_consistency.py            # whole corpus
    python3 pipeline/check_value_consistency.py 5f1 jtm45  # named amps
    python3 pipeline/check_value_consistency.py --json     # machine-readable
    python3 pipeline/check_value_consistency.py --strict   # exit 1 on any diff

Exit status is 0 unless --strict is given (report-only until the corpus is
clean; then it joins the gate list in AGENTS.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_layouts import (           # noqa: E402
    annotation_value, category, era_pair, primary_value, resolve_tube_slug,
)

ROOT = Path(__file__).resolve().parent.parent
AMPS = ROOT / "amps"

# Categories that carry a measurable quantity, and which dimension it is in.
DIMENSION = {"res": "ohms", "film": "farads", "mica": "farads",
             "electro": "farads", "choke": "henries"}
# Categories whose "value" is a designation, compared as a token, not a number.
DESIGNATION = {"tube", "xfmr", "diode", "other"}

# Sentinel for "the caller did not resolve a dimension", so that a caller which
# resolved it to None (this part states a NAME, not a number) is not silently
# overridden by the category default. That bug kept every choke pinned to
# henries and reported eleven agreeing part-number pairs as unreadable.
_UNSET = object()

# Relative tolerance for a quantity comparison. Values are exact decimals on
# every surface — this only absorbs 1/3-style repeating fractions.
REL_TOL = Decimal("0.005")

# Findings that are DEFECTS — two surfaces stating different things about one
# part. These are what --strict gates on.
HARD_KINDS = ("MISMATCH", "UNIT-MISMATCH", "VOLTS-MISMATCH", "WATTS-MISMATCH",
              "TYPE-MISMATCH", "AMBIGUOUS")
# Findings that are DECLARED GAPS — the corpus refusing to invent a figure the
# source never printed, or an annotation the electrical model has no designator
# for. Reported so they stay visible, never gated: hiding them would make the
# archive's honesty rule invisible, and gating them would push someone to invent
# a number to clear the gate.
SOFT_KINDS = ("UNSTATED", "UNLINKED")


# ---------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------
_FRACTIONS = {"½": Decimal("0.5"), "¼": Decimal("0.25"), "¾": Decimal("0.75"),
              "⅓": Decimal(1) / Decimal(3), "⅔": Decimal(2) / Decimal(3),
              "⅛": Decimal("0.125")}


def _dec(tok: str) -> Decimal | None:
    s = str(tok).strip().replace(",", "")
    if s in _FRACTIONS:
        return _FRACTIONS[s]
    if s.startswith("."):
        s = "0" + s
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _close(a: Decimal, b: Decimal) -> bool:
    if a == b:
        return True
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= REL_TOL


def _eng(q: Decimal, dim: str) -> str:
    """Canonical printable form, so the diff table compares like with like."""
    if dim == "ohms":
        for lim, suf in ((Decimal("1E6"), "MΩ"), (Decimal("1E3"), "kΩ")):
            if abs(q) >= lim:
                return f"{_trim(q / lim)} {suf}"
        return f"{_trim(q)} Ω"
    if dim == "farads":
        for lim, suf in ((Decimal("1E-6"), "µF"), (Decimal("1E-9"), "nF"),
                         (Decimal("1E-12"), "pF")):
            if abs(q) >= lim:
                return f"{_trim(q / lim)} {suf}"
        return f"{_trim(q)} F"
    if dim == "henries":
        return f"{_trim(q)} H"
    if dim == "volts":
        return f"{_trim(q)} V"
    if dim == "watts":
        return f"{_trim(q)} W"
    return _trim(q)


def _trim(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


# ---------------------------------------------------------------------------
# A parsed surface reading
# ---------------------------------------------------------------------------
class Reading:
    """What one surface says about one part.

    `dim`/`q` is the principal quantity. `volts`/`watts` are secondary ratings
    where the surface states them (most do not, and silence is not a
    disagreement). `token` is the designation for non-numeric parts. `problem`
    is set when the string could not be resolved — that is a finding, not a
    pass."""

    __slots__ = ("surface", "raw", "dim", "q", "volts", "watts", "token",
                 "ratio", "problem", "aliases", "sections")

    def __init__(self, surface, raw, dim=None, q=None, volts=None, watts=None,
                 token=None, problem=None, ratio=None, aliases=None,
                 sections=None):
        self.surface, self.raw = surface, raw
        self.dim, self.q = dim, q
        self.volts, self.watts, self.token, self.problem = volts, watts, token, problem
        self.ratio = ratio
        self.aliases = aliases or frozenset()
        self.sections = sections

    def stated(self) -> str:
        if self.sections is not None:
            return " + ".join(_eng(x, self.dim) for x in self.sections)
        if self.ratio is not None:
            return " : ".join(_eng(x, "ohms") for x in self.ratio)
        if self.q is not None:
            extra = []
            if self.volts is not None:
                extra.append(_eng(self.volts, "volts"))
            if self.watts is not None:
                extra.append(_eng(self.watts, "watts"))
            return _eng(self.q, self.dim) + ("  [" + " · ".join(extra) + "]" if extra else "")
        if self.token:
            return self.token
        return "—"


# ---------------------------------------------------------------------------
# Surface 1 — bom.yaml, house units
# ---------------------------------------------------------------------------
_RE_OHMS = re.compile(r"^≈?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKM])?\s*(?:Ω|ohms?)$")
_RE_FARADS = re.compile(r"^≈?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([µμunp])F$")
_RE_HENRY = re.compile(r"^≈?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*H$")
_RE_VOLTS = re.compile(r"^≈?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*V(?:DC)?$")
_RE_WATTS = re.compile(r"^≈?\s*(\S+)\s*W$")
_RE_PAREN = re.compile(r"\s*\([^()]*\)\s*$")
# The factory's value-voltage shorthand loose inside a house string. It reads as
# one number and means two; era_pair() refuses it and so does this.
_RE_DASH_PAIR = re.compile(r"\d\s*-\s*\d")

_OHM_MULT = {None: Decimal(1), "": Decimal(1), "k": Decimal("1E3"),
             "K": Decimal("1E3"), "M": Decimal("1E6")}
_FARAD_MULT = {"µ": Decimal("1E-6"), "μ": Decimal("1E-6"), "u": Decimal("1E-6"),
               "n": Decimal("1E-9"), "p": Decimal("1E-12")}


# A transformer states an impedance RATIO, not a single quantity, and the two
# surfaces write it differently by convention: the parts list in house units
# ("≈5 kΩ : 8 Ω"), the schematic in drafting shorthand with the topology in
# front ("SE 5k:8", "PP OT 4k a-a"). Same claim, so it is compared as a ratio.
_RE_RATIO_SPLIT = re.compile(r"\s*:\s*")
_RE_RATIO_LEAD = re.compile(r"^(?:SE|PP|OT|PP\s+OT|SE\s+OT)\s+", re.I)


def _ratio(s: str) -> tuple[Decimal, ...] | None:
    t = _RE_RATIO_LEAD.sub("", _RE_PAREN.sub("", str(s)).strip()).strip()
    t = t.replace("≈", "").replace("~", "").strip()
    if ":" not in t:
        return None
    legs = []
    for leg in _RE_RATIO_SPLIT.split(t):
        leg = re.sub(r"\b(?:a-a|p-p|ct|sec|prim)\b", "", leg, flags=re.I).strip()
        m = re.match(r"^(\d[\d,]*(?:\.\d+)?)\s*([kKM])?\s*(?:Ω|ohms?)?$", leg)
        if not m:
            return None
        n = _dec(m.group(1))
        if n is None:
            return None
        legs.append(n * _OHM_MULT[m.group(2)])
    return tuple(legs) if len(legs) >= 2 else None


# A multi-section can is one part with two (or three) capacitances: the parts
# list writes "25 µF + 50 µF", the drawings "25u+25u", "50+50u", "25/50u",
# "2x50u", "50 µF · 450 V (×2)". All say the same thing, so the comparable form
# is the SECTION VECTOR, not a single number — refusing them (as an earlier cut
# of this script did) hid twenty real agreements behind twenty "unreadable" rows.
_RE_SECTION_SPLIT = re.compile(r"\s*[+/]\s*")
# A COUNT of identical parts, not a section vector: "16 µF · 450 V (×2)" is two
# 16 µF cans and "2x50u" is two 50 µF cans — each part is still worth its single
# value, and the schematic symbol for one of them rightly letters just "16u".
# Reading the count as a 16+16 dual-section can invented a part the corpus never
# claimed and reported five false mismatches against the surfaces that got it right.
_RE_COUNT_PAREN = re.compile(r"\(\s*[x×]\s*\d+\s*\)")
_RE_COUNT_PREFIX = re.compile(r"^\d+\s*[x×]\s*(?=[.\d])", re.I)


def _strip_count(text: str) -> str:
    return _RE_COUNT_PREFIX.sub("", _RE_COUNT_PAREN.sub("", str(text)).strip()).strip()


def _sections(text: str, dim: str, unit_parser) -> tuple[Decimal, ...] | None:
    """Section vector for a genuine multi-section can, or None if it is not one.

    Only the joined forms count — "25 µF + 25 µF", "25u+25u", "50+50u",
    "25/50u". A repeat count is stripped first (see _strip_count)."""
    s = _strip_count(text)
    parts = [p.strip() for p in _RE_SECTION_SPLIT.split(s) if p.strip()]
    if len(parts) < 2:
        return None

    # The unit is often written once, on the last section ("50+50u", "25/50u").
    unit_suffix = ""
    mu = re.search(r"([µμunp]F?|µF)\s*$", parts[-1])
    if mu:
        unit_suffix = mu.group(1)
    out = []
    for p in parts:
        q = unit_parser(p)
        if q is None and unit_suffix and re.fullmatch(r"[\d.,]+", p):
            q = unit_parser(p + unit_suffix)
        if q is None:
            return None
        out.append(q)
    return tuple(out)


def effective_dim(cat: str, bom_value: str) -> str | None:
    """The dimension a part's value is stated in.

    Category usually decides it, but two categories carry a quantity the
    category name does not name: `other` holds the pots (a resistance, plus a
    taper suffix the category has no word for), and `xfmr` holds an impedance
    ratio. Deciding the dimension once, from the parts list, keeps every surface
    parsed against the same expectation instead of each guessing."""
    prim = _RE_PAREN.sub("", primary_value(bom_value)).strip()
    if cat == "choke":
        fields = [_RE_PAREN.sub("", t).strip() for t in str(bom_value).split("·")]
        if any(_RE_HENRY.match(f) or _henry_range(f) for f in fields):
            return "henries"
        # A choke's parts-list value is whatever the drawing actually printed:
        # an inductance, a range, a DC resistance, or — most often — the factory
        # part number and nothing else. Forcing henries onto all four turned
        # every agreeing part-number pair into an "unreadable inductance" row.
        if _RE_HENRY.match(prim) or _henry_range(prim):
            return "henries"
        if _RE_OHMS.match(prim.replace("≈", "").replace("~", "").strip()) or \
                re.match(r"^[≈~]?\s*[\d.,]+\s*(?:Ω|ohms?)\s*DCR", prim, re.I):
            return "ohms"
        return None                         # compared as a designation
    if cat in DIMENSION:
        return DIMENSION[cat]
    if _ratio(prim):
        return "ratio"
    for rx, dim in ((_RE_OHMS, "ohms"), (_RE_FARADS, "farads"), (_RE_HENRY, "henries")):
        if rx.match(_RE_TAPER.sub("", prim)):
            return dim
    if cat == "other" and _RE_CURRENT.match(prim):
        return "amps"
    return None


# "10–20 H" (parts list, en dash) and "10-20H" (drawing, hyphen) are the same
# stated range — a swinging choke's two ends, not a single inductance.
_RE_HENRY_RANGE = re.compile(
    r"^[≈~]?\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*H$", re.I)


def _henry_range(s: str) -> tuple[Decimal, Decimal] | None:
    m = _RE_HENRY_RANGE.match(str(s).strip())
    if not m:
        return None
    a, b = _dec(m.group(1)), _dec(m.group(2))
    return None if a is None or b is None else (a, b)


def _current(s: str) -> Decimal | None:
    m = _RE_CURRENT.match(_norm_token(s).upper())
    if not m:
        return None
    n = _dec(m.group(1))
    if n is None:
        return None
    return n / Decimal(1000) if m.group(2).lower() == "ma" else n


# Pot taper suffix in a house value: "250 kΩ-A", "1 MΩ-L". The taper is a
# separate fact from the resistance and is not compared as a quantity.
_RE_TAPER = re.compile(r"-(?:A|L|RA|C|W)\b")


def read_bom(value: str, cat: str, dim=_UNSET) -> Reading:
    toks = [t.strip() for t in str(value).split("·")]
    prim = _RE_TAPER.sub("", _RE_PAREN.sub("", toks[0]).strip()).strip()
    rest = toks[1:]
    if dim is _UNSET:
        dim = DIMENSION.get(cat)

    volts = watts = None
    for t in rest:
        mv = _RE_VOLTS.match(t)
        if mv and volts is None:
            volts = _dec(mv.group(1))
            continue
        mw = _RE_WATTS.match(t)
        if mw and watts is None:
            w = _dec(mw.group(1))
            if w is not None:
                watts = w

    if dim == "ratio":
        r = _ratio(prim)
        if r:
            return Reading("bom.yaml", value, "ratio", ratio=r)
        return Reading("bom.yaml", value, token=_designation(toks[0], cat),
                       aliases=_designation_set(toks[0], cat))

    if dim == "amps":
        a = _current(prim)
        if a is not None:
            return Reading("bom.yaml", value, "amps", a)
        return Reading("bom.yaml", value, token=_designation(toks[0], cat),
                       aliases=_designation_set(toks[0], cat))

    if dim == "farads":
        secs = _sections(prim, dim, _bom_farads)
        if secs:
            return Reading("bom.yaml", value, "farads", volts=volts, sections=secs)

    if dim == "henries":
        for f in [prim] + [_RE_PAREN.sub("", t).strip() for t in rest]:
            hr = _henry_range(f)
            if hr:
                return Reading("bom.yaml", value, "henries", sections=hr)
            mh = _RE_HENRY.match(f)
            if mh:
                n = _dec(mh.group(1))
                if n is not None:
                    return Reading("bom.yaml", value, "henries", n)

    if dim == "ohms" and cat == "choke":
        m = re.match(r"^[≈~]?\s*([\d.,]+)\s*([kKM])?\s*(?:Ω|ohms?)", prim)
        if m:
            n = _dec(m.group(1))
            if n is not None:
                return Reading("bom.yaml", value, "ohms", n * _OHM_MULT[m.group(2)])

    if _RE_DASH_PAIR.search(prim) and dim and not _henry_range(prim):
        return Reading("bom.yaml", value, dim=dim, problem=(
            "house value carries the factory value-voltage shorthand "
            f"('{prim}') — it reads as one number and means two"))

    if dim == "ohms":
        m = _RE_OHMS.match(prim)
        if m:
            n = _dec(m.group(1))
            if n is not None:
                return Reading("bom.yaml", value, "ohms", n * _OHM_MULT[m.group(2)],
                               volts, watts)
    elif dim == "farads":
        m = _RE_FARADS.match(prim)
        if m:
            n = _dec(m.group(1))
            if n is not None:
                return Reading("bom.yaml", value, "farads", n * _FARAD_MULT[m.group(2)],
                               volts, watts)
    elif dim == "henries":
        m = _RE_HENRY.match(prim)
        if m:
            n = _dec(m.group(1))
            if n is not None:
                return Reading("bom.yaml", value, "henries", n, volts, watts)

    if dim:
        # A quantity-bearing category whose value is not a quantity. Some are
        # legitimately descriptive ("presence/NFB network"); the grammar gate in
        # test_era_values.py owns that question, so this only notes it.
        return Reading("bom.yaml", value, dim=dim,
                       problem=f"not a plain {dim} value")
    return Reading("bom.yaml", value, token=_designation(toks[0], cat),
                       aliases=_designation_set(toks[0], cat))


def _bom_farads(tok: str) -> Decimal | None:
    m = _RE_FARADS.match(str(tok).strip())
    if not m:
        return None
    n = _dec(m.group(1))
    return None if n is None else n * _FARAD_MULT[m.group(2)]


def _norm_token(s: str) -> str:
    """Designation comparison form: case-folded, punctuation-flattened."""
    s = str(s).strip().lower()
    s = s.replace("×", "x").replace("·", " ").replace("−", "-")
    s = re.sub(r"[\s_]+", " ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# Designations — comparing a NAME, not a number
# ---------------------------------------------------------------------------
# A schematic symbol inherits its library's generic Value ("OT", "CHOKE",
# "POT") when the draughtsman states the part's identity elsewhere. That is a
# placeholder, not a competing claim, and treating it as one buries the real
# findings under a hundred rows saying a transformer is called "OT".
_NO_CLAIM = {
    "ot", "pt", "choke", "pot", "sw", "jack", "lamp", "fuse", "tank", "opto",
    "inlet", "triode", "pentode", "diode", "elec", "spkr", "link", "gnd",
    "ground", "n/a", "r", "c", "part not legible", "pp ot", "se ot", "3-pin",
}
# Diode shorthand as the drawings write it, against the parts list's prose.
_DIODE_SYNONYM = {"si": "silicon", "sel": "selenium", "se": "selenium",
                  "ge": "germanium"}
_DIODE_MATERIALS = {"silicon", "selenium", "germanium", "copper oxide"}
_RE_DIODE_STRIP = re.compile(
    r"\b(?:diode|rectifier|rect\.?|class|type|bridge)\b|-class")
_RE_COUNT_SUFFIX = re.compile(r"\s*[x×]\s*\d+$")
# Role notes hung off a tube's type on the drawing: "7025 norm", "ECC83 osc",
# "12AT7 rev drv", "12AX7 driver + tremolo". The TYPE is the claim.
_RE_TUBE_TYPE = re.compile(
    r"^\s*([0-9]{1,2}[A-Z]{1,3}[0-9]{0,2}[A-Z]{0,3}|E[A-Z]{2}[0-9]{2}[A-Z]?|"
    r"[A-Z]{2}[0-9]{2,4}|[0-9]{4})\b", re.I)
_RE_MAKER = re.compile(
    r"^(?:fender|valco|marshall|vox|ampeg|hiwatt|partridge|drake|haddon|"
    r"supro|gibson|danelectro|jensen|triad|schumacher)\s+", re.I)
# Fuse / mains current ratings: "3 A", "2A slo-blo", "T500mA", "1 A slo-blo".
_RE_CURRENT = re.compile(r"^(?:T|F)?\s*(\d+(?:\.\d+)?)\s*(mA|A)\b", re.I)


_RE_PAREN_ANY = re.compile(r"\(([^()]*)\)")


def _designation(raw: str, cat: str) -> str | None:
    """Every name a surface accepts for a part, joined for display.

    A parenthetical in a parts-list value is an ALIAS, not a gloss to discard:
    "12AX7 (7025)" states that either designation is right for this socket, and
    a drawing that letters "7025" is agreeing with it, not contradicting it.
    Comparison is therefore set intersection — see _designation_set()."""
    names = sorted(_designation_set(raw, cat))
    return " / ".join(names) if names else None


def _designation_set(raw: str, cat: str) -> frozenset[str]:
    out = set()
    primary = _designation_one(raw, cat)
    if primary:
        out.add(primary)
    for alias in _RE_PAREN_ANY.findall(str(raw)):
        a = _designation_one(alias, cat)
        if a:
            out.add(a)
    return frozenset(out)


def _designation_one(raw: str, cat: str) -> str | None:
    """The comparable name a surface states for a non-numeric part, or None
    when the surface makes no claim about identity at all."""
    s = _norm_token(_RE_PAREN.sub("", str(raw)).strip())
    if not s or s in _NO_CLAIM:
        return None

    if cat == "tube":
        m = _RE_TUBE_TYPE.match(s)
        if not m:
            return None
        # Resolve through the corpus's OWN valve-equivalence table — every
        # reference/tubes/*.yaml `also_known_as` list plus the EU/US supplement
        # render_layouts already uses to pick a socket's basing. Two surfaces
        # that name one valve under two accepted names are agreeing, and this
        # archive says so in its own data: a 7025 IS the low-noise 12AX7 whose
        # basing the drawing anchors to, and "5Y3-GT" and "5Y3GT" are one
        # rectifier written two ways. Nine of the twenty-eight findings this
        # gate reported were that difference in spelling, which buried the
        # question it exists to answer — does any surface name a DIFFERENT
        # valve? Anything the table does not know still compares verbatim.
        tok = m.group(1).replace("-", "")
        return resolve_tube_slug(tok) or tok

    if cat == "diode":
        s = _RE_COUNT_SUFFIX.sub("", s)
        s = _RE_DIODE_STRIP.sub("", s).strip(" ,-")
        s = re.sub(r"\s+", " ", s).strip()
        s = _DIODE_SYNONYM.get(s, s)
        if s in _DIODE_MATERIALS:
            return s
        # A part number is a claim; a position note ("series leg A, upper") is
        # not, and neither is a role note left over from a stripped phrase.
        for t in s.split():
            if re.search(r"\d", t) and re.fullmatch(r"[a-z]{0,3}\d[a-z0-9-]*", t):
                return t.strip(".,")
        return None

    if cat in ("xfmr", "choke"):
        # The parts list writes the maker in front of the factory part number;
        # the drawing letters the number alone. The number is the claim — an
        # impedance in the same string ("8/15 ohm", "4k a-a") is a different
        # fact and is not a part number, so it must not be compared as one.
        s = _RE_MAKER.sub("", s).strip()
        for t in s.split():
            t = t.strip(".,")
            if not re.fullmatch(r"[a-z]*\d[a-z0-9-]*", t):
                continue
            if len(t) < 4 or re.fullmatch(r"\d{1,3}k?", t):
                continue                    # an impedance or a tap, not a number
            return t
        return None

    # `other` is a grab-bag — a switch's pole count against its panel function,
    # a jack's thread size against its diameter. Those are different facts, not
    # rival claims, so only the ones with a real unit are compared (fuses).
    return None


# ---------------------------------------------------------------------------
# Surface 2 — schematic.kicad_sch symbol Value
# ---------------------------------------------------------------------------
# Annotation words a draughtsman hangs off a schematic value ("1M vol",
# "22k NFB", "100k presence"). They are a role note, not part of the quantity.
_SCH_TRAILING_WORD = re.compile(
    r"[\s·]+(?:vol|volume|bass|treb|treble|mid|middle|presence|pres\.?|int|intens\.?|"
    r"intensity|speed|bal|balance|bias|adj|lin|log|trim|master|preamp|rev|reverb|"
    r"cut|top cut|nfb|fb|est|info\.?|dual|sec|a-a|CF|osc|mod|Bass Treble|Presence)$",
    re.I)
_SCH_TOLERANCE = re.compile(r"^\d+(?:\.\d+)?\s*%$")
_SCH_WATTS = re.compile(r"^(\d+(?:\.\d+)?)\s*W$", re.I)
_SCH_VOLTS = re.compile(r"^(\d+(?:\.\d+)?)\s*V$", re.I)
# RKM / IEC 60062 infix notation: 2k2, 1k5, 4k7, 1M8, 1n0.
_RKM = re.compile(r"^(\d+)([kKMRunp])(\d+)$")
_SCH_OHMS = re.compile(r"^(\d[\d,]*(?:\.\d+)?)\s*(k|K|M|MEG|meg|R|r)?$")
_SCH_FARADS = re.compile(r"^(\.\d+|\d[\d,]*(?:\.\d+)?)\s*([uµnp])F?$", re.I)
_SCH_PF = re.compile(r"^(\d[\d,]*(?:\.\d+)?)\s*pF$", re.I)
_SCH_HENRY = re.compile(r"^(\d+(?:\.\d+)?)\s*H$", re.I)
# Multi-section cans and value ranges — one string, more than one quantity.
_SCH_MULTI = re.compile(r"[\d.][a-zµ]?\s*[+/]\s*[.\d]", re.I)
_SCH_TAPER = re.compile(r"-(?:A|L|RA|C|W)$", re.I)


def read_sch(value: str, cat: str, dim=_UNSET) -> Reading | None:
    raw = str(value)
    if dim is _UNSET:
        dim = DIMENSION.get(cat)
    s = _RE_PAREN.sub("", raw).strip().rstrip("*").strip()

    if dim == "ratio":
        r = _ratio(s)
        if r:
            return Reading("schematic", raw, "ratio", ratio=r)
        return Reading("schematic", raw, token=_designation(raw, cat),
                       aliases=_designation_set(raw, cat))

    if dim == "amps":
        a = _current(s)
        if a is not None:
            return Reading("schematic", raw, "amps", a)
        return Reading("schematic", raw, token=_designation(raw, cat),
                       aliases=_designation_set(raw, cat))

    # Peel role annotations off the tail until none remain.
    while True:
        s2 = _SCH_TRAILING_WORD.sub("", s).strip()
        if s2 == s:
            break
        s = s2

    fields = [f.strip() for f in re.split(r"[\s·]+", s) if f.strip()]
    volts = watts = None
    keep = []
    for f in fields:
        if _SCH_TOLERANCE.match(f):
            continue
        mw = _SCH_WATTS.match(f)
        if mw and watts is None and keep:      # a bare "5W" only after a value
            watts = _dec(mw.group(1))
            continue
        mv = _SCH_VOLTS.match(f)
        if mv and volts is None and keep:
            volts = _dec(mv.group(1))
            continue
        keep.append(f)

    if not keep:
        return Reading("schematic", raw, dim=dim, problem="empty value")

    # "2x50u" is two 50 µF cans, the same claim the parts list makes with
    # "(×2)" — a repeat count, not part of the value.
    head = _strip_count(keep[0])
    tail = keep[1:]

    if not dim:
        return Reading("schematic", raw, token=_designation(raw, cat),
                       aliases=_designation_set(raw, cat))

    # The era value-voltage shorthand and multi-section cans state more than one
    # quantity in one token. Neither can be proved equal to a single BOM value.
    if dim == "farads" and _SCH_MULTI.search(head):
        secs = _sections(head, dim, lambda t: _sch_quantity(t, "farads"))
        if secs:
            return Reading("schematic", raw, "farads", volts=volts, sections=secs)
        return Reading("schematic", raw, dim=dim, problem=(
            f"'{head}' states more than one section/value in one token"))

    if dim == "henries":
        hr = _henry_range(head)
        if hr:
            return Reading("schematic", raw, "henries", sections=hr)

    # "100u-25" / ".01u-400" / "30-450u" — value-voltage pairs, and the last of
    # those is genuinely ambiguous (30 µF at 450 V, or a 30..450 range?).
    m_pair = re.match(r"^(.+?)-(\d+(?:\.\d+)?)$", head)
    if m_pair and not _SCH_TAPER.search(head):
        lead, trail = m_pair.group(1), m_pair.group(2)
        lead_q = _sch_quantity(lead, dim)
        if lead_q is not None and re.search(r"[uµnpFkKMR]", lead, re.I):
            # unit on the leading half: unambiguous, trailing half is volts
            return Reading("schematic", raw, dim, lead_q, volts or _dec(trail), watts)
        return Reading("schematic", raw, dim=dim, problem=(
            f"'{head}' is the factory value-voltage shorthand with no unit on "
            "the leading half — it cannot be read as one quantity"))

    q = _sch_quantity(head, dim)
    if q is None:
        if _norm_token(" ".join(keep)) in _NO_CLAIM:
            return None          # library placeholder: the symbol states nothing
        return Reading("schematic", raw, dim=dim,
                       problem=f"'{head}' is not a readable {dim} value")

    # Anything left after the quantity that still looks numeric is unexplained.
    for t in tail:
        if re.search(r"\d", t) and not _SCH_TOLERANCE.match(t):
            return Reading("schematic", raw, dim, q, volts, watts, problem=(
                f"unexplained trailing field '{t}'"))
    return Reading("schematic", raw, dim, q, volts, watts)


def _sch_quantity(tok: str, dim: str) -> Decimal | None:
    # "~110" — the drawings mark an estimated or measured-approximate figure
    # with a tilde, exactly as the parts list marks it with "≈". Same number.
    t = tok.strip().replace(",", "").lstrip("~≈").strip()
    t = _SCH_TAPER.sub("", t)
    if dim == "ohms":
        m = _RKM.match(t)
        if m and m.group(2) in "kKMR":
            whole, suf, frac = m.groups()
            n = _dec(f"{whole}.{frac}")
            return None if n is None else n * {"k": Decimal("1E3"), "K": Decimal("1E3"),
                                               "M": Decimal("1E6"), "R": Decimal(1)}[suf]
        m = _SCH_OHMS.match(t)
        if m:
            n = _dec(m.group(1))
            if n is None:
                return None
            suf = (m.group(2) or "").upper()
            mult = {"": Decimal(1), "R": Decimal(1), "K": Decimal("1E3"),
                    "M": Decimal("1E6"), "MEG": Decimal("1E6")}[suf]
            return n * mult
        return None
    if dim == "farads":
        m = _SCH_PF.match(t)
        if m:
            n = _dec(m.group(1))
            return None if n is None else n * Decimal("1E-12")
        m = _RKM.match(t)
        if m and m.group(2) in "unp":
            whole, suf, frac = m.groups()
            n = _dec(f"{whole}.{frac}")
            return None if n is None else n * _FARAD_MULT[suf]
        m = _SCH_FARADS.match(t)
        if m:
            n = _dec(m.group(1))
            suf = m.group(2).lower().replace("µ", "u")
            return None if n is None else n * _FARAD_MULT[suf]
        return None
    if dim == "henries":
        m = _SCH_HENRY.match(t)
        if m:
            return _dec(m.group(1))
        return None
    return None


# ---------------------------------------------------------------------------
# Surface 3 — the era sheet lettering (derived from bom.yaml by era_pair)
# ---------------------------------------------------------------------------
_ERA_RES = re.compile(r"^(\d+(?:\.\d+)?)(MEG|K)?(?:-(\d+(?:\.\d+)?))?$")
_ERA_MFD = re.compile(r"^(\d+(?:\.\d+)?)MFD$")
# A twin can, lettered the way the era sheets lettered it: sections joined by a
# slash with the unit written once — "25/25MFD", "50+50MFD".
_ERA_MULTI_MFD = re.compile(r"^(\d+(?:\.\d+)?(?:\s*[/+]\s*\d+(?:\.\d+)?)+)MFD$")
_ERA_PF = re.compile(r"^(\d+(?:\.\d+)?)PF$")
_ERA_FILM = re.compile(r"^(\.\d+|\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?$")
_ERA_VOLTS = re.compile(r"^(\d+(?:\.\d+)?)V\b")


def read_era(value: str, cat: str, dim=_UNSET) -> Reading | None:
    """Round-trip the sheet lettering back to a quantity.

    era_pair() refuses anything it cannot letter, handing the house tokens back
    untouched — by design, and not a finding. So a refusal returns None; only a
    string it DID letter is round-tripped."""
    v1, v2 = era_pair(value, cat)
    raw = v1 + (f" / {v2}" if v2 else "")
    if dim is _UNSET:
        dim = DIMENSION.get(cat)
    if dim not in ("ohms", "farads"):
        # era_pair() letters resistances and capacitances only; a pot's taper
        # suffix and a transformer's ratio are free-standing hardware labels
        # that keep house units, and it hands them straight back.
        return None
    house_prim = _RE_PAREN.sub("", primary_value(value)).strip()
    refused = str(v1).strip() in (house_prim, primary_value(value).strip())
    if not dim:
        return None
    if refused:
        return None

    if dim == "ohms":
        m = _ERA_RES.match(v1)
        if not m:
            return Reading("sheet(era)", raw, dim=dim,
                           problem=f"lettering '{v1}' is not readable era resistor form")
        n = _dec(m.group(1))
        mult = {None: Decimal(1), "K": Decimal("1E3"), "MEG": Decimal("1E6")}[m.group(2)]
        watts = _dec(m.group(3)) if m.group(3) else None
        return Reading("sheet(era)", raw, "ohms", None if n is None else n * mult,
                       None, watts)

    if dim == "farads":
        volts = None
        if v2:
            mv = _ERA_VOLTS.match(v2)
            if mv:
                volts = _dec(mv.group(1))
        m = _ERA_MULTI_MFD.match(v1)
        if m:
            secs = [_dec(t) for t in re.split(r"\s*[/+]\s*", m.group(1))]
            if all(x is not None for x in secs):
                return Reading("sheet(era)", raw, "farads", volts=volts,
                               sections=tuple(x * Decimal("1E-6") for x in secs))
        m = _ERA_MFD.match(v1)
        if m:
            n = _dec(m.group(1))
            return Reading("sheet(era)", raw, "farads",
                           None if n is None else n * Decimal("1E-6"), volts)
        m = _ERA_PF.match(v1)
        if m:
            n = _dec(m.group(1))
            return Reading("sheet(era)", raw, "farads",
                           None if n is None else n * Decimal("1E-12"), volts)
        m = _ERA_FILM.match(v1)
        if m:
            n = _dec(m.group(1))            # bare decimal microfarads
            return Reading("sheet(era)", raw, "farads",
                           None if n is None else n * Decimal("1E-6"),
                           volts or (_dec(m.group(2)) if m.group(2) else None))
        return Reading("sheet(era)", raw, dim=dim,
                       problem=f"lettering '{v1}' is not readable era capacitor form")
    return None


# ---------------------------------------------------------------------------
# Surface 4 — layout.yaml
# ---------------------------------------------------------------------------
def read_layout_label(label: str, cat: str, ref: str, dim=_UNSET) -> Reading | None:
    """A layout label states a quantity only when it carries one.

    Most are positional ("Ch.1 volume", "C6"); those say nothing to check. A
    tube label states its type ("V1 · 12AX7") and a hand-written stub states a
    value ("27 kΩ") — those are claims, and must match."""
    s = str(label).strip()
    parts = [p.strip() for p in s.split("·")]
    cand = parts[-1] if len(parts) > 1 else s
    if cand == ref or _norm_token(cand) == _norm_token(ref):
        return None
    if dim is _UNSET:
        dim = DIMENSION.get(cat)
    if dim in ("ohms", "farads", "henries"):
        r = read_bom(cand, cat, dim)
        if r.q is None:
            return None                     # positional label, no claim made
        return Reading("layout.label", s, r.dim, r.q, r.volts, r.watts)
    if dim == "ratio":
        return None                         # "Output trans" — positional
    if cat in ("tube", "diode", "xfmr"):
        tok = _designation(cand, cat)
        if tok:
            return Reading("layout.label", s, token=tok,
                           aliases=_designation_set(cand, cat))
    return None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
_RE_UNSTATED = re.compile(
    r"not (?:printed|marked|legible|recorded|stated|given)|no type marked|"
    r"not yet (?:read|documented)|^n/a$", re.I)


def _types_compatible(a: Reading, b: Reading) -> bool:
    """Two designations agree if they name the same part under any accepted name.

    Two ways they can agree while reading differently:
      * alias sets overlap — "12AX7 (7025)" and "7025" are one socket, and the
        parts list said so itself by printing both;
      * one names a material class the other's part number belongs to — a
        drawing lettering "1N4007" is not contradicting a list saying "silicon".
    Flagging either would bury the rows where two surfaces name two different
    parts, which is the only thing here that can mislead a builder."""
    sa = a.aliases or ({a.token} if a.token else set())
    sb = b.aliases or ({b.token} if b.token else set())
    if sa & sb:
        return True
    both = sa | sb
    return bool(both & _DIODE_MATERIALS) and not (both <= _DIODE_MATERIALS)


def compare(readings: list[Reading]) -> list[dict]:
    """Every pair of surfaces that state the same kind of thing must agree."""
    out = []
    for r in readings:
        if r.problem:
            # "value not printed" is not an ambiguity, it is the corpus keeping
            # its own honesty rule: the source did not state a figure and this
            # archive refuses to invent one. It is reported separately so it
            # cannot dilute the rows that are genuinely unreadable.
            kind = "UNSTATED" if _RE_UNSTATED.search(r.raw) else "AMBIGUOUS"
            out.append({"kind": kind, "surfaces": [r.surface],
                        "values": [r.raw], "detail": r.problem})

    usable = [r for r in readings if not r.problem]
    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            a, b = usable[i], usable[j]
            if a.sections is not None or b.sections is not None:
                sa = a.sections if a.sections is not None else (
                    (a.q,) if a.q is not None else None)
                sb = b.sections if b.sections is not None else (
                    (b.q,) if b.q is not None else None)
                if sa is None or sb is None:
                    continue
                # Section ORDER on a can is not a claim this corpus makes
                # consistently; the set of sections is.
                if len(sa) != len(sb) or not all(
                        _close(x, y) for x, y in zip(sorted(sa), sorted(sb))):
                    out.append({"kind": "MISMATCH",
                                "surfaces": [a.surface, b.surface],
                                "values": [f"{a.raw} → {a.stated()}",
                                           f"{b.raw} → {b.stated()}"],
                                "detail": f"{a.stated()} ≠ {b.stated()}"})
            elif a.ratio is not None and b.ratio is not None:
                if len(a.ratio) != len(b.ratio) or not all(
                        _close(x, y) for x, y in zip(a.ratio, b.ratio)):
                    out.append({"kind": "MISMATCH",
                                "surfaces": [a.surface, b.surface],
                                "values": [f"{a.raw} → {a.stated()}",
                                           f"{b.raw} → {b.stated()}"],
                                "detail": f"{a.stated()} ≠ {b.stated()}"})
            elif a.q is not None and b.q is not None:
                if a.dim != b.dim:
                    out.append({"kind": "UNIT-MISMATCH",
                                "surfaces": [a.surface, b.surface],
                                "values": [f"{a.raw} → {a.stated()}",
                                           f"{b.raw} → {b.stated()}"],
                                "detail": f"{a.dim} vs {b.dim}"})
                elif not _close(a.q, b.q):
                    out.append({"kind": "MISMATCH",
                                "surfaces": [a.surface, b.surface],
                                "values": [f"{a.raw} → {_eng(a.q, a.dim)}",
                                           f"{b.raw} → {_eng(b.q, b.dim)}"],
                                "detail": f"{_eng(a.q, a.dim)} ≠ {_eng(b.q, b.dim)}"})
                else:
                    for field, dimn in (("volts", "volts"), ("watts", "watts")):
                        va, vb = getattr(a, field), getattr(b, field)
                        if va is not None and vb is not None and not _close(va, vb):
                            out.append({"kind": f"{field.upper()}-MISMATCH",
                                        "surfaces": [a.surface, b.surface],
                                        "values": [a.raw, b.raw],
                                        "detail": f"{_eng(va, dimn)} ≠ {_eng(vb, dimn)}"})
            elif a.token and b.token and a.q is None and b.q is None:
                if a.token != b.token and not _types_compatible(a, b):
                    out.append({"kind": "TYPE-MISMATCH",
                                "surfaces": [a.surface, b.surface],
                                "values": [a.raw, b.raw],
                                "detail": f"'{a.token}' ≠ '{b.token}'"})
    return out


# ---------------------------------------------------------------------------
# Per-amp driver
# ---------------------------------------------------------------------------
def _strip_unit(ref: str) -> str:
    """'V1A' -> 'V1' — schematic multi-unit symbols share one designator."""
    if len(ref) > 1 and ref[-1].isalpha() and ref[-2].isdigit():
        return ref[:-1]
    return ref


def load_sch_values(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(exact-designator map, multi-unit-base map).

    Both are needed, and the exact one must win. A tube is drawn as V1A and V1B
    and listed once as V1, so the base map is what links those. But this corpus
    also uses semantic designators whose tail happens to be a letter after a
    digit — RK1A/RK1B are two different cathode resistors, R1a/R1b/R1K are three
    different resistors, RS1 and RS1T are two. Folding those onto a base the way
    the tube rule does pools unrelated parts and manufactures mismatches
    between values that were never talking about the same component."""
    from kiutils.schematic import Schematic
    sch = Schematic.from_file(str(path))
    exact: dict[str, list[str]] = {}
    base: dict[str, list[str]] = {}
    for sym in sch.schematicSymbols:
        ref = val = None
        for prop in sym.properties:
            if prop.key == "Reference":
                ref = prop.value
            elif prop.key == "Value":
                val = prop.value
        if not ref:
            continue
        v = "" if val is None else val
        exact.setdefault(ref, []).append(v)
        base.setdefault(_strip_unit(ref), []).append(v)
    return exact, base


def check_amp(amp_dir: Path) -> list[dict]:
    findings = []
    bom_path, sch_path = amp_dir / "bom.yaml", amp_dir / "schematic.kicad_sch"
    if not bom_path.exists():
        return findings
    bom_raw = yaml.safe_load(bom_path.read_text()) or {}
    bom = {}
    for it in bom_raw.get("items", []):
        ref = it.get("ref")
        if ref and ref != "—":
            bom[ref] = {"value": str(it.get("value", "")), "part": str(it.get("part", ""))}

    sch_exact, sch_base = load_sch_values(sch_path) if sch_path.exists() else ({}, {})

    layout_labels: dict[str, list[str]] = {}
    unlinked: list[tuple[str, str]] = []
    lay_path = amp_dir / "layout.yaml"
    if lay_path.exists():
        lay = yaml.safe_load(lay_path.read_text()) or {}
        for it in (lay.get("offboard") or []) + (lay.get("parts") or []):
            ref = it.get("ref")
            if ref and it.get("label"):
                layout_labels.setdefault(ref, []).append(str(it["label"]))
            if not ref:
                av = annotation_value(it)
                if av:
                    unlinked.append((str(it.get("id") or it.get("label") or "?"), av))

    for ref in sorted(bom):
        rec = bom[ref]
        cat = category(rec["part"])
        dim = effective_dim(cat, rec["value"])
        readings = [read_bom(rec["value"], cat, dim)]

        # Exact designator first; the multi-unit base is only a fallback for a
        # part the schematic splits across lettered units (V1 drawn as V1A/V1B).
        sch_vals = sch_exact.get(ref) or sch_base.get(ref, [])
        for sv in sch_vals:
            if sv.strip():
                sr = read_sch(sv, cat, dim)
                if sr is not None:
                    readings.append(sr)
        era = read_era(rec["value"], cat, dim)
        if era is not None:
            readings.append(era)
        for lab in layout_labels.get(ref, []):
            lr = read_layout_label(lab, cat, ref, dim)
            if lr is not None:
                readings.append(lr)

        # Dedupe identical schematic readings (multi-unit symbols repeat one value).
        seen, uniq = set(), []
        for r in readings:
            key = (r.surface, r.raw)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)

        for f in compare(uniq):
            f.update({"amp": amp_dir.name, "ref": ref, "part": rec["part"], "cat": cat})
            findings.append(f)

    for ident, val in unlinked:
        findings.append({"amp": amp_dir.name, "ref": f"(ref-less {ident})",
                         "part": "layout annotation", "cat": "—",
                         "kind": "UNLINKED", "surfaces": ["layout.value"],
                         "values": [val],
                         "detail": "ref-less annotation value — no BOM or schematic "
                                   "surface exists to cross-check it against"})
    return findings


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Self-test — a gate that cannot fail proves nothing
# ---------------------------------------------------------------------------
# Every normalisation above exists to stop a *notation* difference reading as a
# *value* difference. Each one is also a chance to normalise away a real fault.
# So the pairs below are checked both ways: the ones that must agree, and the
# ones that must not. This is what stops the script from quietly degrading into
# "no findings, ever" as more conventions get absorbed.
_SELFTEST = [
    # (bom value, part, schematic value, must_agree)
    ("100 kΩ · ½ W", "Carbon comp resistor", "100k", True),
    ("100 kΩ · ½ W", "Carbon comp resistor", "10k", False),       # decade slip
    ("4,700 Ω", "Carbon comp resistor", "4.7k", True),
    ("4,700 Ω", "Carbon comp resistor", "4700k", False),
    ("1 MΩ", "Audio-taper potentiometer", "1M vol", True),
    ("1 MΩ", "Audio-taper potentiometer", "500k vol", False),
    ("2.2 kΩ · ½ W", "Carbon comp resistor", "2k2", True),        # RKM infix
    ("2.2 kΩ · ½ W", "Carbon comp resistor", "2k7", False),
    ("0.02 µF · 600 V", "Coupling capacitor", ".02u", True),
    ("0.02 µF · 600 V", "Coupling capacitor", ".002u", False),    # decade slip
    ("0.02 µF · 600 V", "Coupling capacitor", "20n", True),
    ("250 pF", "Mica capacitor", "250p", True),
    ("250 pF", "Mica capacitor", "250n", False),                  # unit slip
    ("25 µF · 25 V", "Electrolytic capacitor", "25u", True),
    ("25 µF · 25 V", "Electrolytic capacitor", "25u 450V", False),  # volts clash
    ("16 µF · 450 V (×2)", "Electrolytic capacitor", "16u", True),  # count, not sections
    ("25 µF + 25 µF", "Electrolytic capacitor (dual can)", "25u+25u", True),
    ("25 µF + 25 µF", "Electrolytic capacitor (dual can)", "25u+50u", False),
    ("470 Ω · 5 W", "Wirewound resistor", "470 5W", True),
    ("470 Ω · 5 W", "Wirewound resistor", "470 1W", False),       # wattage clash
    ("12AX7", "Preamp tube", "12AX7 norm", True),                 # role note
    ("12AX7 (7025)", "Preamp tube", "7025", True),                # stated alias
    ("12AX7", "Preamp tube", "12AY7", False),                     # different tube
    ("silicon", "Rectifier diode", "1N4007", True),               # class + member
    ("1N4007", "Rectifier diode", "1N4148", False),               # two parts
    ("Fender 125P1B", "Output transformer", "125P1B", True),
    ("Fender 125P1B", "Output transformer", "125A10B", False),
    ("≈5 kΩ : 8 Ω", "Output transformer", "SE 5k:8", True),
    ("≈5 kΩ : 8 Ω", "Output transformer", "SE 4k:8", False),
]


def selftest() -> int:
    bad = 0
    for value, part, sch_value, must_agree in _SELFTEST:
        cat = category(part)
        dim = effective_dim(cat, value)
        readings = [read_bom(value, cat, dim)]
        sr = read_sch(sch_value, cat, dim)
        if sr is not None:
            readings.append(sr)
        era = read_era(value, cat, dim)
        if era is not None:
            readings.append(era)
        diffs = [f for f in compare(readings) if f["kind"] != "UNSTATED"]
        agreed = not diffs
        if agreed != must_agree:
            bad += 1
            want = "agree" if must_agree else "DISAGREE"
            print(f"selftest FAIL: {value!r} [{part}] vs {sch_value!r} — "
                  f"expected {want}, got {[d['kind'] + ': ' + d['detail'] for d in diffs] or 'agreement'}")
    print(f"selftest: {len(_SELFTEST) - bad}/{len(_SELFTEST)} pairs behaved as specified")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("amps", nargs="*", help="amp ids (default: all)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any disagreement")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the gate still catches planted faults")
    ap.add_argument("--no-unlinked", action="store_true",
                    help="suppress the informational UNLINKED rows")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    ids = args.amps or sorted(d.name for d in AMPS.iterdir()
                              if d.is_dir() and not d.name.startswith("_"))
    findings = []
    for amp_id in ids:
        d = AMPS / amp_id
        if not d.is_dir():
            print(f"unknown amp: {amp_id}", file=sys.stderr)
            return 2
        findings.extend(check_amp(d))

    if args.no_unlinked:
        findings = [f for f in findings if f["kind"] != "UNLINKED"]

    if args.json:
        print(json.dumps({"amps": len(ids), "findings": findings}, indent=2))
    else:
        _print_table(findings, len(ids))

    hard = [f for f in findings if f["kind"] not in SOFT_KINDS]
    if args.strict and hard:
        return 1
    return 0


def _print_table(findings: list[dict], n_amps: int) -> None:
    if not findings:
        print(f"value consistency: {n_amps} amps, every surface agrees")
        return
    order = list(HARD_KINDS) + list(SOFT_KINDS)
    rank = {k: i for i, k in enumerate(order)}
    findings = sorted(findings, key=lambda f: (rank.get(f["kind"], 99), f["amp"], f["ref"]))

    w_amp = max(4, max(len(f["amp"]) for f in findings))
    w_ref = max(3, max(len(f["ref"]) for f in findings))
    w_kind = max(4, max(len(f["kind"]) for f in findings))
    print(f"{'AMP':<{w_amp}}  {'REF':<{w_ref}}  {'KIND':<{w_kind}}  SURFACES / VALUES")
    print("-" * (w_amp + w_ref + w_kind + 60))
    for f in findings:
        surf = " vs ".join(f["surfaces"])
        vals = "  ||  ".join(f["values"])
        print(f"{f['amp']:<{w_amp}}  {f['ref']:<{w_ref}}  {f['kind']:<{w_kind}}  "
              f"{surf}: {vals}")
        print(f"{'':<{w_amp + w_ref + w_kind + 6}}{f['detail']}")

    counts: dict[str, int] = {}
    for f in findings:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    hard = sum(v for k, v in counts.items() if k in HARD_KINDS)
    soft = sum(v for k, v in counts.items() if k in SOFT_KINDS)
    print()
    print(f"{len(findings)} findings across {n_amps} amps: " +
          ", ".join(f"{k}={v}" for k, v in sorted(counts.items(),
                                                  key=lambda kv: rank.get(kv[0], 99))))
    # The two counts mean different things and must never be added together.
    # A DISAGREEMENT is a defect: two surfaces state different quantities for one
    # part and a builder cannot tell which to trust. The rest are this archive
    # keeping its own honesty rule — a value the source never printed, or an
    # annotation the electrical model carries no designator for. Those are
    # published deliberately (AGENTS.md rule 5) and are not gated.
    print(f"  {hard} disagreement(s) — gated (--strict)")
    print(f"  {soft} declared-gap row(s) — informational: a value the source did "
          f"not print, or an annotation with no designator to cross-check against")


if __name__ == "__main__":
    sys.exit(main())
