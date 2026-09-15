// Everything the bot says. Uzbek, written in old Latin with ʻ (U+02BB) — the
// script every reader can read today. Examples are produced by the engine at
// run time, never typed here, so they cannot drift from what the bot does.

export const SITE = 'chertma.maqsudjon.com';

export const LABELS = { new: 'Yangi alifbo', old: 'Eski lotin', cyrillic: 'Kirill' };

export const esc = (s) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

export const T = {
  already: 'matn allaqachon toʻgʻri ✓',
  alreadyShort: 'allaqachon toʻgʻri',
  unchanged: 'oʻzgarmadi — tanilmagan soʻzlar yozilganidek qoldi',
  unchangedShort: 'oʻzgarmadi',
  noLetters: 'Oʻgiradigan soʻz topilmadi. Matn yozib yuboring.',
  cut: (n) => `Matn juda uzun: birinchi ${n} belgi oʻgirildi, qolgani kesildi.`,
  partCut: '… (qolgani kesildi)',
  nonText: 'Men faqat matn bilan ishlayman. Soʻz yoki gap yozib yuboring.',
  forwarded: 'Uzatilgan xabarni oʻgirmayman. Matnni nusxalab, oddiy xabar qilib yuboring.',
  unknownCommand: 'Bunday buyruq yoʻq. Matn yuboring yoki /help ni bosing.',
  inlineHintTitle: 'Chertma',
  inlineHintDescription: (u) => `Matn yozing: @${u} togri gap`,
};

const EXAMPLE = 'togri gap, ozbekcha yozish oson';

export function startText(username, convert) {
  return [
    'Chertma oddiy klaviaturada yozilgan oʻzbekcha matnni toʻgʻrilab, uch yozuvda qaytaradi: '
      + 'yangi alifbo (Ş Ç Ö Ğ), eski lotin va kirill.',
    '',
    `<code>${esc(EXAMPLE)}</code>\n→ <code>${esc(convert(EXAMPLE, 'new'))}</code>`,
    '',
    `Menga matn yuboring. Boshqa istalgan chatda <code>@${esc(username)} matn</code> deb yozing va natijani tanlang.`,
    SITE,
  ].join('\n');
}

export function helpText(username) {
  return `Matn yuboring — uch yozuvda qaytaraman. Boshqa chatda: <code>@${esc(username)} matn</code>.\n${SITE}`;
}

export function nimaText(convert) {
  const line = (w) => {
    const out = convert(w, 'new');
    return `<code>${esc(w)}</code> → <code>${esc(out)}</code>${out === w ? ' (oʻzgarmadi)' : ''}`;
  };
  return [
    'Chertma faqat imloni toʻgʻrilaydi: klaviatura yoʻqotgan belgilarni (Ş Ç Ö Ğ, tutuq) tiklaydi. '
      + 'Sheva, qisqartma va uslubingizga esa tegmaydi.',
    '',
    line('kelaslar'),
    line('qisela'),
  ].join('\n');
}

export function inlineHintMessage(username) {
  return `Chertma: matnni yangi alifbo, eski lotin va kirillga oʻgiradi. Istalgan chatda <code>@${esc(username)} matn</code> deb yozing.\n${SITE}`;
}
