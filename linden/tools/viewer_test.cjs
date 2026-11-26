// Phone-emulated check of the walkthrough viewer: load, screenshot, walk with the joystick,
// look by dragging, and try to walk through a wall.
//   node tools/viewer_test.cjs http://127.0.0.1:8765/ out/viewer_test
const { chromium, devices } = require('playwright');
const fs = require('fs');

(async () => {
  const url = process.argv[2] || 'http://127.0.0.1:8765/';
  const out = process.argv[3] || 'out/viewer_test';
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await browser.newContext({ ...devices['iPhone 13'] });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', (m) => logs.push(m.type() + ': ' + m.text()));
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
  await page.goto(url);
  await page.waitForFunction(() => !document.getElementById('loading'), null, { timeout: 120000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/1_spawn.png` });

  const state = () => page.evaluate(() => ({ x: +window.__linden.P.x.toFixed(2), y: +window.__linden.P.y.toFixed(2), yaw: +window.__linden.P.yaw.toFixed(2), room: document.getElementById('room').textContent }));
  const s0 = await state();

  // drag the joystick forward for 2 s
  const st = await page.locator('#stick').boundingBox();
  const cx = st.x + st.width / 2, cy = st.y + st.height / 2;
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx, cy - 50, { steps: 5 });
  await page.waitForTimeout(2000); await page.mouse.up();
  const s1 = await state();
  await page.screenshot({ path: `${out}/2_walked.png` });

  // drag to look right
  const vw = page.viewportSize();
  await page.mouse.move(vw.width * 0.7, vw.height * 0.4); await page.mouse.down();
  await page.mouse.move(vw.width * 0.3, vw.height * 0.45, { steps: 10 }); await page.mouse.up();
  await page.waitForTimeout(300);
  const s2 = await state();
  await page.screenshot({ path: `${out}/3_looked.png` });

  // wall test: put the player in the living room facing the TV wall and walk into it for 4 s
  await page.evaluate(() => { const P = window.__linden.P; P.x = 6.2; P.y = 10.6; P.yaw = -Math.PI / 2; P.pitch = 0; });
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx, cy - 55, { steps: 5 });
  await page.waitForTimeout(4000); await page.mouse.up();
  const s3 = await state();
  await page.screenshot({ path: `${out}/4_wall.png` });
  console.log(JSON.stringify({ spawn: s0, walked: s1, looked: s2, wall: s3, logs: logs.slice(0, 15) }, null, 1));
  await browser.close();
})();
