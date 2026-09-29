# Declared capacitor polarity — 2026-09-28 audit

All 268 electrolytics drawn across the 40 layouts declare their positive
terminal with `plus: a | b`. Each declaration has an adjacent provenance
comment: 84 use a readable printed capacitor `+`, and 184 use documented DC
sign. The latter records the actual node levels and their origin (simulated
operating point, ideal supply, ground, resistor walk or bounded series-stack
joint); a page position is never treated as evidence. For four unmodelled
Fender oscillator cathodes plus the 5G9 cathode, the factory circuit establishes
a positive cathode relative to ground, while the automated DC check remains
undecided.

The original report was 203 right / 49 wrong / 16 undecided / 0 unmarked.
The current report is **252 right / 0 wrong / 16 undecided / 0 unmarked**.
All 49 known reversals are corrected. Source reads also move five previously
undecided marks to the source's positive lead; their automated verdict remains
undecided. No wiring claims or amp verification statuses change.

`pipeline/verify_layout_nets.py` now blocks reversed electrolytics on every
board. Its committed export includes per-board counts even for clean boards,
so an absent entry must be read as unknown, not as a successful check. The
source declaration and the electrical check are distinct evidence.

## Source read register

Read before the declarations were changed. The table gives the exact native
raster size and crop `[left, top, right, bottom]` in that raster. Wide crops
were split into strips no wider than 1800 px and inspected at native scale.
PDF rows use the embedded page image, without resampling; `m1959` is the
Unicord Rev B page (page 3), and Fender rows use the board-layout page except
6161 (schematic). AC15's available OA/031 image is only 900 × 723: it was
read for circuit identity, and its six declarations explicitly use DC sign,
not a claimed legible capacitor mark. DR103's SN903 preamp is a vector PDF,
rendered at 160 dpi (the pixels below are a render, not native scan pixels);
its readable C1 `+` is the cathode bypass. The supplemental early-1970s
layout supplies context only; it does not override the SN903 circuit.

Source images stay outside the repository. Layout comments carry the per-part
evidence; this table makes the source page and inspected area reproducible.
The B15N source is the published 12/68 revision C sheet already cited by the
corpus; reading its polarity does not broaden the corpus's historical claims.

