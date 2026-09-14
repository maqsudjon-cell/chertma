# Ambiguity fixtures — for human review

**Status: NOT REVIEWED.** Nothing in this table enters `tests/` or `bench/`
until every row is marked.

Each row is one ASCII input whose skeleton matches two or three real words.
Glosses are mine; they are exactly what needs checking. The `books` columns
are canonical-form counts from `uz-books-v2` (filled in by the pipeline at
checkpoint 2) so that a pair where one side is negligible can be dropped on
evidence.

Mark the last column `keep`, `fix: …` or `drop`.

## Already ruled

| # | Input | Candidates | Ruling |
|---|---|---|---|
| R1 | `ser` | `ser` (сер) abundant, rich in · `şer` (шер) lion · `şeʼr` (шеър) poem | keep, three candidates |

## Proposed — needs marking

| # | Input | A | Gloss A | B | Gloss B | C | Gloss C | books A | books B | books C | Mark |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `oq` | `oq` оқ | white | `öq` ўқ | bullet; arrow | | | | | | |
| 2 | `ot` | `ot` от | horse; name; throw! | `öt` ўт | fire; grass; bile; pass! | | | | | | |
| 3 | `oz` | `oz` оз | few, little | `öz` ўз | self, own | | | | | | |
| 4 | `ol` | `ol` ол | take! | `öl` ўл | die! | | | | | | |
| 5 | `oy` | `oy` ой | moon; month | `öy` ўй | thought; carve! | | | | | | |
| 6 | `tor` | `tor` тор | narrow; string (of an instrument) | `tör` тўр | net, mesh; seat of honour | | | | | | |
| 7 | `toq` | `toq` тоқ | odd (number); single | `töq` тўқ | full (not hungry); dark (colour) | | | | | | |
| 8 | `toy` | `toy` той | foal | `töy` тўй | wedding; feast | | | | | | |
| 9 | `boy` | `boy` бой | rich | `böy` бўй | height, stature; scent | | | | | | |
| 10 | `soy` | `soy` сой | stream, brook | `söy` сўй | slaughter! | | | | | | |
| 11 | `chol` | `çol` чол | old man | `çöl` чўл | desert, steppe | | | | | | |
| 12 | `chop` | `çop` чоп | chop!; run!; print (`chop etmoq`) | `çöp` чўп | stick, twig, straw | | | | | | |
| 13 | `chok` | `çok` чок | seam; crack | `çök` чўк | sink!; kneel! | | | | | | |
| 14 | `qol` | `qol` қол | stay!, remain! | `qöl` қўл | hand, arm | | | | | | |
| 15 | `bos` | `bos` бос | press!; step on! | `boş` бош | head; beginning | `böş` бўш | empty; free | | | | |
| 16 | `tos` | `tos` тос | basin; pelvis | `toş` тош | stone | `töş` тўш | breastbone, chest | | | | |
| 17 | `qosh` | `qoş` қош | eyebrow | `qöş` қўш | add!; pair | | | | | | |
| 18 | `shox` | `şox` шох | branch; horn | `şöx` шўх | playful, mischievous | | | | | | |
| 19 | `bog` | `boğ` боғ | garden | `böğ` бўғ | strangle!, choke! | | | | | | |
| 20 | `son` | `son` сон | number; thigh | `şon` шон | glory, fame | | | | | | |
| 21 | `sim` | `sim` сим | wire | `şim` шим | trousers | | | | | | |
| 22 | `is` | `is` ис | smell (of burning); soot | `iş` иш | work; matter | | | | | | |
| 23 | `tus` | `tus` тус | colour, hue; look | `tuş` туш | dream; noon; get down! | | | | | | |
| 24 | `qus` | `qus` қус | vomit! | `quş` қуш | bird | | | | | | |

Not carried over from the brief's list (the ruling rebuilds the fixture from
the 24 pairs): `sok` / `şok` and `och` → `oç` / `öç`. Add them back as rows
if you want them.
