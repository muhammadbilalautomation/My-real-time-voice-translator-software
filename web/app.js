'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="app-token"]').content;
let current = {active:false, testing:false, muted:false, hear:true};
let busy = false, timer = null, closed = false, connected = false;
let localError = '';
const placeholders = {original:$('original').firstElementChild.cloneNode(true), translation:$('translation').firstElementChild.cloneNode(true)};

async function api(path, body) {
  const response = await fetch('/api/' + path, {
    method:body === undefined ? 'GET':'POST',
    headers:{'X-App-Token':token, 'Content-Type':'application/json'},
    ...(body === undefined ? {} : {body:JSON.stringify(body)}),
    signal:AbortSignal.timeout(6000)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'درخواست مکمل نہیں ہو سکی۔');
  return result;
}
function error(message) { $('error').textContent = message; $('error').hidden = !message; }
function renderText(id, text) {
  const node = $(id);
  if (text) {
    if (node.textContent !== text) {node.textContent = text; node.scrollTop = node.scrollHeight;}
  } else if (!node.querySelector('.empty')) node.replaceChildren(placeholders[id].cloneNode(true));
}
function render(state) {
  current = state;
  const running = state.active, occupied = running || state.testing;
  for (const id of ['mic','output','direction','refresh','test-voice','clear']) $(id).disabled = occupied || busy;
  $('start').hidden = occupied;
  $('start').disabled = busy || !connected || !state.key_ready || !$('mic').value || !$('output').value;
  $('stop').hidden = !occupied;
  $('stop').disabled = busy;
  $('mute').disabled = !running || busy;
  $('mute').setAttribute('aria-pressed', String(state.muted));
  $('mute').textContent = state.muted ? 'مائیک کھولیں':'مائیک خاموش';
  $('hear').checked = state.hear;
  $('hear').disabled = busy || state.testing;
  $('session-light').classList.toggle('on', running && !state.muted);
  $('live-badge').classList.toggle('on', running);
  $('live-badge').textContent = running ? (state.muted ? 'مائیک خاموش ہے':'لائیو ترجمہ جاری ہے'):'مائیک بند ہے';
  $('session-title').textContent = state.testing ? 'آواز کا نمونہ':running ? (state.muted ? 'مائیک خاموش ہے':'آپ کی بات سنی جا رہی ہے'):'بات شروع کرنے کے لیے تیار';
  $('session-status').textContent = state.status;
  $('provider').textContent = state.key_ready ? 'Gemini · API key محفوظ ہے':'Gemini · API key درکار ہے';
  $('latency').textContent = state.latency || 'آواز اور ترجمہ مستقل محفوظ نہیں ہوتے';
  renderText('original',state.original); renderText('translation',state.translation);
  error(state.error || localError || (!state.key_ready ? 'API key نہیں ملی۔ project کی مقامی .env فائل چیک کریں؛ key چیٹ میں نہ بھیجیں۔':''));
}
async function poll() {
  if (closed) return;
  try {const state = await api('state'); connected = true; render(state);}
  catch (_) {
    connected = false; $('start').disabled = true;
    $('session-status').textContent = 'مقامی ایپ سے رابطہ ٹوٹ گیا۔';
    error('رابطہ نہیں ہو رہا۔ Desktop سے Voice Translator دوبارہ کھولیں۔ مائیک زیادہ سے زیادہ 30 سیکنڈ میں خود بند ہوگا۔');
  }
  timer = setTimeout(poll, 900);
}
async function devices() {
  const lists = await api('devices');
  for (const [id,key] of [['mic','inputs'],['output','outputs']]) {
    const previous = $(id).selectedOptions[0]?.dataset.name;
    const items = lists[key];
    $(id).replaceChildren();
    for (const device of items) {
      const option = document.createElement('option');
      option.value = String(device.id); option.textContent = `${device.name} · ${device.api}`;
      option.dataset.name = device.name; option.dataset.headphones = String(device.headphones);
      $(id).append(option);
    }
    const score = d => (d.name === previous ? 100:0) + (id === 'mic' ? (/realtek/i.test(d.name) ? 20:0) : (d.headphones ? 20:0)) + (d.api === 'Windows WASAPI' ? 5:0);
    const preferred = [...items].sort((a,b) => score(b)-score(a))[0];
    if (preferred) $(id).value = String(preferred.id);
    else {const option = document.createElement('option'); option.value=''; option.textContent='کوئی ڈیوائس نہیں ملی'; $(id).append(option);}
  }
  const headphones = $('output').selectedOptions[0]?.dataset.headphones === 'true';
  $('output-hint').textContent = headphones ? 'ایئربڈز منتخب ہیں؛ ترجمے کی آواز یہیں آئے گی۔':'اسپیکر منتخب ہیں؛ فی الحال صرف متن۔ ایئربڈز کنیکٹ کرکے فہرست تازہ کریں۔';
  await api('mute',{hear:headphones});
}
function selection() {return {mic:Number($('mic').value), output:Number($('output').value), target:$('direction').value, hear:$('hear').checked};}
async function action(work) {
  if (busy || closed) return;
  localError = '';
  busy = true; clearTimeout(timer);
  for (const id of ['start','stop','mic','output','direction','refresh','test-voice','clear','mute','hear']) $(id).disabled = true;
  try {await work(); if (closed) return; current = await api('state'); connected = true; render(current);}
  catch (exception) {localError = exception.message || 'دوبارہ آزمائیں۔'; error(localError);}
  finally {busy = false; $('start').disabled = !connected || !current.key_ready; $('stop').disabled = false;
    for (const id of ['mic','output','direction','refresh','test-voice','clear']) $(id).disabled = current.active || current.testing;
    $('mute').disabled = !current.active; $('hear').disabled = current.testing;
    if (!closed) timer = setTimeout(poll, 2200);
    else for (const item of document.querySelectorAll('button,input,select')) item.disabled=true;
  }
}
$('start').addEventListener('click', () => action(() => api('start',selection())));
$('stop').addEventListener('click', () => action(() => api('stop',{})));
$('mute').addEventListener('click', () => action(() => api('mute',{muted:!current.muted})));
$('hear').addEventListener('change', () => {const hear = $('hear').checked; action(() => api('mute',{hear}));});
$('output').addEventListener('change', () => action(async () => {
  const headphones = $('output').selectedOptions[0]?.dataset.headphones === 'true';
  await api('mute',{hear:headphones});
}));
$('test-voice').addEventListener('click', () => action(() => api('test',selection())));
$('clear').addEventListener('click', () => action(() => api('clear',{})));
$('refresh').addEventListener('click', () => action(async () => {await api('refresh',{}); await devices();}));
$('direction').addEventListener('change', () => {
  const english = $('direction').value === 'en';
  $('source-label').textContent = english ? 'URDU':'ENGLISH';
  $('target-label').textContent = english ? 'ENGLISH':'URDU';
  $('original').dir = english ? 'rtl':'ltr'; $('translation').dir = english ? 'ltr':'rtl';
  $('original').classList.toggle('source-text',english);
});
for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => {
  const guide = button.dataset.view === 'guide';
  $('guide-view').hidden = !guide; $('translator-view').hidden = guide;
  $('page-name').textContent = guide ? 'استعمال کا طریقہ':'لائیو ترجمہ';
  for (const item of document.querySelectorAll('[data-view]')) {
    item.classList.toggle('selected',item === button);
    if (item === button) item.setAttribute('aria-current','page'); else item.removeAttribute('aria-current');
  }
});
$('exit').addEventListener('click', () => action(async () => {
  await api('shutdown',{}); closed = true; clearTimeout(timer);
  $('session-status').textContent = 'ایپ بند ہو گئی ہے۔ یہ ونڈو بند کر دیں۔';
  $('provider').textContent = 'ایپ بند ہے'; $('session-title').textContent = 'مائیک بند ہے';
  for (const item of document.querySelectorAll('button,input,select')) item.disabled=true;
}));
window.addEventListener('pagehide', () => {fetch('/api/stop',{method:'POST',headers:{'X-App-Token':token,'Content-Type':'application/json'},body:'{}',keepalive:true}).catch(()=>{});});
(async () => {try {await devices();} catch (exception) {error(exception.message);} await poll();})();
