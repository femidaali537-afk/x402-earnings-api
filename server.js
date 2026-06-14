// ULTRA SAFE x402 API - NO PAYMENT MIDDLEWARE YET (to get it live on Railway)
// We will add real x402 payment in next step after it's stable
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const WALLET_ADDRESS = '0xD98C02DaaaEc5B62A28d94e67908479236070230';

app.get('/health', (req, res) => {
  res.json({ 
    status: 'x402-LIVE-ON-RAILWAY',
    message: 'API is running. Will add real USDC payments next.',
    wallet: WALLET_ADDRESS,
    time: new Date().toISOString(),
    endpoints: ['/api/crypto/prices', '/api/github/trending']
  });
});

app.get('/api/crypto/prices', async (req, res) => {
  try {
    const symbols = req.query.symbols || 'bitcoin,ethereum';
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${symbols}&vs_currencies=usd&include_24hr_change=true`;
    const { data } = await axios.get(url, { timeout: 5000 });
    res.json({ data, note: 'Free for now. Payment coming soon.' });
  } catch (e) {
    res.json({ error: 'price fetch failed' });
  }
});

app.get('/api/github/trending', async (req, res) => {
  try {
    const { data } = await axios.get('https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=5', { timeout: 8000 });
    res.json({ 
      data: data.items.map(r => ({ 
        name: r.full_name, 
        stars: r.stargazers_count 
      })), 
      note: 'Free for now. Payment coming soon.' 
    });
  } catch (e) {
    res.json({ error: 'github failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`x402 API running on port ${PORT}`);
  console.log(`Wallet: ${WALLET_ADDRESS}`);
  console.log(`Health: /health (always free)`);
});