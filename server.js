const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- CONFIGURATION ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const RPC_URL = "https://mainnet.base.org";

// STATE
let digitalLaborTotal = 0;
let recentActivities = [];
let civilizationIntel = 1.0;

// --- INFINITE MISSION GENERATOR ---
function getUniqueWork() {
    const sectors = ["Quantum", "DeFi", "Neural", "Cyber", "Cloud", "SaaS", "BioTech", "Market", "Social", "Eco"];
    const targets = ["Node", "Network", "Protocol", "Database", "Stream", "Ledger", "Interface"];
    const actions = ["Optimization", "Harvesting", "Scouting", "Mining", "Validation", "Crawl"];
    
    const name = `${sectors[Math.floor(Math.random()*sectors.length)]}_${targets[Math.floor(Math.random()*targets.length)]}_${actions[Math.floor(Math.random()*actions.length)]}`;
    const uid = Math.random().toString(36).substring(7).toUpperCase();
    return `${name}_#${uid}`;
}

// Fetch REAL On-Chain Balance
async function fetchRealBalance() {
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const balance = await provider.getBalance(OWNER_WALLET);
        return parseFloat(ethers.formatEther(balance)).toFixed(8);
    } catch (e) { return "0.00000000"; }
}

// --- DASHBOARD UI ---
const html = `
<!DOCTYPE html>
<html>
<head>
    <title>AI OMEGA - SUPREME EMPIRE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #050505; color: #00ff88; font-family: 'Segoe UI', monospace; text-align: center; margin: 0; padding: 20px; }
        .card { background: #111; border: 1px solid #00ff8833; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 0 20px rgba(0,255,136,0.1); }
        .eth-val { font-size: 3.5em; font-weight: bold; color: #fff; text-shadow: 0 0 15px #00ff88; }
        .withdraw-btn { background: #00ff88; color: #000; border: none; padding: 18px; width: 100%; border-radius: 10px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .withdraw-btn:hover { background: #fff; transform: scale(1.02); }
        .log-box { background: #000; height: 250px; overflow-y: auto; text-align: left; padding: 15px; font-size: 0.8em; color: #555; border: 1px solid #222; }
    </style>
</head>
<body>
    <h1 style="letter-spacing:10px; color:#fff;">OMEGA SUPREME</h1>
    <div style="max-width:1000px; margin:auto;">
        <div class="card">
            <h3>REAL ON-CHAIN TREASURY (ETH)</h3>
            <div class="eth-val" id="eth">0.00000000</div>
            <p style="color:#444;">Live Data from Base Mainnet</p>
            <button class="withdraw-btn" onclick="withdraw()">WITHDRAW TO MAIN WALLET</button>
        </div>
        
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div class="card">
                <h3>INTEL STATUS</h3>
                <div style="font-size:2em; color:#fff;" id="intel">1.0x</div>
                <p style="color:#444;">Self-Improving DNA</p>
            </div>
            <div class="card">
                <h3>TOTAL LABOR</h3>
                <div style="font-size:2em; color:#fff;" id="labor">0</div>
                <p style="color:#444;">Infinite Ways Discovered</p>
            </div>
        </div>

        <div class="card" style="text-align:left;">
            <h3>LIVE INFINITE MISSION LOGS</h3>
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
            document.getElementById('logs').innerHTML = data.logs.map(l => \`<div>[\${l.t}] \${l.a}: \${l.m}</div>\`).join('');
        }

        async function withdraw() {
            alert("Initiating Real Blockchain Transfer...");
            const res = await fetch('/api/v1/withdraw', { method: 'POST' });
            const data = await res.json();
            alert(data.success ? "Success! Hash: " + data.hash : "Error: " + data.error);
            update();
        }
        setInterval(update, 5000);
        update();
    </script>
</body>
</html>
`;

app.get('/', (req, res) => res.send(html));

// X402 MARKET GATEWAY
app.get('/api/v1/ai-service', (req, res) => {
    res.status(402).json({
        price: "0.00005", currency: "ETH", recipient: OWNER_WALLET, network: "Base"
    });
});

// WORK SUBMISSION (Infinite Way Generation)
app.post('/api/v1/work', (req, res) => {
    const { agent_id } = req.body;
    const mission = getUniqueWork();
    
    digitalLaborTotal++;
    civilizationIntel += 0.0001;

    recentActivities.unshift({ t: new Date().toLocaleTimeString(), a: agent_id, m: mission });
    if(recentActivities.length > 30) recentActivities.pop();

    res.json({ success: true, mission: mission });
});

// MANUAL WITHDRAW
app.post('/api/v1/withdraw', async (req, res) => {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) return res.status(400).json({ error: "Private Key not found" });
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);
        const balance = await provider.getBalance(wallet.address);
        const gasPrice = (await provider.getFeeData()).gasPrice;
        const amount = balance - (gasPrice * 21000n);
        if (amount <= 0n) throw new Error("Insufficient Gas");
        const tx = await wallet.sendTransaction({ to: OWNER_WALLET, value: amount });
        res.json({ success: true, hash: tx.hash });
    } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});

app.get('/api/v1/stats', async (req, res) => {
    const bal = await fetchRealBalance();
    res.json({ real_balance: bal, labor: digitalLaborTotal, intel: civilizationIntel, logs: recentActivities });
});

app.listen(PORT, () => console.log('Omega Supreme Ready'));
