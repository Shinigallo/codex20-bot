const { chromium } = require('playwright');

(async () => {
  console.log('Avvio browser (modalità estesa)...');
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  try {
    const page = await context.newPage();
    console.log('Accesso a Puter.com...');
    
    // Aumentiamo il timeout a 2 minuti per hardware ARM/lento
    await page.goto('https://puter.com', { waitUntil: 'load', timeout: 120000 });

    console.log('Attesa inizializzazione sistema (60s)...');
    // Aspettiamo che il desktop virtuale carichi i suoi script
    await page.waitForTimeout(60000);

    console.log('Tentativo di recupero token tramite comando interno...');
    const token = await page.evaluate(async () => {
        try {
            // Proviamo vari modi per ottenere il token dall'SDK interno di Puter
            if (window.puter && window.puter.auth && typeof window.puter.auth.getAuthToken === 'function') {
                return await window.puter.auth.getAuthToken();
            }
            // Alternativa: cerchiamo nel localStorage
            return localStorage.getItem('puter-auth-token') || localStorage.getItem('token');
        } catch (e) {
            return 'Errore: ' + e.message;
        }
    });

    if (token && !token.startsWith('Errore')) {
        console.log('TOKEN_TROVATO:', token);
    } else {
        console.log('Token non trovato direttamente. Dati presenti nel localStorage:');
        const storage = await page.evaluate(() => JSON.stringify(localStorage));
        console.log(storage);
    }
  } catch (error) {
    console.error('Errore critico:', error.message);
  } finally {
    await browser.close();
  }
})();
