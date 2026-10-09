const fs=require('node:fs');
const {chromium}=require('C:/Users/44725/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 let browser;
 try {
  const p=chromium.executablePath();
  console.log(JSON.stringify({defaultBrowser:p,defaultExists:fs.existsSync(p)}));
  browser=await chromium.launch({channel:'msedge',headless:true,chromiumSandbox:true,timeout:12000});
  const context=await browser.newContext({viewport:{width:800,height:600}});
  const page=await context.newPage();await page.goto('about:blank');
  await page.setContent('<p id="probe">APF_ENV_PROBE</p>');
  const text=await page.locator('#probe').textContent();
  if(text!=='APF_ENV_PROBE')throw new Error('fixed DOM probe mismatch');
  console.log(JSON.stringify({channel:'msedge',browserVersion:browser.version(),dom:text,chromiumSandbox:true,passed:true}));
 } finally {if(browser)await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
