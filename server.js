// CACHED VERSION - Avoids CoinGecko 429 rate limit
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const WALLET_ADDRESS = '0xD98C02DaaaEc5B62A28d94e67908479236070230';

// Simple in-memory cache
let priceCache = {
  data: null,
  lastUpdated: 0
};

const CACHE_DURATION_MS = 60 * 1000; // 60 seconds

app.get('/health', (req, res) => {
  res.json({ 
    status: 'x402-LIVE-ON-RENDER',
    message: 'API is running. Will add real USDC payments next.',
    wallet: WALLET_ADDRESS,
    time: new Date().toISOString()
  });
});

app.get('/api/crypto/prices', async (req, res) => {
  const now = Date.now();
  
  // Return cached data if still fresh
  if (priceCache.data && (now - priceCache.lastUpdated) < CACHE_DURATION_MS) {
    return res.json({ 
      data: priceCache.data, 
      note: 'Free for now (cached). Will require USDC payment via x402 soon.',
      cached: true
    });
  }

  try {
    const symbols = req.query.symbols || 'bitcoin,ethereum';
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${symbols}&vs_currencies=usd&include_24hr_change=true`;
    
    const { data } = await axios.get(url, { 
      timeout: 15000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; x402-earnings-api/1.0)'
      }
    });
    
    // Save to cache
    priceCache = {
      data: data,
      lastUpdated: now
    };
    
    res.json({ 
      data, 
      note: 'Free for now. Will require USDC payment via x402 soon.' 
    });
  } catch (e) {
    console.error('CoinGecko error:', e.message);
    // If we have old cache, return it even if expired
    if (priceCache.data) {
      return res.json({ 
        data: priceCache.data, 
        note: 'Using cached data due to rate limit. Will require USDC payment via x402 soon.',
        cached: true,
        stale: true
      });
    }
    res.json({ 
      error: 'price fetch failed', 
      details: e.message 
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
    res.json({ error: 'github failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`API running on port ${PORT}`);
  console.log(`Wallet: ${WALLET_ADDRESS}`);
});