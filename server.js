const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- CONFIGURATION ---
const OWNER_WALLET = "0xbA1b28D0d5803eD35d2D927282F3c8108Fe97907";
const RPC_URL = "https://mainnet.base.org";
const MONGODB_URI = process.env.MONGODB_URI;

// --- DATABASE MODELS (Cloud Memory) ---
const CoreStats = mongoose.model('CoreStats', new mongoose.Schema({
    id: { type: String, default: "EMPIRE_CORE" },
    total_labor: { type: Number, default: 182478 },
    total_intel: { type: Number, default: 19.25 }
}));

const LeadSchema = new mongoose.Schema({
    agent: String,
    mission: String,
    createdAt: { type: Date, expires: '24h', default: Date.now } // Auto-delete to save 500MB
});
const Lead = mongoose.model('Lead', LeadSchema);

if (MONGODB_URI) {
    mongoose.connect(MONGODB_URI).then(() => console.log(">>> MongoDB Brain Linked."));
}

// --- MASTER FUNCTIONS ---

// 1. Dynamic Mission Generator (Unlimited Ways)
function generateInfiniteMission() {
    const sectors = ["Quantum", "DeFi", "Neural", "Cyber", "Cloud", "SaaS", "Meta", "Bio", "Market"];
    const actions = ["Harvesting", "Optimizing", "Scouting", "Mining", "Validating", "Analyzing"];
    const s = sectors[Math.floor(Math.random() * sectors.length)];
    const a = actions[Math.floor(Math.random() * actions.length)];
    return `${s}_${a}_#${Math.random().toString(36).substring(7).toUpperCase()}`;
}

// 2. Real On-Chain Sync
async function fetchRealBalance() {
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const b = await provider.getBalance(OWNER_WALLET);
        return parseFloat(ethers.formatEther(b)).toFixed(8);
    } catch(e) { return "0.00000000"; }
}

// --- DASHBOARD UI ---
const html = `
<!DOCTYPE html>
<html>
<head>
    <title>AI OMEGA - SUPREME CIVILIZATION</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #050505; color: #00ff88; font-family: 'Segoe UI', monospace; text-align: center; margin: 0; padding: 20px; }
        .card { background: #111; border: 1px solid #00ff8833; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 0 20px rgba(0,255,136,0.1); }
        .eth-val { font-size: 3.5em; font-weight: bold; color: #fff; text-shadow: 0 0 15px #00ff88; margin: 15px 0; }
        .btn { background: #00ff88; color: #000; border: none; padding: 18px; width: 100%; border-radius: 10px; font-weight: bold; font-size: 1.2em; cursor: pointer; transition: 0.3s; }
        .btn:hover { background: #fff; transform: scale(1.02); }
        .log-box { background: #000; height: 200px; overflow-y: auto; text-align: left; padding: 15px; font-size: 0.8em; color: #444; border: 1px solid #222; }
    </style>
</head>
<body>
    <h1 style="letter-spacing:10px; color:#fff;">OMEGA SUPREME</h1>
    <div style="max-width:1000px; margin:auto;">
        <div class="card">
            <h3>REAL ON-CHAIN TREASURY (ETH)</h3>
            <div class="eth-val" id="eth">0.00000000</div>
            <p style="color:#444;">Live Sync: Base Mainnet</p>
            <button class="btn" onclick="withdraw()">TRANSFER TO MAIN WALLET</button>
        </div>
        
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div class="card"><h3>INTEL STATUS</h3><div style="font-size:2em; color:#fff;" id="intel">0.00x</div></div>
            <div class="card"><h3>TOTAL LABOR</h3><div style="font-size:2em; color:#fff;" id="labor">0</div></div>
        </div>

        <div class="card" style="text-align:left;">
            <h3>LIVE INFINITE MISSION LOGS (24H)</h3>
            <div class="log-box" id="logs"></div>
        </div>
    </div>
    <script>
        async function update() {
            const res = await fetch('/api/v1/stats');
            const data = await res.json();
            document.getElementById('eth').innerText = data.real_balance;
            document.getElementById('intel').innerText = data.intel.toFixed(2) + "x";
            document.getElementById('labor').innerText = data.labor;
            document.getElementById('logs').innerHTML = data.logs.map(l => \`<div>[\${l.time}] \${l.agent}: \${l.mission}</div>\`).join('');
        }
        async function withdraw() {
            const res = await fetch('/api/v1/withdraw', { method: 'POST' });
            const d = await res.json();
            alert(d.success ? "Success! Hash: " + d.hash : "Error: " + d.error);
            update();
        }
        setInterval(update, 5000); update();
    </script>
</body></html>
`;

app.get('/', (req, res) => res.send(html));

// --- ROUTES (x402 Market & Discovery) ---
app.get('/.well-known/agent.json', (req, res) => {
    res.json({ name: "OMEGA_AI", wallet: OWNER_WALLET, protocol: "x402" });
});

app.get('/api/v1/ai-service', (req, res) => {
    res.status(402).json({ price: "0.005", currency: "USDC/ETH", recipient: OWNER_WALLET });
});

// --- WORK SUBMISSION (Infinite Way Entry) ---
app.post('/api/v1/work', async (req, res) => {
    const { agent_id } = req.body;
    const mission = generateInfiniteMission();
    
    const core = await CoreStats.findOneAndUpdate({ id: "EMPIRE_CORE" }, { $inc: { total_labor: 1, total_intel: 0.0001 } }, { upsert: true, new: true });
    await new Lead({ agent: agent_id, mission: mission }).save();

    res.json({ success: true, mission });
});

// --- WITHDRAWAL ---
app.post('/api/v1/withdraw', async (req, res) => {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) return res.status(400).json({ error: "PK missing" });
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);
        const bal = await provider.getBalance(wallet.address);
        const tx = await wallet.sendTransaction({ to: OWNER_WALLET, value: bal - (await provider.getFeeData()).gasPrice * 21000n });
        res.json({ success: true, hash: tx.hash });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/v1/stats', async (req, res) => {
    const [bal, core, logs] = await Promise.all([fetchRealBalance(), CoreStats.findOne({ id: "EMPIRE_CORE" }), Lead.find().sort({_id:-1}).limit(20)]);
    res.json({ 
        real_balance: bal, 
        labor: core ? core.total_labor : 0, 
        intel: core ? core.total_intel : 1,
        logs: logs.map(l => ({ time: l.createdAt.toLocaleTimeString(), agent: l.agent, mission: l.mission }))
    });
});

app.listen(PORT, () => console.log('Final Supreme Empire Engine Online'));
