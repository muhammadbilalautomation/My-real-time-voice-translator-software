// Run with: playwright-cli -s=translator run-code --filename=qa/browser-check.js
// Uses the real local UI, with simulated session responses. No mic/API calls.
async page => {
  const assert = (value, message) => {if (!value) throw new Error(message);};
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(() => document.querySelector('#provider').textContent.includes('محفوظ'));
  await page.locator('[data-view="guide"]').click();
  assert(await page.getByText('صرف تین آسان قدم۔').isVisible(),'Guide did not open');
  await page.locator('[data-view="translator"]').click();
  const state = {active:false,testing:false,muted:false,hear:false,key_ready:true,status:'Ready',error:'',original:'',translation:'',latency:''};
  await page.route('**/api/*', async route => {
    const path = new URL(route.request().url()).pathname;
    if(path === '/api/devices') return route.continue();
    let body = {};
    try {body = route.request().postDataJSON() || {};} catch (_) {}
    if(path === '/api/start') {
      if(state.fail_start) return route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:'ایئربڈز غائب ہیں'})});
      assert(Boolean(body.mic_name && body.mic_api && body.output_name && body.output_api),'Device identity missing');
      state.active=true;
      state.original='میرا نام بلال ہے۔';
      state.translation='My name is Bilal. <img src=x onerror=alert(1)>';
    }
    if(path === '/api/stop') state.active=false;
    if(path === '/api/mute') Object.assign(state,body);
    if(path === '/api/clear') state.original=state.translation='';
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(path === '/api/state' ? state : {ok:true})});
  });
  await page.locator('[data-view="settings"]').click();
  await page.locator('#api-key').fill('AQ.test-only-placeholder-do-not-use');
  await page.locator('#save-key').click();
  await page.waitForFunction(() => document.querySelector('#key-feedback').textContent === 'Key محفوظ ہوگئی۔');
  assert(await page.locator('#api-key').inputValue() === '', 'Saved secret not cleared');
  await page.locator('[data-view="translator"]').click();
  await page.locator('#start').click();
  await page.waitForFunction(() => !document.querySelector('#stop').hidden);
  assert(await page.locator('#mic').isDisabled(),'Device changes allowed during a session');
  assert(await page.locator('#translation img').count() === 0,'Transcript HTML was executed');
  assert((await page.locator('#translation').textContent()).includes('<img'),'Transcript changed');
  await page.locator('#mute').click();
  await page.waitForFunction(() => document.querySelector('#mute').getAttribute('aria-pressed') === 'true');
  await page.locator('#hear').check();
  await page.waitForFunction(() => document.querySelector('#hear').checked);
  assert(state.hear === true,'Audio checkbox value was lost');
  await page.locator('#stop').click();
  await page.waitForFunction(() => document.querySelector('#stop').hidden);
  await page.locator('#direction').selectOption('ur');
  assert(await page.locator('#translation').getAttribute('dir') === 'rtl','Urdu direction incorrect');
  await page.locator('#clear').click();
  await page.waitForFunction(() => document.querySelector('#original .empty'));
  state.fail_start = true;
  state.error = 'Old API failure';
  state.status = 'NEW POLL OBSERVED';
  await page.locator('#start').click();
  await page.waitForFunction(() => document.querySelector('#session-status').textContent === 'NEW POLL OBSERVED');
  assert((await page.locator('#error').textContent()).includes('ایئربڈز'),'Old API error hid new device error');
  state.fail_start = false;
  state.error = '';
  state.status = 'Ready';
  await page.locator('#clear').click();
  state.retry_after = 60;
  state.error = 'Google quota';
  await page.waitForFunction(() => document.querySelector('#start').disabled && document.querySelector('#test-voice').disabled);
  assert((await page.locator('#session-title').textContent()).includes('انتظار'),'Quota wait not visible');
  state.retry_after = 0;
  state.error = '';
  await page.waitForFunction(() => !document.querySelector('#start').disabled);
  for(const size of [{width:1366,height:768},{width:390,height:844}]) {
    await page.setViewportSize(size);
    const layout = await page.evaluate(() => ({overflow:document.documentElement.scrollWidth > innerWidth,box:document.querySelector('#start').getBoundingClientRect().toJSON(),height:innerHeight}));
    assert(!layout.overflow,'Horizontal overflow at '+size.width);
    assert(layout.box.top >= 0 && layout.box.bottom <= layout.height,'Start button hidden at '+size.width);
  }
  await page.unroute('**/api/*');
  await page.setViewportSize({width:1366,height:900});
  await page.reload();
  await page.waitForFunction(() => document.querySelector('#provider').textContent.includes('محفوظ'));
  return 'PASS: guide, start/stop, mute, audio toggle, safe transcripts, Urdu direction, clear, desktop/mobile layout. Session calls were simulated; microphone never opened.';
}
