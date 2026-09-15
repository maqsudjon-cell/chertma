// Web demo. The engine is loaded from ./engine and never touches the network;
// this file supplies the one loader call and nothing else leaves the page.
import { Chertma, tokenize, detectScript } from './engine/index.js';

const $ = (s) => document.querySelector(s);
const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

const T = {
  uz: {
    loading: 'yuklanmoqda…', ready: 'tayyor', offline: 'internetsiz tayyor', failed: 'yuklab bölmadi',
    tagline: 'Oddiy klaviaturada yozing — töğri özbekça oling.',
    sub: 'Yangi alifbodagi Ş Ç Ö Ğ, eski lotin va kirill. Apostrof qidirmang.',
    tabType: 'Yozing', tabConvert: 'Ögiring',
    typeLabel: 'Lotin yoki kirillda, apostrofsiz yozing', placeholder: 'togri gap, ozbekcha yozish oson',
    examples: 'Misollar:', scriptNew: 'Yangi lotin', scriptOld: 'Eski lotin', scriptCyr: 'Kirill',
    copy: 'Nusxa oliş', copied: 'Nusxa olindi', saved: 'ta bosiş tejaldi',
    savedHint: '— har bir tiklangan ş ç ö ğ ʼ telefonda kamida 2 bosiş',
    unknownNote: 'Tanilmagan sözlar yozilganidek qoladi.',
    convertLabel: 'Matnni joylang', convertPlaceholder: 'Oʻzbekiston, Тошкент, shahar…',
    from: 'Qaysi yozuvdan', to: 'Qaysi yozuvga',
    convertNote: 'Bu rejim hech narsani tuzatmaydi — faqat yozuvni almaştiradi.',
    untouchedTitle: 'Nimaga tegmaymiz',
    untouchedBody: 'Chertma imloni tuzatadi, şevani emas. Qisqartma, şeva va uslubingiz yozilganidek qoladi:',
    kelaslar: 'kelasizlar', qisela: 'qilsanglar', balu: 'baliq',
    privacyTitle: 'Maxfiylik',
    privacyBody: 'Matningiz qurilmangizdan çiqmaydi. Sahifa va luğat yuklangaç, tarmoqqa hech qanday sörov yuborilmaydi. Cookie yöq, analitika yöq. Bir marta oçilgaç, internetsiz ham işlaydi.',
    benchBody: 'Yangi alifbo uçun oçiq baholaş töplami. Hozir qölda tekşirilmoqda; tayyor bölgaç eʼlon qilinadi.',
    benchLink: 'Qoralamani körish →', source: 'Manba kodi',
    data: 'Luğat: tahrirchi/uz-books-v2 (MIT), tahrirchi/uz-crawl (Apache-2.0)',
    langButton: 'EN',
  },
  en: {
    loading: 'loading…', ready: 'ready', offline: 'ready offline', failed: 'failed to load',
    tagline: 'Type on an ordinary keyboard. Get correct Uzbek.',
    sub: 'The new Latin letters Ş Ç Ö Ğ, old Latin and Cyrillic. No hunting for apostrophes.',
    tabType: 'Type', tabConvert: 'Convert',
    typeLabel: 'Type in Latin or Cyrillic, no apostrophes needed', placeholder: 'togri gap, ozbekcha yozish oson',
    examples: 'Examples:', scriptNew: 'New Latin', scriptOld: 'Old Latin', scriptCyr: 'Cyrillic',
    copy: 'Copy', copied: 'Copied', saved: 'keypresses saved',
    savedHint: '— each restored ş ç ö ğ ʼ takes at least 2 presses on a phone',
    unknownNote: 'Words it does not know stay exactly as typed.',
    convertLabel: 'Paste text', convertPlaceholder: 'Oʻzbekiston, Тошкент, shahar…',
    from: 'From', to: 'To',
    convertNote: 'This mode corrects nothing — it only changes the script.',
    untouchedTitle: 'What we don’t touch',
    untouchedBody: 'Chertma fixes spelling, not speech. Contractions, dialect and your voice come through as typed:',
    kelaslar: 'for kelasizlar', qisela: 'for qilsanglar', balu: 'for baliq',
    privacyTitle: 'Privacy',
    privacyBody: 'Your text never leaves your device. Once the page and its dictionary have loaded, it makes no network requests. No cookies, no analytics. After the first visit it works offline.',
    benchBody: 'An open evaluation set for the new alphabet. Every item is being reviewed by hand; it will be announced when ready.',
    benchLink: 'See the draft →', source: 'Source code',
    data: 'Lexicon: tahrirchi/uz-books-v2 (MIT), tahrirchi/uz-crawl (Apache-2.0)',
    langButton: 'UZ',
  },
};

