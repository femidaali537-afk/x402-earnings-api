// IMPROVED VERSION - Better CoinGecko handling + longer timeout
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const WALLET_ADDRESS = '0xD98C02DaaaEc5B62A28d94e67908479236070230';

app.get('/health', (req, res) => {
  res.json({ 
    status: 'x402-LIVE-ON-RENDER',
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
    
    const { data } = await axios.get(url, { 
      timeout: 12000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; x402-earnings-api/1.0)'
      }
    });
    
    res.json({ 
      data, 
      note: 'Free for now. Will require USDC payment via x402 soon.' 
    });
  } catch (e) {
    console.error('CoinGecko error:', e.message);
    res.json({ 
      error: 'price fetch failed', 
      details: e.message || 'unknown error' 
    });
  }
});

app.get('/api/github/trending', async (req, res) => {
  try {
    const { data } = await axios.get('https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=5', { 
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; x402-earnings-api/1.0)'
      }
    });
    res.json({ 
      data: data.items.map(r => ({ name: r.full_name, stars: r.stargazers_count })), 
      note: 'Free for now. Will require USDC payment via x402 soon.' 
    });
  } catch (e) {
    console.error('GitHub error:', e.message);
    res.json({ error: 'github failed', details: e.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API running on port ${PORT}`);
  console.log(`Wallet: ${WALLET_ADDRESS}`);
  console.log(`Health: /health`);
});