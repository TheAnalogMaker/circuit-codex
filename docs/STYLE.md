# House style for reader-facing prose

This guide covers text a reader sees on the site: source citations, circuit
stories, captions, glossary entries and page copy. It does not cover code
comments, commit messages or internal docs.

## Base standard

We follow the [Google developer documentation style guide](https://developers.google.com/style)
for everything this page does not override. Read it there; it is not copied
here. The parts we lean on most are
[voice and tone](https://developers.google.com/style/tone),
[active voice](https://developers.google.com/style/voice),
[short sentences](https://developers.google.com/style/sentence-structure) and
[units of measurement](https://developers.google.com/style/units-of-measure).

## House rules

- **Write for a guitarist or an amp tech, not an engineer.** Use plain words.
  Say "the power transformer", not "TR1", unless the designator is the point.
- **Use active voice and short sentences.** One idea per sentence.
- **Define a term on first use, or link it to the
  [glossary](https://circuitcodex.com/reference/glossary/).** Where links cannot appear (for example,
  in a `sources[].desc` string), use a term the glossary already defines, or
  say what it means in a few words.
- **Leave out internal process words.** Readers should not see CI, PR,
  corpus, gate, history-tier, null, packet or governor. Say "this page" or
  "this site", not "this entry" or "the corpus".
- **Put a space between a number and its unit:** 0.02 µF, 22 kΩ, 450 V, 25 W.
  A thin space is fine. Use the proper symbols (µ, Ω, −) and a true minus
  sign for negative voltages (−35 V).
- **Use era drawing shorthand only inside quotes.** Shorthand such as
  `.02-600`, `MFD`, `uuF` or `20H CH1` appears only when you quote what a
  drawing prints, inside quotation marks. Otherwise write the value out:
  0.02 µF, 600 V.

## Citation format for Sources

Each entry in a circuit's `sources` list is one citation. Its `desc` reads:

```
Publisher, "Title as printed" (drawing code, date). What this source supplies.
```

- **Publisher** is the maker or site that issued the document: Fender, JMI,
  RCA, Wikipedia, Rob Robinette.
- **Title as printed** is the title block or page title, in quotation marks.
- **Drawing code and date** go in parentheses. Give whichever the source
  prints. Leave a slot out rather than guess it.
- **What this source supplies** says what the page takes from it: every
  component value, the printed voltage chart, the board layout, the production
  dates, a data-sheet operating point.

After that, you may add a short sentence on how the source was read, or a
caveat a reader needs. Keep every caveat that matters, even if it takes more
than one sentence. Examples: the chart is disputed; a value is illegible; this
is a different revision; a figure appears on one page only; the drawing does
not print a voltage chart; the copy is a modern redraw.

Do not write dated process logs ("re-read 2026-08-03", "audit", "verbatim").
Change history belongs in the [corrections log](https://circuitcodex.com/corrections/). The component
values themselves live in the parts list, schematic and operating-point table,
so a citation does not need to repeat them.

Keep the standing notices in their usual form: "Not reproduced here; archived
at EL34World." and, for layout sources, "That drawing is redrawn from the
published facts, never traced."

### Examples

**Before** (5F4):

> Fender 'Super-Amp' Model 5F4 drawing (C-EG): every component value AND the
> printed voltage chart read directly from the published schematic
> (2026-07-18; tone network and phase inverter re-read at lug level
> 2026-08-03) — 12AY7 two-channel front end (68k stoppers, 1M leaks, shared
> 820Ω/25µF cathode, 100k plates), … a 6L6G pair fixed-biased at -40 V through
> 220k leaks, 56k speaker NFB + 5k presence with .1-200 on the driver cathode,
> and a 5U4G rectifier; rails +415/+410/+332/+280, PT 8087, OT 45216, choke
> 14684. Not reproduced here; archived at EL34World

**After:**

> Fender, "Super-Amp" Model 5F4 schematic (drawing code C-EG). Supplies every
> component value, the printed voltage chart and the transformer and choke
> part numbers (power transformer 8087, output transformer 45216, choke
> 14684). Not reproduced here; archived at EL34World.

**Before** (5E3):

> Fender 'Deluxe' Model 5E3 drawing (F-EE): all component values read
> directly from the published schematic/layout (2026-07-18) — incl. the
> cathodyne bias arrangement (1M grid leak to the 1.5k/56k cathode junction)
> and rail droppers 5k + 22k; the wiper-fed volume pair, the tone network on
> the V2A grid, the V2A-plate coupler (value not legible) and the four input
> jacks re-read in the 2026-10-03 source audit. The drawing carries no voltage
> chart. Not reproduced here; archived at EL34World

**After:**

> Fender, "Deluxe" Model 5E3 schematic and layout (drawing code F-EE).
> Supplies every component value except one: the value of the coupling
> capacitor from V2A's plate is not legible. The drawing carries no voltage
> chart. Not reproduced here; archived at EL34World.

The second example keeps its caveat (the illegible coupler) and drops the
audit dates.
