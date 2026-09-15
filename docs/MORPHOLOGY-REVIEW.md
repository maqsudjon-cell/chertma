# Morphology and word-list review — 2026-09-15

**Ruled 2026-09-16: stage 1 on (`morphology: 'read'`), stage 2 off, and the lite word list
stays as it was.** The report below is what that decision was made on; everything in it was
measured on the 10 000 generated forms of `tests/fixtures/invariant-generated.txt` in all three
output scripts. One consequence to note: `shoshima → şoşima` in new-Latin output — on
CLAUDE.md §1's passthrough list, but a spelling conversion, not a rewrite, and byte-identical
in old-Latin output.

## 1. Morphological fallback (SPEC §5.2) — off

| Mode | Forms whose output changes | Of which letters corrected |
|---|---|---|
| first design (no guards) | 902 new-Latin · 93 old · 172 Cyrillic | many wrong: `Island → Ishland`, `кураб → қораб`, `Камазлар → Қамазлар` |
| `'read'` (stage 1: stem + suffix valid as typed) | **809** (all in new-Latin output; 0 in old, 0 in Cyrillic beyond rule transliteration) | 0 — every change is an old-Latin spelling read through a real stem: `mashinangiz → maşinangiz` |
| `true` (stages 1 + 2, guards M2–M7) | **822** = the 809 above + **13** | 13 |

Stage 2, all 13 forms (the judgement column is my reading — please check it):

| Input | new | old | Cyrillic | My reading |
|---|---|---|---|---|
| `aldasang` | `aldaşang` | `aldashang` | `алдашанг` | wrong — aldasang "if you deceive" is correct as typed |
| `baxslashganda` | `baxşlaşganda` | `baxshlashganda` | `бахшлашганда` | wrong — the stem is baxs/bahs, no ş |
| `island` | `işland` | `ishland` | `ишланд` | wrong — English word |
| `josusi` | `jöşusi` | `joʻshusi` | `жўшуси` | wrong — josus "spy" |
| `kobraga` | `köbraga` | `koʻbraga` | `кўбрага` | wrong — kobra |
| `maqtasangiz` | `maqtaşangiz` | `maqtashangiz` | `мақташангиз` | wrong — maqtamoq "praise"; maqtasangiz is correct |
| `maqtasin` | `maqtaşin` | `maqtashin` | `мақташин` | wrong — maqtasin is correct |
| `o'xshasin` | `öxşaşin` | `oʻxshashin` | `ўхшашин` | wrong — should be öxşasin; the suffix -sin got ş |
| `ogʻritib` | `öğritib` | `oʻgʻritib` | `ўғритиб` | wrong — ogʻritmoq "to hurt" is correct as typed; öğritib is a different verb |
| `og‘ritmoq` | `öğritmoq` | `oʻgʻritmoq` | `ўғритмоқ` | wrong — same as above |
| `qotirilishi` | `qötirilişi` | `qoʻtirilishi` | `қўтирилиши` | wrong — qotirmoq "to dry, harden" is correct as typed |
| `toqnashtirib` | `töqnaştirib` | `toʻqnashtirib` | `тўқнаштириб` | right — töqnaştirib "colliding" |
| `yasardim` | `yaşardim` | `yashardim` | `яшардим` | ambiguous — yasardim "I would make" is correct as typed; yaşardim "I would live" needs context |

By that reading, 1 of 13 stem corrections is right. Also: with `morphology: true`,
**`qoyvor → qöyvor`** — one of the brief's must-not-touch forms (and open question Q31). With
`'read'`, `shoshima → şoşima` (the old-Latin spelling of "don't hurry").

