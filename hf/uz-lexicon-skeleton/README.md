---
license: cc-by-4.0
language:
- uz
pretty_name: Uzbek frequency lexicon with skeleton index
size_categories:
- 10M<n<100M
tags:
- uzbek
- lexicon
- word-frequency
- n-grams
- orthography
- transliteration
- alphabet-reform
configs:
- config_name: unigrams
  data_files: unigrams.tsv
  sep: "\t"
  default: true
- config_name: bigrams
  data_files: bigrams.tsv
  sep: "\t"
---

# Uzbek frequency lexicon with skeleton index

**English** · [Oʻzbekcha](#oʻzbekcha)

> **Derived from [`tahrirchi/uz-books-v2`](https://huggingface.co/datasets/tahrirchi/uz-books-v2) (MIT)
> and [`tahrirchi/uz-crawl`](https://huggingface.co/datasets/tahrirchi/uz-crawl) (Apache-2.0).**
> **1.75 billion word tokens counted: 1.43 B from books, 296 M from news, 25.5 M from Telegram channels.**
> Licence: CC BY 4.0 — credit this dataset **and** both sources.

4,892,125 Uzbek word forms with their frequencies, 23,160,605 word pairs, and a
**skeleton index** that groups the words a keyboard makes indistinguishable. Every word is
written in the **new Latin alphabet** (2026: `ş ç ö ğ`, tutuq `ʼ`), lowercase, Unicode NFC.

## Files

| File | Bytes | Rows | Columns |
|---|---|---|---|
| `unigrams.tsv` | 122,955,106 | 4,892,125 | `word`, `count`, `skeleton` — sorted by count, descending |
| `bigrams.tsv` | 463,187,708 | 23,160,605 | `w1`, `w2`, `count` — pairs seen **6 or more** times, sorted by count |
| `skeleton-index.tsv` | 109,603,683 | 4,711,419 | `skeleton`, then every word with that skeleton, most frequent first |

All files are UTF-8, tab-separated, with a header row and `\n` line endings. Rows of
`skeleton-index.tsv` have a variable number of columns (1 to 11 words), so read it line
by line rather than as a fixed table:

```python
index = {}
with open("skeleton-index.tsv", encoding="utf-8") as f:
    next(f)
    for line in f:
        skeleton, *words = line.rstrip("\n").split("\t")
        index[skeleton] = words
```

`unigrams` and `bigrams` load with `datasets.load_dataset("Maqsudjonpolatov/uz-lexicon-skeleton", "unigrams")`.

**Bigram cutoff.** At a cutoff of 3 the file would be 990,561,851 bytes; at 4, 721,519,271;
at 5, 563,061,817. The smallest cutoff that keeps it under about 500 MB is **count ≥ 6**.

## The skeleton, and why the index is useful

Uzbek is written with marks that keyboards lose: `ş ç ö ğ`, the old `oʻ gʻ sh ch`, the tutuq
`ʼ`, or the Cyrillic `ш ч ў ғ`. The **skeleton** of a word is what is left when every
distinction a keyboard could have destroyed is folded away:

| Class | Stands for |
|---|---|
| `S` | `ş` `sh` `s` `w` |
| `C` | `ç` `ch` `c` |
| `O` | `ö` `oʻ` `o` |
| `G` | `ğ` `gʻ` `gh` `g` |
| (dropped) | every apostrophe: `ʼ` `ʻ` `'` `’` |

Every other letter stands for itself. Cyrillic input is transliterated before folding, so
`тўғри`, `toʻgʻri`, `togri` and `töğri` all have the skeleton `tOGri`.

The index answers the question a keyboard, a spell checker or a transliteration model
has to answer: *the user typed something with this skeleton — which real words could
they have meant, and which is most likely?*

**Worked example — `sosib`.** Someone types `sosib` on a phone. Its skeleton is `SOSib`,
and the index row is:

```
SOSib	şoşib	söşib	sösib	şöşib
```

with counts 34,212 · 6 · 2 · 2 in `unigrams.tsv`. The answer is `şoşib` ("hurrying").
`sosib` itself is **not** in the lexicon: it occurs 16 times in the books, under 1 % as
often as `şoşib`, so it was treated as a misspelling and its count merged into `şoşib`.

**A real ambiguity.** `Oz` → `öz` (4,256,258) · `oz` (293,779) · `öʼz` (43). Both `öz`
("self") and `oz` ("few") are words; only context decides.

This project builds on the index: the [Chertma](https://github.com/maqsudjon-cell/chertma)
engine ([chertma.maqsudjon.com](https://chertma.maqsudjon.com)) corrects a typed word only
to a word in its skeleton row, and returns it unchanged when the row is empty.

## How it was built

1. All three sources were tokenized and every token normalized to canonical new Latin
   (old Latin: `sh → ş`, `oʻ → ö`, `gʻ → ğ`, other apostrophes → `ʼ`; Cyrillic by
   transliteration rules; NFC). The rules are in the Chertma `docs/SPEC.md`.
2. A document was dropped when more than 5 % of its tokens of two or more characters fell
   outside the Uzbek alphabet (Russian, English): 495 books, 17,135 news articles and
   15,090 Telegram posts.
3. Words and adjacent word pairs within a sentence were counted.
4. **Admission** — a form is a word in this lexicon if:
   - it was seen at least twice (hapax legomena dropped);
   - it has no mark (`ş ç ö ğ ʼ`) and the **books** contain it at least twice — news and
     Telegram alone cannot make an unmarked form a word, because they are full of
     `togri`, `ozbek`;
   - it is a copy of a marked word with some marks removed and appears in the books less
     than 1 % as often as that word → **merged into that word** (17,382 forms, e.g.
     `sosib → şoşib`);
   - forms of fewer than two letters are dropped, except `u o e a`.
5. `count` is books + news + Telegram, after merging. Bigrams were remapped the same way
   and kept when both words are in the lexicon.

## Known limitations

- **OCR noise from books.** The books were scanned; misrecognized forms are present,
  mostly with low counts. Of 4,892,125 words, 2,464,574 occur fewer than 5 times. Filter by
  `count` for your use: 379,885 words occur 100 times or more.
- **Stray apostrophes.** A misplaced apostrophe makes a marked form (`vʼa`, `bilaʼn`,
  `töʼğri`), and marked forms are admitted from any source. There are 84,547 words with `ʼ`;
  62,982 of them occur fewer than 10 times. They crowd the index: 161,414 skeletons have
  two or more words, but only 42,204 have two or more words seen at least 10 times, and
  6,974 at least 100 times.
- **Russian-layout spellings are present.** Some source texts were typed on a Russian
  keyboard, which has no `ў қ ғ ҳ`. So `tugri` (for `töğri`) is in the lexicon with
  count 57,367 (57,301 of them from books), and `bulgan`, `kanday`, `xalkaro`, `uzbekiston`
  are too. The admission rule only merges forms with *marks* removed, not `u/ö`, `k/q`, `x/h`.
- **Coverage is an upper bound.** Measured on the counting data itself, the 50,000 most
  frequent words cover 85.7 % of book tokens, 91.0 % of news and 87.9 % of Telegram; the
  400,000 most frequent cover 95.2 %, 97.8 % and 97.1 %. There is no held-out set, so
  real coverage on new text is lower.
- **Orthography of Cyrillic `ъ`.** Cyrillic was transliterated with `ъ` dropped before
  `е ё ю я`, while the Latin books write `meʼyor`, `obʼekt`; both spellings can appear.
- **Register.** Mostly books and news. The Telegram part is curated channel posts, not
  private chat, so slang and dialect are thin.
- **Surface forms only.** No lemmas, no morphology; every inflected form is its own row.

## Licence and attribution

This dataset is released under **CC BY 4.0**. It is a derived work — word and word-pair
counts, not running text — of:

- **UzBooks V2**, `tahrirchi/uz-books-v2` (revision `aac9c105`), by Mukhammadsaid Mamasaidov and
  Abror Shopulatov, licensed **MIT** — https://huggingface.co/datasets/tahrirchi/uz-books-v2
- **UzCrawl**, `tahrirchi/uz-crawl` (revision `8fff2d17`), by Mukhammadsaid Mamasaidov and
  Abror Shopulatov, licensed **Apache-2.0** — https://huggingface.co/datasets/tahrirchi/uz-crawl

When you use this dataset, credit it and both sources; their licence terms continue to
apply to the material derived from them.

## Citation

```bibtex
@misc{polatov2026uzlexiconskeleton,
  author = {Polatov, Maqsudjon},
  title  = {Uzbek frequency lexicon with skeleton index},
  year   = {2026},
  url    = {https://huggingface.co/datasets/Maqsudjonpolatov/uz-lexicon-skeleton},
  note   = {Derived from tahrirchi/uz-books-v2 (MIT) and tahrirchi/uz-crawl (Apache-2.0)}
}

@online{Mamasaidov2024UzBooksV2,
    author    = {Mukhammadsaid Mamasaidov and Abror Shopulatov},
    title     = {UzBooks V2 dataset},
    year      = {2026},
    url       = {https://huggingface.co/datasets/tahrirchi/uz-books-v2}
}

@online{Mamasaidov2023UzCrawl,
    author    = {Mukhammadsaid Mamasaidov and Abror Shopulatov},
    title     = {UzCrawl dataset},
    year      = {2023},
    url       = {https://huggingface.co/datasets/tahrirchi/uz-crawl},
    note      = {Accessed: 2026-09-14},
    urldate   = {2026-09-14}
}
```

---

## Oʻzbekcha

> **Manba: [`tahrirchi/uz-books-v2`](https://huggingface.co/datasets/tahrirchi/uz-books-v2) (MIT) va
> [`tahrirchi/uz-crawl`](https://huggingface.co/datasets/tahrirchi/uz-crawl) (Apache-2.0).**
> **1,75 milliard soʻz sanaldi: 1,43 mlrd kitoblardan, 296 mln yangiliklardan, 25,5 mln Telegram kanallaridan.**
> Litsenziya: CC BY 4.0 — ushbu toʻplam **va** ikkala manba koʻrsatilishi shart.

4 892 125 ta oʻzbek soʻz shakli va ularning chastotasi, 23 160 605 ta soʻz juftligi hamda
klaviatura farqlay olmaydigan soʻzlarni guruhlaydigan **skelet indeksi**. Barcha soʻzlar
**yangi lotin alifbosida** (2026: `ş ç ö ğ`, tutuq `ʼ`), kichik harfda, Unicode NFC shaklida.

### Fayllar

| Fayl | Bayt | Qator | Ustunlar |
|---|---|---|---|
| `unigrams.tsv` | 122 955 106 | 4 892 125 | `word`, `count`, `skeleton` |
| `bigrams.tsv` | 463 187 708 | 23 160 605 | `w1`, `w2`, `count` — kamida **6 marta** uchragan juftliklar |
| `skeleton-index.tsv` | 109 603 683 | 4 711 419 | `skeleton`, keyin shu skeletdagi barcha soʻzlar, eng koʻp uchraydigani birinchi |

Bigramlar chegarasi: 3 boʻlganda fayl 990 561 851 bayt, 4 da 721 519 271, 5 da 563 061 817
boʻlardi; 500 MB atrofida qoladigan eng kichik chegara — **count ≥ 6**.

### Skelet nima va indeks nega kerak

Oʻzbek yozuvida klaviatura yoʻqotadigan belgilar bor: `ş ç ö ğ`, eski `oʻ gʻ sh ch`, tutuq
`ʼ`, kirilldagi `ш ч ў ғ`. Soʻzning **skeleti** — klaviatura yoʻqotishi mumkin boʻlgan barcha
farqlar olib tashlangandagi shakli: `S` = `ş sh s w`, `C` = `ç ch c`, `O` = `ö oʻ o`,
`G` = `ğ gʻ gh g`, apostroflar tashlab yuboriladi. Shuning uchun `тўғри`, `toʻgʻri`, `togri`
va `töğri` soʻzlarining skeleti bir xil: `tOGri`.

Indeks klaviatura, imlo tekshiruvchi yoki transliteratsiya modeli javob berishi kerak
boʻlgan savolga javob beradi: *foydalanuvchi shu skeletli narsa yozdi — u qaysi haqiqiy
soʻzni nazarda tutgan boʻlishi mumkin va qaysi biri ehtimolroq?*

**Misol — `sosib`.** Telefonda `sosib` deb yozildi. Skeleti `SOSib`, indeks qatori:
`şoşib` (34 212) · `söşib` (6) · `sösib` (2) · `şöşib` (2). Javob — `şoşib`. `sosib` ning
oʻzi lugʻatda **yoʻq**: kitoblarda 16 marta uchraydi, bu `şoşib` ning 1 % idan kam, shuning
uchun imlo xatosi deb hisoblanib, soni `şoşib` ga qoʻshilgan.

**Haqiqiy ikki maʼnolilik:** `Oz` → `öz` (4 256 258) · `oz` (293 779) · `öʼz` (43). `oʻz` ham,
`oz` ham soʻz — qaysi biri toʻgʻriligini faqat gap hal qiladi.

### Qanday tuzilgan

Uch manbadagi har bir soʻz yangi lotin shakliga keltirildi va sanaldi. 5 % dan ortigʻi
oʻzbek alifbosidan tashqarida boʻlgan hujjatlar chiqarib tashlandi. Lugʻatga kirish
qoidalari: kamida 2 marta uchragan; belgisiz (`ş ç ö ğ ʼ` siz) shakl faqat kitoblarda kamida
2 marta boʻlsa kiradi; belgili soʻzning belgisi tushib qolgan nusxasi kitoblarda uning 1 %
idan kam uchrasa, oʻsha soʻzga qoʻshiladi (17 382 ta shakl).

### Cheklovlar

- **Kitoblardagi OCR xatolari** bor, asosan kam sonli. 379 885 ta soʻz kamida 100 marta uchraydi —
  ishingizga qarab `count` boʻyicha saralang.
- **Notoʻgʻri qoʻyilgan apostroflar** (`vʼa`, `bilaʼn`, `töʼğri`) belgili shakl hosil qiladi va
  lugʻatga kirib qolgan: `ʼ` li 84 547 ta soʻzdan 62 982 tasi 10 martadan kam uchraydi.
- **Rus klaviaturasida yozilgan shakllar bor:** `tugri` (`töğri` oʻrniga) 57 367 marta (shundan
  57 301 tasi kitoblarda), shuningdek `bulgan`, `kanday`, `xalkaro`, `uzbekiston`.
- **Qamrov yuqori chegara:** u sanash uchun ishlatilgan matnning oʻzida oʻlchangan; eng koʻp
  uchraydigan 50 000 soʻz kitob matnining 85,7 % ini, yangiliklarning 91,0 % ini, Telegramning
  87,9 % ini qamraydi. Yangi matnda bu raqam pastroq boʻladi.
- Kirilldagi `ъ` unlidan keyin qanday yozilishi hali aniq emas (`meʼyor` / `meyor`).
- Asosan kitob va yangiliklar; Telegram qismi — kanal postlari, shaxsiy yozishmalar emas.
- Faqat soʻz shakllari: lemma va morfologiya yoʻq.

### Litsenziya

**CC BY 4.0.** Bu toʻplam `tahrirchi/uz-books-v2` (MIT; Mukhammadsaid Mamasaidov, Abror Shopulatov)
va `tahrirchi/uz-crawl` (Apache-2.0; Mukhammadsaid Mamasaidov, Abror Shopulatov) asosida olingan
soʻz va soʻz juftligi sanoqlaridir. Foydalanganda ushbu toʻplamni va ikkala manbani
koʻrsating; manbalarning litsenziya shartlari ulardan olingan maʼlumotlarga ham tegishli.
