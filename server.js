// FINAL SAFE x402 API - Health always free, payment only on specific routes
const express = require('express');
const { paymentMiddleware } = require('@x402/express');
const axios = require('axios');

const app = express();
app.use(express.json());

const WALLET_ADDRESS = '0xD98C02DaaaEc5B62A28d94e67908479236070230';
const FACILITATOR_URL = 'https://facilitator.payai.network';
const NETWORK = 'eip155:8453';
const USDC_ASSET = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const PRICES = {
  basic: '$0.01'
};

// Always working FREE health (no payment middleware here)
app.get('/health', (req, res) => {
  res.json({ 
    status: 'x402-LIVE-ON-RAILWAY',
    message: 'AI agents can pay USDC to this wallet.',
    wallet: WALLET_ADDRESS,
    time: new Date().toISOString()
  });
});

// Create middleware instance
const pay = paymentMiddleware({
  payTo: WALLET_ADDRESS,
  facilitatorUrl: FACILITATOR_URL,
  defaultPrice: PRICES.basic,
  defaultNetwork: NETWORK,
  defaultAsset: USDC_ASSET
});

// Paid routes - middleware applied per route
app.get('/api/crypto/prices', pay, async (req, res) => {
  try {
    const symbols = req.query.symbols || 'bitcoin,ethereum';
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${symbols}&vs_currencies=usd&include_24hr_change=true`;
    const { data } = await axios.get(url, { timeout: 5000 });
    res.json({ data, paid_via: 'x402', price: PRICES.basic });
  } catch (e) {
    res.json({ error: 'price fetch failed', paid_via: 'x402' });
  }
});

app.get('/api/github/trending', pay, async (req, res) => {
  try {
    const { data } = await axios.get('https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=5', { timeout: 8000 });
    res.json({ data: data.items.map(r => ({ name: r.full_name, stars: r.stargazers_count })), paid_via: 'x402', price: PRICES.basic });
  } catch (e) {
    res.json({ error: 'github failed', paid_via: 'x402' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`x402 API running on port ${PORT}`);
  console.log(`Wallet: ${WALLET_ADDRESS}`);
  console.log(`Test free: /health`);
});