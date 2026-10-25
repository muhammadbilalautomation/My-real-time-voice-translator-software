// Run with: playwright-cli -s=translator run-code --filename=qa/browser-check.js
// Uses the real local UI, with simulated session responses. No mic/API calls.
async page => {
  const assert = (value, message) => {if (!value) throw new Error(message);};
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(() => document.querySelector('#provider').textContent.includes('محفوظ'));
  await page.getByRole('button',{name:'استعمال کا طریقہ Guide'}).click();
  assert(await page.getByText('صرف تین آسان قدم۔').isVisible(),'Guide did not open');
  await page.getByRole('button',{name:'لائیو ترجمہ Live'}).click();
  const state = {active:false,testing:false,muted:false,hear:false,key_ready:true,status:'Ready',error:'',original:'',translation:'',latency:''};
  await page.route('**/api/*', async route => {
    const path = new URL(route.request().url()).pathname;
    if(path === '/api/devices') return route.continue();
    let body = {};
    try {body = route.request().postDataJSON() || {};} catch (_) {}
    if(path === '/api/start') {
      state.active=true;
      state.original='میرا نام بلال ہے۔';
      state.translation='My name is Bilal. <img src=x onerror=alert(1)>';
    }
    if(path === '/api/stop') state.active=false;
    if(path === '/api/mute') Object.assign(state,body);
    if(path === '/api/clear') state.original=state.translation='';
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(path === '/api/state' ? state : {ok:true})});
  });
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