| Board / supplement | Source | Pixels | Read crop |
| --- | --- | --- | --- |
| `5c1` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_champ_5c1_schem.pdf) | 6510 × 4718 | `195, 566, 6445, 3963` |
| `5d3` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_deluxe_5d3.pdf) | 6322 × 4514 | `1833, 1941, 6322, 3340` |
| `5e1` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_champ_5e1.pdf) | 5194 × 4394 | `1454, 1670, 5038, 3471` |
| `5e3` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_deluxe_5e3.pdf) | 6361 × 3988 | `1781, 1595, 6361, 2911` |
| `5e4a` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_super_5e4a.pdf) | 6210 × 3501 | `1242, 1295, 6210, 2696` |
| `5e5a` | [drawing](https://schematicheaven.net/fenderamps/pro_5e5a_schem.pdf) | 1506 × 864 | `301, 320, 1506, 691` |
| `5e6a` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_bassman_5e6a.pdf) | 6463 × 3809 | `1163, 1371, 6463, 3009` |
| `5f1` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_champ_5f1_schem.pdf) | 1147 × 988 | `321, 366, 1147, 800` |
| `5f10` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_harvard_5f10.pdf) | 6378 × 4525 | `1276, 1810, 6378, 3394` |
| `5f2a` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_princeton_5f2a.pdf) | 4882 × 4648 | `1367, 1487, 4833, 3532` |
| `5f4` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_super_5f4.pdf) | 6330 × 3228 | `1266, 1130, 6330, 2582` |
| `5f6` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_bassman_5f6.pdf) | 6286 × 3564 | `1886, 1176, 6286, 2958` |
| `5f6a` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_bassman_5f6a.pdf) | 6402 × 3641 | `2241, 1165, 6402, 3022` |
| `5f8a` | [drawing](https://schematicheaven.net/fenderamps/twin_5f8a_schem.pdf) | 6368 × 3218 | `2229, 998, 6368, 2574` |
| `5g9` | [drawing](https://web.archive.org/web/20150316142123/http://el34world.com/charts/Schematics/files/fender/Fender_TREMOLUX_5G9.pdf) | 6518 × 4128 | `2216, 1404, 6518, 3344` |
| `6161` | [drawing](https://el34world.com/charts/Schematics/files/Valco/Valco_6161.pdf) | 2901 × 1908 | `0, 0, 2901, 1908` |
| `6g2` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_princeton_6g2.pdf) | 6510 × 4752 | `2344, 1996, 6510, 3802` |
| `6g3` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_deluxe_6g3.pdf) | 6428 × 4213 | `2571, 1769, 6428, 3455` |
| `6g4` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_super_6g4_schem.pdf) | 2250 × 1269 | `698, 381, 2250, 1041` |
| `6g5` | [drawing](https://schematicheaven.net/fenderamps/pro_6g5_schem.pdf) | 2224 × 1331 | `712, 306, 2224, 998` |
| `6g6b` | [drawing](https://el34world.com/charts/Schematics/Files/Fender/Fender_bassman_6g6b.pdf) | 6366 × 4380 | `2292, 1402, 6366, 3329` |
| `aa1164` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_princeton_reverb_aa1164.pdf) | 5734 × 4467 | `2179, 1429, 4989, 2948` |
| `aa764` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_champ_AA764_layout.pdf) | 2171 × 1591 | `716, 716, 1693, 1193` |
| `aa764-vibro` | [drawing](https://el34world.com/charts/Schematics/Files/Fender/Fender_vibro_champ_aa764.pdf) | 6480 × 4058 | `2916, 1542, 5249, 3125` |
| `aa864-bassman` | [drawing](https://el34world.com/charts/Schematics/Files/Fender/Fender_bassman_aa864_layout.pdf) | 2115 × 1548 | `888, 619, 2030, 1192` |
| `aa964` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_princeton_AA964_layout.pdf) | 2166 × 1591 | `736, 668, 1928, 1241` |
| `ab165` | [drawing](https://el34world.com/charts/Schematics/Files/Fender/Fender_bassman_ab165_layout.pdf) | 2148 × 1578 | `687, 521, 2019, 1215` |
| `ab763` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_deluxe_reverb_ab763.pdf) | 6026 × 3650 | `1928, 1241, 5966, 2847` |
| `ab763-super` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_super_reverb_ab763_layout.pdf) | 2182 × 1394 | `655, 376, 2117, 1073` |
| `ab763-twin` | [drawing](https://el34world.com/charts/Schematics/files/Fender/Fender_twin_reverb_ab763_layout.pdf) | 2157 × 1397 | `690, 363, 2114, 1006` |
| `ac15` | [drawing](https://www.voxac30.org.uk/images/ac15_third_circuit/thumbs3/oa31.jpg) | 900 × 723 | `0, 0, 900, 723` |
| `ac30` | [drawing](https://www.voxac30.org.uk/vox_ac30_circuit_diagrams.html) | 3600 × 2492 | `0, 0, 3600, 2492` |
| `b15n` | [drawing](https://ampeg.com/data/6/0a000509142f661ff65a5784a/application/pdf/) | 3328 × 5080 | `899, 305, 2563, 4572` |
| `dr103` | [drawing](https://www.hiwatt.org/Schematics/DR103sn903pre.pdf) | 1760 × 1360 | `0, 0, 1760, 1360` |
| `dr103-layout` | [drawing](https://www.hiwatt.org/Layouts/DR103hiwattlayout.pdf) | 2417 × 1795 | `0, 0, 2417, 1795` |
| `ga40` | [drawing](https://schematicheaven.net/gibsonamps/ga40.pdf) | 1022 × 758 | `0, 0, 1022, 538` |
| `jtm100` | [drawing](https://www.drtube.com/schematics/marshall/1959t-66.gif) | 1068 × 759 | `0, 0, 1068, 630` |
| `jtm45` | [drawing](https://www.drtube.com/schematics/marshall/jtm45tr.gif) | 2194 × 1539 | `0, 0, 2194, 1154` |
| `m1959` | [drawing](https://el34world.com/charts/Schematics/files/Marshall/Marshall_jmp_superlead_100w_1959.pdf) | 1377 × 904 | `0, 136, 1377, 669` |
| `m1987` | [drawing](https://www.drtube.com/schematics/marshall/1987u.gif) | 2023 × 1304 | `0, 196, 2023, 913` |
| `m2204` | [drawing](https://www.drtube.com/schematics/marshall/2204pwrm.gif) | 2051 × 1408 | `0, 0, 2051, 1197` |
| `m2204-pre` | [drawing](https://www.drtube.com/schematics/marshall/2204prem.gif) | 2071 × 1436 | `0, 359, 1760, 1221` |

## DC checks still undecided

These entries remain in `reference/electrolytics.yaml`, including the selected
lead and both known/unknown node levels. The printed source determines the
mark where available; it does not supply missing simulator coverage.

| Board | Can | Declared positive lead | Evidence / remaining limit |
| --- | --- | --- | --- |
| `5g9` | `CK3` | `a` | factory cathode above ground, + at CK3.a; DC check remains undecided (CK3.a: reaches only ground, through RK3) |
| `6g2` | `CKTO` | `a` | factory cathode above ground, + at CKTO.a; DC check remains undecided (CKTO.a: reaches only ground, through RKTO) |
| `6g3` | `C11` | `a` | factory cathode above ground, + at C11.a; DC check remains undecided (C11.a: reaches only ground, through RK3) |
| `6g4` | `CTOK` | `a` | factory cathode above ground, + at CTOK.a; DC check remains undecided (CTOK.a: reaches only ground, through RTOK) |
| `6g5` | `CTOK` | `a` | factory cathode above ground, + at CTOK.a; DC check remains undecided (CTOK.a: reaches only ground, through RTOK) |
| `aa1164` | `CKTO` | `b` | source '+' at CKTO.b; DC check remains undecided (CKTO.b: reaches only ground, through RKTO) |
| `aa1164` | `CKD1` | `a` | source '+' at CKD1.a; DC check remains undecided (CKD1.b: on KD1B, which has no simulated volts) |
| `aa764` | `C5` | `b` | source '+' at C5.b; DC check remains undecided (C5.a: on KFB, which has no simulated volts) |
| `aa764-vibro` | `C5` | `b` | source '+' at C5.b; DC check remains undecided (C5.a: on KFB, which has no simulated volts) |
| `aa964` | `CKTO` | `a` | source '+' at CKTO.a; DC check remains undecided (CKTO.a: reaches only ground, through RKTO) |
| `ab763` | `CKTO2` | `b` | source '+' at CKTO2.b; DC check remains undecided (CKTO2.b: reaches only ground, through RKTO2) |
| `ab763` | `CKTO1` | `b` | source '+' at CKTO1.b; DC check remains undecided (CKTO1.b: reaches only ground, through RKTO1) |
| `ab763-super` | `CKTO2` | `a` | source '+' at CKTO2.a; DC check remains undecided (CKTO2.a: reaches only ground, through RKTO2) |
| `ab763-super` | `CKTO1` | `a` | source '+' at CKTO1.a; DC check remains undecided (CKTO1.a: reaches only ground, through RKTO1) |
| `ab763-twin` | `CKTO1` | `b` | source '+' at CKTO1.b; DC check remains undecided (CKTO1.b: reaches only ground, through RKTO1) |
| `ab763-twin` | `CKTO2` | `b` | source '+' at CKTO2.b; DC check remains undecided (CKTO2.b: reaches only ground, through RKTO2) |

## Review and regression checks

The validator rejects a declaration naming an absent lead or a non-electrolytic.
The net selftest reverses a real bias can, removes its declaration to expose
the legacy fallback, and plants a reversal on an unclaimed board. Thirty-two
renderer cases compare the emitted `+` coordinate with the declared terminal
in both styles, with reversed endpoint order and all four off-board edges.
It also proves that an explicit source declaration leaves missing DC coverage
undecided and that clean boards are retained in the exported counts.

Regenerate both layout styles, the social cards, and site assets together.
Visual review must use readable component crops as well as each complete
board; a passing DC check cannot prove that the glyph or label is readable.
