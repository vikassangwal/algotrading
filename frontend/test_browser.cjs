const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('ERROR:', msg.text());
    } else {
      console.log('LOG:', msg.text());
    }
  });
  
  page.on('pageerror', error => {
    console.log('PAGE ERROR:', error.message);
  });
  
  page.on('requestfailed', request => {
    console.log('REQUEST FAILED:', request.url(), request.failure().errorText);
  });

  console.log("Navigating...");
  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2', timeout: 10000 });
  } catch (e) {
    console.log("Navigation error:", e.message);
  }
  
  console.log("Waiting a bit...");
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  await browser.close();
})();
