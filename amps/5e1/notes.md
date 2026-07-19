# 5E1 — Tweed Champ-style

The mid-1950s tweed Champ: a single 12AX7 giving two gain stages, one 1 MΩ
volume control, a cathode-biased 6V6GT single-ended output, and a 5Y3GT
rectifier — no tone control and no phase inverter, about five watts of the
shortest signal path Fender ever shipped. Produced circa 1955–1957, it is the
direct ancestor of the more familiar 5F1: same tube complement and nearly the
same preamp, but with a choke-filtered power supply the 5F1 later dropped.

## Circuit walkthrough (short form)

Two input jacks (each through its own 68 kΩ stopper, 1 MΩ grid leak) → **V1A**
(12AX7, 100 kΩ plate load, 1.5 kΩ cathode bypassed by 25 µF) → 0.02 µF coupling
→ 1 MΩ volume pot → **V1B** (12AX7, 100 kΩ plate load, 1.5 kΩ cathode, left
unbypassed so the feedback can work into it) → 0.02 µF coupling → **V2** 6V6GT
(cathode-biased, 470 Ω 5 W with 25 µF bypass, 220 kΩ grid leak) → single-ended
output transformer (≈5 kΩ : 8 Ω, typical for a single-ended 6V6; the drawing
doesn't mark it) → speaker.
Negative feedback: 22 kΩ from the speaker jack into V1B's cathode — at DC this
parallels the 1.5 kΩ cathode resistor through the secondary's near-zero DCR.

Power: a center-tapped HT winding feeds the 5Y3GT full-wave rectifier into a
choke-filtered supply. The first 8 µF reservoir sits at **+320 V**; a filter
**choke** drops it to **+305 V**, which supplies the 6V6 plate (through the
output-transformer primary) and its screen; a **22 kΩ** resistor then drops the
rail to **+260 V** for the two 12 AX7 plates. Three 8 µF / 450 V cans do the
filtering.

## The choke, and what changed on the way to the 5F1

The 5E1's supply is the clearest fingerprint separating it from its descendant.
Here a **choke** does the first bit of B+ filtering — reservoir +320 V down to
+305 V — and the output tube runs its plate *and* screen off that single
post-choke node. The 5F1 that followed replaced the choke with a plain 10 kΩ
resistor, split the plate and screen onto separate rails, and shifted the
reservoir up to +340 V. Same amp, quieter-on-paper filtering, one fewer iron
part to buy.

Because the choke's DC resistance isn't printed anywhere on the drawing, the
model estimates it from the chart itself: a +320 → +305 V drop carrying the
roughly 43 mA the printed pin voltages imply works out to about 350 Ω, and the
simulation settles on the same 42 mA self-consistently.

## Verification

The drawing prints a full voltage chart (Fender's usual "read to ground with an
electronic voltmeter, ±20%"), and the simulation matches every node on it: the
6V6 cathode within 0.1 % (+19.0 V vs +19 V), the output rail within 0.1 %
(+305 V), and the preamp rail within 2.4 %. The rails are held to a tighter
±8 % internal verification target (the choke's DC resistance is estimated
rather than printed, so the archive holds itself to a stricter bar there),
while the two 12AX7 plates and cathodes are checked against Fender's printed
±20 % convention. The preamp stages simulate a little lean —
plates near +178 V against the chart's +150 V — because the tube models are
datasheet-typical while Fender measured production tubes of the day; the same
gap shows up on every tweed circuit here. Planned refinements: the output
transformer's primary resistance in the DC deck, and full curve-traced tube
models.