// Uzbek by default for everyone (many Uzbek phones run a Russian or English locale); EN is one tap away.
let lang = store.get('chertma.lang', 'uz');
const t = (k) => T[lang][k] ?? T.uz[k];

function applyLang() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-i18n-placeholder]')) el.placeholder = t(el.dataset.i18nPlaceholder);
  $('#lang').textContent = t('langButton');
  setStatus(statusState);
  renderTyping();
}

let statusState = 'loading';
function setStatus(state) {
  statusState = state;
  const el = $('#status');
  el.dataset.state = state;
  el.textContent = t(state);
}

// --- engine ----------------------------------------------------------------------

async function lexiconBytes() {
  if ('DecompressionStream' in window) {
    const res = await fetch('data/lexicon-lite.bin.gz');
    if (!res.ok) throw new Error(res.status);
    return new Response(res.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  }
  const res = await fetch('data/lexicon-lite.bin');
  if (!res.ok) throw new Error(res.status);
  return res.arrayBuffer();
}

const engine = new Chertma({ loader: lexiconBytes, maxSuggestions: 4 });
let ready = false;

function run(text, script) {
  engine.options.script = script;
  const out = engine.autocorrect(text);
  engine.options.script = 'new';
  return out;
}

// --- live typing ---------------------------------------------------------------------

const MARKS = /[şçöğʼŞÇÖĞ]/g;
const SCRIPTS = ['new', 'old', 'cyrillic'];
const LABEL = { new: 'scriptNew', old: 'scriptOld', cyrillic: 'scriptCyr' };
let primary = store.get('chertma.script', 'new');
if (!SCRIPTS.includes(primary)) primary = 'new';

const escape = (s) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

/** Output HTML with changed tokens' letters highlighted. Gaps are copied
 * verbatim by the engine, so input and output align segment by segment. */
function highlight(input, output) {
  const segs = tokenize(input);
  let html = '';
  let p = 0;
  for (let i = 0; i < segs.length; i++) {
    const raw = input.slice(segs[i].start, segs[i].end);
    if (segs[i].kind === 'gap') { html += escape(raw); p += raw.length; continue; }
    const next = segs[i + 1];
    let end = next ? output.indexOf(input.slice(next.start, next.end), p) : output.length;
    if (end < 0) end = output.length;
    const tok = output.slice(p, end);
    p = end;
    html += tok === raw ? escape(tok) : escape(tok).replace(MARKS, (m) => `<mark>${m}</mark>`);
  }
  return html;
}

function renderTyping() {
  if (!ready) return;
  const text = $('#typing').value;
  const order = [primary, ...SCRIPTS.filter((s) => s !== primary)];
  const outs = Object.fromEntries(SCRIPTS.map((s) => [s, run(text, s)]));
  $('#out-primary').innerHTML = highlight(text, outs[order[0]]);
  $('#lab-2').textContent = t(LABEL[order[1]]);
  $('#out-2').innerHTML = highlight(text, outs[order[1]]);
  $('#lab-3').textContent = t(LABEL[order[2]]);
  $('#out-3').innerHTML = highlight(text, outs[order[2]]);
  for (const b of document.querySelectorAll('.scripts button')) b.setAttribute('aria-checked', String(b.dataset.script === primary));
  const inMarks = (text.match(MARKS) || []).length;
  const outMarks = (outs.new.match(MARKS) || []).length;
  $('#saved').textContent = String(2 * Math.max(0, outMarks - inMarks));
  renderSuggestions();
}

function currentWord() {
  const ta = $('#typing');
  const caret = ta.selectionStart ?? ta.value.length;
  const before = ta.value.slice(0, caret);
  const segs = tokenize(before).filter((s) => s.kind === 'token');
  const last = segs[segs.length - 1];
  if (!last || last.end !== before.length) return { buffer: '', start: caret, prev: segs.length ? before.slice(segs[segs.length - 1].start, segs[segs.length - 1].end) : null };
  const prev = segs[segs.length - 2];
  return { buffer: before.slice(last.start, last.end), start: last.start, prev: prev ? before.slice(prev.start, prev.end) : null };
}

function renderSuggestions() {
  const box = $('#suggest');
  box.textContent = '';
  const { buffer, start, prev } = currentWord();
  if (!buffer && !prev) return;
  // Suggestions follow the script being typed: Cyrillic in, Cyrillic out.
  const cyr = buffer && detectScript(buffer.toLowerCase()) === 'cyrillic';
  engine.options.script = cyr ? 'cyrillic' : primary === 'cyrillic' ? 'new' : primary;
  const list = engine.suggest(buffer, prev);
  engine.options.script = 'new';
  for (const s of list) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = s.word;
    b.dataset.source = s.source;
    b.title = s.source;
    b.addEventListener('click', () => {
      const ta = $('#typing');
      const caret = ta.selectionStart ?? ta.value.length;
      ta.value = ta.value.slice(0, start) + s.word + ' ' + ta.value.slice(caret);
      const pos = start + s.word.length + 1;
      ta.setSelectionRange(pos, pos);
      ta.focus();
      renderTyping();
    });
    box.append(b);
  }
}

