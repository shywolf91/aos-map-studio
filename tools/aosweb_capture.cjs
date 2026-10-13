// Render a .vxl in Dylan's aos_web client (offline "Open VXL map" mode) and screenshot viewpoints.
// Usage: node aosweb_capture.cjs <map.vxl> <outdir> <views.json> [baseUrl]
// views.json: [{"name":..., "x":..., "y":..., "z":... (AoS eye coords, z down), "tx":..,"ty":..,"tz":.. (look-at)}]
// Needs Playwright: `npm i playwright` (then `npx playwright install chromium`), or set PLAYWRIGHT_MODULE / CHROME_PATH.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'); const path = require('node:path');
(async () => {
  const [vxl, outdir, viewsFile, base] = process.argv.slice(2);
  const views = JSON.parse(fs.readFileSync(viewsFile, 'utf8'));
  fs.mkdirSync(outdir, {recursive: true});
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || undefined,
    headless: true, args: ['--enable-unsafe-swiftshader', '--use-gl=swiftshader', '--ignore-gpu-blocklist']});
  const page = await browser.newPage({viewport: {width: 1100, height: 640}});
  page.setDefaultTimeout(600000);
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(base || 'http://127.0.0.1:8090');
  await page.waitForFunction(() => !!Opal.gvars.observer.token && Opal.gvars.observer.token !== Opal.nil);
  if (process.env.DISTANCE) await page.selectOption('#distance', process.env.DISTANCE);   // software WebGL: keep frames cheap
  await page.locator('#map-file').setInputFiles(vxl);
  await page.locator('#loading').waitFor({state: 'hidden', timeout: 900000});
  // hide overlays (minimap, captions) so shots show only the world
  await page.addStyleTag({content: '#minimap-panel,.view-top,.view-bottom,#crosshair,#scope,#shot-panel{display:none!important}'});
  await page.waitForTimeout(2500);
  const results = [];
  for (const v of views) {
    await page.evaluate(v => {
      const r = Opal.gvars.observer.renderer; const cam = r.camera.$to_n();
      // AoS (x, y, z-down) -> three (x, 63 - z, y)
      const ex = v.x, ey = 63 - v.z, ez = v.y, tx = v.tx, ty = 63 - v.tz, tz = v.ty;
      const dx = tx - ex, dy = ty - ey, dz = tz - ez, h = Math.hypot(dx, dz);
      cam.position.set(ex, ey, ez);
      r.yaw = Math.atan2(-dx, -dz); r.pitch = Math.atan2(dy, h);
    }, v);
    await page.waitForTimeout(1500);
    const file = path.join(outdir, `${v.name}.png`);
    const box = await page.locator('#world').boundingBox();
    await page.screenshot({path: file, clip: box, timeout: 180000});
    results.push(file);
  }
  console.log(JSON.stringify({shots: results, pageErrors: errors}));
  await page.locator('#disconnect').click().catch(() => {});   // release the bridge session
  await page.waitForTimeout(500);
  await browser.close();
})().catch(e => { console.error(e); process.exitCode = 1; });
