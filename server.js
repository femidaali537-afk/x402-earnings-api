const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- CONFIG ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const RPC_URL = "https://mainnet.base.org";

let poolWealthETH = 0.0;
let agentCount = 0;
let logs = [];
let intelligence = { "Web_Scouting": 1.0, "Arbitrage": 1.0, "Data_Mining": 1.0, "Social_Mining": 1.0 };

// --- DASHBOARD UI ---
const html = `
<!DOCTYPE html>
<html>
<head>
    <title>AI OMEGA EMPIRE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #08080a; color: #00ff88; font-family: sans-serif; text-align: center; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; max-width: 1200px; margin: auto; }
        .card { background: #111116; border: 1px solid #00ff8833; padding: 20px; border-radius: 12px; }
        .val { font-size: 2em; color: #fff; margin: 5px 0; }
        .btn { background: #00ff88; color: #000; border: none; padding: 15px 30px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px; }
        .btn:disabled { background: #444; color: #888; cursor: not-allowed; }
        .log-box { background: #000; height: 180px; overflow-y: auto; text-align: left; padding: 10px; font-family: monospace; font-size: 0.8em; color: #00ff88; border: 1px solid #333; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>OMEGA CIVILIZATION</h1>
    <div class="grid">
        <div class="card">
            <h3>TREASURY (ETH)</h3>
            <div class="val" id="eth">0.00000000</div>
            <button id="withdrawBtn" class="btn" onclick="withdraw()">WITHDRAW EARNINGS</button>
            <p id="status" style="font-size:0.7em; color:#888; margin-top:10px;">Ready</p>
        </div>
        <div class="card">
            <h3>ACTIVE POPULATION</h3>
            <div class="val" id="agents">0</div>
            <p>Units working 24/7</p>
        </div>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h3>INTELLIGENCE</h3>
            <div id="intel"></div>
        </div>
        <div class="card">
            <h3>LIVE WORK LOGS</h3>
            <div class="log-box" id="logs"></div>
        </div>
    </div>

    <script>
        async function update() {
            try {
                const res = await fetch('/api/v1/stats');
                const data = await res.json();
                document.getElementById('eth').innerText = parseFloat(data.pool).toFixed(8);
                document.getElementById('agents').innerText = data.agents;
                
                let intelHtml = '';
                for(let key in data.intel) {
                    let pct = Math.min(100, data.intel[key] * 1).toFixed(1);
                    intelHtml += \`<div style="text-align:left; font-size:0.8em;">\${key}: \${pct}%</div><div style="background:#222;height:5px;margin-bottom:5px;"><div style="background:#00ff88;height:100%;width:\${pct}%"></div></div>\`;
                }
                document.getElementById('intel').innerHTML = intelHtml;
                document.getElementById('logs').innerHTML = data.logs.map(l => \`<div>[\${l.t}] \${l.a}: +\${l.r} ETH</div>\`).join('');
            } catch(e) {}
        }

        async function withdraw() {
            const btn = document.getElementById('withdrawBtn');
            const status = document.getElementById('status');
            btn.disabled = true;
            status.innerText = "Processing Transaction...";
            
            try {
                const res = await fetch('/api/v1/withdraw', { method: 'POST' });
                const data = await res.json();
                if(data.success) {
                    alert("Success! Transfer Hash: " + data.hash);
                    status.innerText = "Paid Successfully";
                } else {
                    alert("Error: " + data.error);
                    status.innerText = "Failed";
                }
            } catch(e) {
                alert("Withdrawal Failed. Check if you have gas fees (ETH) in server wallet.");
                status.innerText = "Error";
            }
            btn.disabled = false;
            update();
        }
        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
`;

app.get('/', (req, res) => res.send(html));

app.post('/api/v1/work', (req, res) => {
    const { agent_id, reward, way } = req.body;
    const r = parseFloat(reward) || 0;
    poolWealthETH += r;
    
    if(way && intelligence[way]) intelligence[way] += 0.01;
    
    logs.unshift({ t: new Date().toLocaleTimeString(), a: agent_id, r: r.toFixed(8) });
    if(logs.length > 20) logs.pop();
    
    const idNum = parseInt(agent_id.split('-').pop());
    if(!isNaN(idNum) && idNum > agentCount) agentCount = idNum;

    res.json({ success: true });
});

app.post('/api/v1/withdraw', async (req, res) => {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) return res.status(400).json({ error: "Private Key not set" });

    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);
        
        const tx = {
            to: OWNER_WALLET,
            value: ethers.parseEther(poolWealthETH.toFixed(18))
        };

        const transaction = await wallet.sendTransaction(tx);
        await transaction.wait();
        
        poolWealthETH = 0; // Reset after success
        res.json({ success: true, hash: transaction.hash });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/v1/stats', (req, res) => {
    res.json({
        pool: poolWealthETH.toFixed(8),
        agents: agentCount,
        intel: intelligence,
        logs: logs
    });
});

app.listen(PORT, () => console.log('Empire Ready with Manual Withdraw'));
