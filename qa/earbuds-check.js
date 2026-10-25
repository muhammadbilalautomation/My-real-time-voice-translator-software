// UI-only test: simulated Windows endpoints, no Bluetooth settings/mic/API calls.
async page => {
  const assert = (ok, why) => {if (!ok) throw new Error(why);};
  let available = true, refreshes = 0, starts = 0;
  const state = {active:false,testing:false,muted:false,hear:false,key_ready:true,status:'Ready',error:'',original:'',translation:'',latency:'',retry_after:0};
  await page.route('**/api/*',async route => {
    const path = new URL(route.request().url()).pathname;
    let body={}; try {body=route.request().postDataJSON() || {};} catch (_) {}
    if(path === '/api/start') {starts++; throw new Error('Earbuds selection must never start the mic');}
    if(path === '/api/refresh') refreshes++;
    if(path === '/api/mute') Object.assign(state,body);
    const devices = {inputs:[{id:9,name:'Microphone (Realtek)',api:'Windows WASAPI'}],outputs:[
      {id:8,name:'Speakers (Realtek)',api:'Windows WASAPI',headphones:false},
      ...(available ? [{id:4,name:'Headphones (AirPads pro)',api:'MME',headphones:true},{id:12,name:'Headphones (AirPads pro)',api:'Windows WASAPI',headphones:true}]:[])]};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(path === '/api/state' ? state : path === '/api/devices' ? devices : {ok:true})});
  });
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(()=>document.querySelector('#provider').textContent.includes('محفوظ'));
  assert(refreshes === 0,'Earbuds mode ran automatically');
  await page.locator('[data-view=settings]').click();
  await page.locator('#connect-earbuds').click({timeout:3000});
  await page.waitForFunction(()=>document.querySelector('#earbuds-status').textContent.includes('منتخب'));
  assert(await page.locator('#output').inputValue() === '12','WASAPI AirPods not selected');
  assert(await page.locator('#mic').inputValue() === '9','Microphone was changed');
  assert(state.hear && refreshes === 1 && starts === 0,'Selection did not enable audio safely');
  state.active=true;
  await page.waitForFunction(()=>document.querySelector('#connect-earbuds').disabled && document.querySelector('#live-badge').classList.contains('on'));
  state.active=false;
  await page.waitForFunction(()=>!document.querySelector('#connect-earbuds').disabled);
  available=false;
  await page.locator('#connect-earbuds').click();
  await page.waitForFunction(()=>document.querySelector('#earbuds-status').classList.contains('failure'));
  assert(!state.hear && starts === 0,'Missing earbuds enabled speakers or opened the mic');
  available=true;
  await page.locator('#connect-earbuds').click();
  await page.waitForFunction(()=>document.querySelector('#earbuds-status').textContent.includes('منتخب') && !document.querySelector('#earbuds-status').classList.contains('failure'));
  assert(await page.locator('#output').inputValue() === '12','Reconnect failed');
  await page.unroute('**/api/*');
  await page.reload();
  return 'PASS: optional Earbuds selection, fresh list, WASAPI preference, audio enabled, mic preserved, active-session guard, missing-device warning and reconnect; no mic/API/Bluetooth actions.';
}
