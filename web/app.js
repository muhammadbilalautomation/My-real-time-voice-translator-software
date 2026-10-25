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
  const waiting = Math.max(0, Number(state.retry_after) || 0);
  for (const id of ['mic','output','direction','refresh','test-voice','clear','api-key','save-key']) $(id).disabled = occupied || busy;
  $('start').hidden = occupied;
  $('start').disabled = busy || !connected || !state.key_ready || !$('mic').value || !$('output').value || waiting > 0;
  $('test-voice').disabled = occupied || busy || waiting > 0;
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
  $('session-title').textContent = state.testing ? 'آواز کا نمونہ':running ? (state.muted ? 'مائیک خاموش ہے':'گفتگو جاری ہے'):'شروع کرنے کے لیے تیار';
  $('session-status').textContent = state.status;
  if (waiting && !occupied) {
    const time = waiting >= 3600 ? Math.ceil(waiting/3600)+' گھنٹے' : waiting >= 60 ? Math.ceil(waiting/60)+' منٹ' : waiting+' سیکنڈ';
    $('session-title').textContent = 'Google کی حد کے بعد انتظار';
    $('session-status').textContent = 'دوبارہ کوشش سے پہلے تقریباً '+time+' انتظار کریں۔';
  }
  $('provider').textContent = state.key_ready ? 'Gemini · API key محفوظ ہے':'Gemini · API key درکار ہے';
  $('latency').textContent = state.latency || '';
  $('key-status').textContent = state.key_ready ? 'Key محفوظ ہے؛ نئی key پیسٹ کرنے کی ضرورت نہیں۔':'ابھی key محفوظ نہیں ہے۔';
  renderText('original',state.original); renderText('translation',state.translation);
  error(localError || state.error || (!state.key_ready ? 'API key نہیں ملی۔ project کی مقامی .env فائل چیک کریں؛ key چیٹ میں نہ بھیجیں۔':''));
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
      option.dataset.api = device.api;
      $(id).append(option);
    }
    const score = d => (d.name === previous ? 100:0) + (id === 'mic' ? (/realtek/i.test(d.name) ? 20:0) : (d.headphones ? 20:0)) + (d.api === 'Windows WASAPI' ? 5:0);
    const preferred = [...items].sort((a,b) => score(b)-score(a))[0];
    if (preferred) $(id).value = String(preferred.id);
    else {const option = document.createElement('option'); option.value=''; option.textContent='کوئی ڈیوائس نہیں ملی'; $(id).append(option);}
  }
  const headphones = $('output').selectedOptions[0]?.dataset.headphones === 'true';
  $('output-hint').textContent = headphones ? 'ایئربڈز منتخب ہیں۔':'صرف متن — آواز کے لیے ایئربڈز منتخب کریں۔';
  await api('mute',{hear:headphones});
}
function selection() {
  const mic = $('mic').selectedOptions[0], output = $('output').selectedOptions[0];
  return {mic:Number($('mic').value),output:Number($('output').value),target:$('direction').value,hear:$('hear').checked,
    mic_name:mic?.dataset.name,mic_api:mic?.dataset.api,output_name:output?.dataset.name,output_api:output?.dataset.api};
}
async function action(work) {
  if (busy || closed) return;
  localError = '';
  busy = true; clearTimeout(timer);
  for (const id of ['start','stop','mic','output','direction','refresh','test-voice','clear','mute','hear','api-key','save-key']) $(id).disabled = true;
  try {await work(); if (closed) return; current = await api('state'); connected = true; render(current);}
  catch (exception) {localError = exception.message || 'دوبارہ آزمائیں۔'; error(localError);}
  finally {busy = false; $('start').disabled = !connected || !current.key_ready || (current.retry_after || 0) > 0; $('stop').disabled = false;
    for (const id of ['mic','output','direction','refresh','test-voice','clear','api-key','save-key']) $(id).disabled = current.active || current.testing;
    $('mute').disabled = !current.active; $('hear').disabled = current.testing;
    $('test-voice').disabled = current.active || current.testing || (current.retry_after || 0) > 0;
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
  const view = button.dataset.view;
  for (const name of ['translator','guide','settings']) $(name+'-view').hidden = name !== view;
  $('page-name').textContent = {guide:'استعمال کا طریقہ',settings:'ترتیبات',translator:'لائیو ترجمہ'}[view];
  if (view !== 'settings') $('api-key').value = '';
  for (const item of document.querySelectorAll('[data-view]')) {
    item.classList.toggle('selected',item === button);
    if (item === button) item.setAttribute('aria-current','page'); else item.removeAttribute('aria-current');
  }
});
$('key-form').addEventListener('submit', event => {
  event.preventDefault();
  if (busy || closed) return;
  const key = $('api-key').value;
  if (!key.trim()) { $('api-key').focus(); return; }
  action(async () => {
    const feedback = $('key-feedback');
    feedback.hidden = false;
    feedback.classList.remove('failure');
    feedback.textContent = 'محفوظ ہو رہی ہے…';
    try {
      await api('key',{key});
      feedback.textContent = 'Key محفوظ ہوگئی۔';
    } catch (exception) {
      feedback.textContent = exception.message;
      feedback.classList.add('failure');
    } finally {
      $('api-key').value = '';
    }
  });
});
$('exit').addEventListener('click', () => action(async () => {
  await api('shutdown',{}); closed = true; clearTimeout(timer);
  $('session-status').textContent = 'ایپ بند ہو گئی ہے۔ یہ ونڈو بند کر دیں۔';
  $('provider').textContent = 'ایپ بند ہے'; $('session-title').textContent = 'مائیک بند ہے';
  for (const item of document.querySelectorAll('button,input,select')) item.disabled=true;
}));
window.addEventListener('pagehide', () => {fetch('/api/stop',{method:'POST',headers:{'X-App-Token':token,'Content-Type':'application/json'},body:'{}',keepalive:true}).catch(()=>{});});
(async () => {try {await devices();} catch (exception) {error(exception.message);} await poll();})();