// --- convert ----------------------------------------------------------------------------

function renderConvert() {
  const text = $('#source').value;
  const from = $('#from').value;
  const to = $('#to').value;
  store.set('chertma.convert', `${from}>${to}`);
  $('#converted').textContent = engine.convert(text, from, to);
}

// --- wiring -------------------------------------------------------------------------------

async function copy(text, button) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.append(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
  button.textContent = t('copied');
  setTimeout(() => { button.textContent = t('copy'); }, 1400);
}

function selectTab(id) {
  const type = id === 'type';
  $('#tab-type').setAttribute('aria-selected', String(type));
  $('#tab-convert').setAttribute('aria-selected', String(!type));
  $('#panel-type').hidden = !type;
  $('#panel-convert').hidden = type;
  store.set('chertma.tab', id);
}

$('#tab-type').addEventListener('click', () => selectTab('type'));
$('#tab-convert').addEventListener('click', () => selectTab('convert'));
$('#lang').addEventListener('click', () => { lang = lang === 'uz' ? 'en' : 'uz'; store.set('chertma.lang', lang); applyLang(); });
$('#typing').addEventListener('input', renderTyping);
$('#typing').addEventListener('keyup', renderSuggestions);
$('#typing').addEventListener('click', renderSuggestions);
for (const b of document.querySelectorAll('[data-example]')) {
  b.addEventListener('click', () => { $('#typing').value = b.dataset.example; renderTyping(); });
}
for (const b of document.querySelectorAll('.scripts button')) {
  b.addEventListener('click', () => { primary = b.dataset.script; store.set('chertma.script', primary); renderTyping(); });
}
$('#copy-primary').addEventListener('click', (e) => copy(run($('#typing').value, primary), e.currentTarget));
$('#copy-converted').addEventListener('click', (e) => copy($('#converted').textContent, e.currentTarget));
$('#source').addEventListener('input', renderConvert);
$('#from').addEventListener('change', renderConvert);
$('#to').addEventListener('change', renderConvert);

const [savedFrom, savedTo] = store.get('chertma.convert', 'old>new').split('>');
$('#from').value = savedFrom;
$('#to').value = savedTo;
selectTab(store.get('chertma.tab', 'type') === 'convert' ? 'convert' : 'type');
applyLang();

try {
  await engine.load('data/lexicon-lite.bin');
  ready = true;
  setStatus('ready');
  for (const li of document.querySelectorAll('#untouched-list li')) {
    li.dataset.ok = String(engine.autocorrect(li.dataset.word) === li.dataset.word);
  }
  renderTyping();
  renderConvert();
} catch (err) {
  setStatus('failed');
  console.error(err);
}

if ('serviceWorker' in navigator) {
  // An updated worker takes over once; reload so the new version is what runs.
  const hadController = Boolean(navigator.serviceWorker.controller);
  let reloaded = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (hadController && !reloaded) { reloaded = true; location.reload(); }
  });
  navigator.serviceWorker.register('sw.js').then(() => navigator.serviceWorker.ready).then(() => {
    if (ready) setStatus('offline');
  }).catch(() => { /* the page still works online */ });
}