Stage 1, full list: `docs/review/morphology-stage1-changes.tsv` (809 rows). Random 40:
`taqchillik` → `taqçillik`, `shakllantirayotgan` → `şakllantirayotgan`, `tushgandir` → `tuşgandir`, `berishmas` → `berişmas`, `uyalishi` → `uyalişi`, `chorlasa` → `çorlasa`, `berishlariga` → `berişlariga`, `ko'rmaganimga` → `körmaganimga`, `uchishiga` → `uçişiga`, `Fransuzchada` → `Fransuzçada`, `o'qishining` → `öqişining`, `yoshligingda` → `yoşligingda`, `jinoyatchilikdan` → `jinoyatçilikdan`, `boshidir` → `boşidir`, `rasmiylashtirishning` → `rasmiylaştirişning`, `oʻtding` → `ötding`, `tuzalishni` → `tuzalişni`, `burishtirib` → `buriştirib`, `Qarashsa` → `Qaraşsa`, `Sizchi` → `Sizçi`, `bo'layapman` → `bölayapman`, `bo‘lmaganmi` → `bölmaganmi`, `chiqilganidan` → `çiqilganidan`, `gʻashingizga` → `ğaşingizga`, `tayinlashga` → `tayinlaşga`, `Erdog'anni` → `Erdoğanni`, `ishonganlar` → `işonganlar`, `urishlar` → `urişlar`, `politsiyachidan` → `politsiyaçidan`, `o‘qimasdan` → `öqimasdan`, `tekshirishadi` → `tekşirişadi`, `uchoq` → `uçoq`, `chaqaloqli` → `çaqaloqli`, `o’ylayapman` → `öylayapman`, `bo'lishimga` → `bölişimga`, `og'rig'idan` → `oğriğidan`, `kechishing` → `keçişing`, `chogʻlaydilar` → `çoğlaydilar`, `ketishlarida` → `ketişlarida`, `ramkachalar` → `ramkaçalar`

What `'read'` would fix: `ishlating → işlating`, `mashinangiz → maşinangiz`. What only
`true` fixes: bare `islating → işlating`.

## 2. Lite chosen by crawl coverage — parked as `data/lexicon-lite-coverage.bin`

| | lite by frequency (shipped word list) | lite by crawl coverage |
|---|---|---|
| Held-out coverage, news | 89.69 % | 92.76 % |
| Held-out coverage, telegram | 87.63 % | 89.46 % |
| Ranked golden sentences | 98/150 = 65.3 % | 109/150 = 72.7 % |
| Strict golden cases failing | 0 | 6 (G055–G057, G235, G275: `Shirinning` no longer fixed — the name dropped out; G174 `куйидан`, G209 `Хозир` — Russian-layout misspellings frequent in the crawl got in) |
| Invariant forms changed (morphology off) | 0 | **181**: 156 because the form is now a word (`ro'yxatlariga → röyxatlariga`), **25 with letters substituted** |

The 25 substitutions (new-Latin output):

| Input | Output |
|---|---|
| `мину` | `mino` |
| `гулларига` | `gollariga` |
| `osyapti` | `oşyapti` |
| `sell` | `şell` |
| `yasamagan` | `yaşamagan` |
| `Тоқаевга` | `Töqayevga` |
| `кузак` | `kozak` |
| `захарланди` | `zaharlandi` |
| `Sadullayeva` | `Saʼdullayeva` |
| `хунармандларга` | `hunarmandlarga` |
| `хокимларни` | `hokimlarni` |
| `Улссон` | `Olsson` |
| `Erdog'anni` | `Erdöğanni` |
| `Хожиматов` | `Hojimatov` |
| `гунохларга` | `gunohlarga` |
| `Камчибек` | `Qamçibek` |
| `ислохотларига` | `islohotlariga` |
| `хохласак` | `xohlasak` |
| `Хаус` | `Xaos` |
| `хохламади` | `xohlamadi` |
| `ванихоят` | `vanihoyat` |
| `бахсдан` | `bahsdan` |
| `мўжизалари` | `möʼjizalari` |
| `такидлашмоқда` | `taʼkidlaşmoqda` |
| `сархисоби` | `sarhisobi` |

Some are right (`хокимларни → hokimlarni`, `бахсдан → bahsdan`, `ислохотларига → islohotlariga`),
some wrong (`гулларига → gollariga`, `мину → mino`, `кузак → kozak`, `Хаус → Xaos`, `sell → şell`).
Full list with the 156 conversions: `docs/review/coverage-lite-invariant-changes.tsv`.

It gained 14 812 words over the frequency lite — mostly news vocabulary and names (`asensio`,
`zaporojye`, `çempionlikni`, `işlating`) — and lost textbook words and Russian-layout misspellings
(`tenglama`, `perpendikulyar`, `buladi`, `tugri`, `suz`, `uquv`), and also `işla`.
