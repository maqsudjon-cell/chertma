---
title: Chertma
emoji: 🔤
colorFrom: yellow
colorTo: gray
sdk: static
app_file: index.html
pinned: false
short_description: Type plain ASCII, get correct Uzbek in three scripts
tags:
- uzbek
- transliteration
- orthography
- keyboard
---

# Chertma

**English** · [Oʻzbekcha](#oʻzbekcha)

Type plain ASCII on an ordinary keyboard and get correct Uzbek back — in the new Latin
alphabet (`ş ç ö ğ`), the old Latin alphabet, or Cyrillic.

```
togri gap, ozbekcha yozish oson  →  töğri gap, özbekça yoziş oson
хозир келаман, рахмат            →  hozir kelaman, rahmat
kelaslar qisela balu             →  kelaslar qisela balu   (dialect is not touched)
```

- **Main site:** [chertma.maqsudjon.com](https://chertma.maqsudjon.com)
- **Lexicon behind it:** [uz-lexicon-skeleton](https://huggingface.co/datasets/HF_USERNAME/uz-lexicon-skeleton) — Uzbek word frequencies with a skeleton index
- **Source code:** [github.com/maqsudjon-cell/chertma](https://github.com/maqsudjon-cell/chertma)

It corrects spelling only: it restores the marks a keyboard lost and never rewrites
dialect, contractions or a word that is already a real word. Words it does not know
stay exactly as typed.

**Privacy.** Everything runs in your browser. The page loads its files and a 0.74 MB
dictionary once; after that it makes no network requests. No cookies, no analytics, no
telemetry of any kind. What you type never leaves the page.

This Space is a static copy of the site: plain HTML, CSS and JavaScript, no build step,
no server.

---

## Oʻzbekcha

Oddiy klaviaturada, apostrofsiz yozing — Chertma toʻgʻri oʻzbekchani yangi lotin alifbosida
(`ş ç ö ğ`), eski lotinda yoki kirillda qaytaradi.

- **Asosiy sayt:** [chertma.maqsudjon.com](https://chertma.maqsudjon.com)
- **Lugʻat:** [uz-lexicon-skeleton](https://huggingface.co/datasets/HF_USERNAME/uz-lexicon-skeleton) — oʻzbek soʻzlari chastotasi va skelet indeksi
- **Manba kodi:** [github.com/maqsudjon-cell/chertma](https://github.com/maqsudjon-cell/chertma)

Chertma faqat imloni toʻgʻrilaydi: klaviatura yoʻqotgan belgilarni tiklaydi. Sheva,
qisqartma va lugʻatda bor soʻzga tegmaydi. Tanimagan soʻzlarini yozilganidek qoldiradi.

**Maxfiylik.** Hammasi brauzeringizda ishlaydi. Sahifa oʻz fayllarini va 0,74 MB lugʻatni
bir marta yuklaydi, keyin tarmoqqa hech qanday soʻrov yubormaydi. Cookie yoʻq, analitika
yoʻq, kuzatuv yoʻq. Yozganingiz sahifadan chiqmaydi.
