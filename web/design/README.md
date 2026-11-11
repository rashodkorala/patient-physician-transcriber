# Clinic design system

The interface for a clinic or public health organisation: a physician's laptop, a room screen on the wall, a tablet in the patient's hands, and a record view.
It is decided in ADR-012 and lives as tokens in `web/app/globals.css`.
Every module stylesheet uses tokens only.

## What it is for

Two people who do not share a language, one of them often older, unwell, or frightened, and a clinician with little time.
The interface must be read at arm's length on a tablet and at three metres on a 40 inch screen, by people who did not choose it and will not be trained on it.
So: light, large, plain, and calm.
Nothing decorative.
Colour only where it means something.

## Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F4F7F6` | `#0F1A1D` | Page background |
| `--surface` | `#FFFFFF` | `#152328` | Cards, fields, the patient's buttons |
| `--ink` | `#14232B` | `#E9F0EE` | Text |
| `--muted` | `#4F5F6A` | `#A3B3B0` | Secondary text and small labels (AA on paper) |
| `--line` | `#D3DCD9` | `#2A3A40` | Rules and borders |
| `--care` | `#0E6B6E` | `#5FC1C0` | The one accent: primary actions, focus ring, links, the interpreter's own words |
| `--physician` | `#2458A6` | `#8DB4F2` | The physician's speaker colour, cool |
| `--patient` | `#9A5A14` | `#E2A85F` | The patient's speaker colour, warm |
| `--companion` | `#6B4E8C` | `#C3A9E3` | The companion's speaker colour |
| `--ok` | `#1E7B4F` | `#6FCF97` | Verified, matched, confirmed |
| `--wait` | `#8A5800` | `#E8BC5A` | Checking, waiting, pending (darker than ADR-012's `#9C6400`, which fell below AA on its soft tint) |
| `--stop` | `#B42318` | `#F28B82` | Blocked, not spoken, broken record |

Each meaning colour has a `-soft` tint for backgrounds behind text in that colour.
Speakers and states are never told apart by colour alone: a label or a shape always goes with it.

## Type

One family, Atkinson Hyperlegible Next (variable), designed by the Braille Institute for low vision readers.
Noto Sans Gurmukhi, Tamil, and Sinhala for those scripts, loaded in the same three weights.

| Weight | Use |
|---|---|
| 400 | Text, captions, the patient's words |
| 500 | Labels, speaker names, controls |
| 600 | The few things that must be found first: a blocked dose, a broken record, a read-back |

Sentence case everywhere.
No uppercase tracked labels, no serif, no italic (three of the scripts have none).
Line length under 80 characters for running text; captions on the room screen are shorter still.

Sizes: `--text-sm` 14, `--text-md` 16, `--text-lg` 18, `--text-xl` 22, `--text-2xl` 28, `--text-3xl` 36.
The room screen scales captions with the viewport and never below 32 pixels at 1080p.

## Shape and depth

Controls 8 pixels (`--r-control`), cards and the patient's buttons 12 pixels (`--r-card`).
Borders are one pixel `--line`; the patient's signal buttons use two pixels so they read as buttons from across a table.
One shadow, `--shadow-panel`, on the controller's sticky panel only.
Focus is a double ring in `--care` (`--focus`), visible on every control.

## Motion

Only the orb breathes, and only the speaking rings move.
Everything else changes state without animation.
`prefers-reduced-motion` stops all of it.

## Each screen

- **Home** (`/`): the product name, one sentence, and three device cards: clinician, room screen, and patient.
  Each card carries a rule in the colour of the person who holds the device, so the colours mean here what they mean everywhere else.
  A small link leads to the record view.
- **Room screen** (`/screen`): paper background, two columns per turn, original then translation, a thin rule in the speaker's colour down the left of each turn and the speaker's name beside it.
  Captions are `clamp(32px, 2.6vw, 52px)`: 50 pixels at 1920, 33 at 1280, never below 32 on a display.
  The physician's manner label sits beneath the translation in the patient's language, with English beside it; patient and companion captions never carry one.
  A patient's signal shows as a notice in both languages, in the patient's colour, for eight seconds; a screen joining inside that window still sees it.
  The interpreter's own rows (introduction, consent, a signal relayed, the closing check, the summary) carry the care colour.
  The orb is the only moving thing: a `--surface` ball with a `--line` ring, its blobs tinted from the speaker tokens, the care colour while translating, and the paper's greys at rest.
- **Patient device** (`/patient`): the patient's language leads every label, English beneath in `--muted`.
  The five controls are the one bold element on the page: white on paper, 56 pixels tall, full width on a phone.
  Nothing on this screen shows an emotion, a manner of the patient's own words, or anything the physician sees privately.
- **Controller** (`/control`): a working surface for a clinician.
  Controls on the left, the private panel on the right.
  The read-back is the one inverted block.
  The trust view is a quiet list, not a dashboard.
- **Record view** (`/record`): the note with one tag per sentence, tags in `--muted` with the speaker's colour as a small square, AI inference in `--wait`.
  The source panel lists every turn with its speaker's rule, the physician's manner as a small muted label, and each patient signal after the turn it followed.
- **Record badge** (every screen): "Record verified" in `--ok` on its soft tint with a filled check; "Record broken at turn 3" in `--stop` with a cross.
  The word always goes with the colour.

## Legacy aliases

`globals.css` still defines `--bg`, `--text`, `--signal`, `--chip-bg`, `--chip-text`, and `--serif` as aliases of the tokens above.
They exist only so `controller.module.css` and `review.module.css` resolve until those are rewritten; no other stylesheet may use them, and the block goes when the last user does.

## Writing

Plain verbs, sentence case, no filler.
A control says what happens when it is used: "Say that again", not "Repeat".
A notice says what happened and what to do next; it never apologises and never blames.
Every patient-facing string lives in `web/i18n/*.json` and carries `_reviewer: pending` until a native speaker signs it off.
