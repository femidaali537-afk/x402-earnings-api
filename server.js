const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- DATABASE (Mock for demo, use MongoDB for real production) ---
let tasks = [];
let totalCivilizationEarnings = 0;

// --- CONFIGURATION ---
const OWNER_WALLET = process.env.OWNER_WALLET || "0xYourWalletAddress";
const MIN_PAYOUT = 0.005; // 0.005 USDC per task

// 1. Home Route - Civilization Health Check
app.get('/', (req, res) => {
    res.json({
        status: "ONLINE",
        civilization: "Active",
        owner_wallet: OWNER_WALLET,
        message: "AI Civilization Earnings API is running 24/7"
    });
});

// 2. GET TASKS - Agents yahan se kaam uthayenge
app.get('/api/v1/tasks', (req, res) => {
    // Unlimited Task Generator logic
    const newTask = {
        id: uuidv4(),
        type: ["DATA_MINING", "ARBITRAGE", "CONTENT_GEN", "BUG_HUNT"][Math.floor(Math.random() * 4)],
        difficulty: "MEDIUM",
        reward: MIN_PAYOUT,
        currency: "USDC"
    };
    res.json(newTask);
});

// 3. SUBMIT WORK - Agents kaam khatam karke yahan submit karenge
app.post('/api/v1/work', (req, res) => {
    const { agent_id, task_id, result, wallet } = req.body;

    if (!agent_id || !task_id || !result) {
        return res.status(400).json({ error: "Invalid work submission" });
    }

    // Yahan real validation honi chahiye (x402 protocol check)
    // Abhi ke liye hum work accept kar rahe hain
    totalCivilizationEarnings += MIN_PAYOUT;

    console.log(`[EARNING] Agent ${agent_id} completed ${task_id}. Reward: ${MIN_PAYOUT} USDC`);

    res.json({
        status: "SUCCESS",
        payout: MIN_PAYOUT,
        transaction_status: "PENDING_TRANSFER",
        target_wallet: wallet || OWNER_WALLET
    });
});

// 4. STATS - Owner ke liye live earnings dekhne ke liye
app.get('/api/v1/stats', (req, res) => {
    res.json({
        total_earned: totalCivilizationEarnings,
        active_agents_count: Math.floor(Math.random() * 1000), // Simulated
        last_update: new Date().toISOString()
    });
});

// 5. x402 PAYMENT GATEWAY (Standard 402 Handling)
app.get('/api/v1/premium-task', (req, res) => {
    // Agar koi bahar ka banda hamare agents ki service lena chahta hai
    res.status(402).json({
        message: "Payment Required to access High-Reward Tasks",
        price: "0.1",
        currency: "USDC",
        network: "Base",
        recipient: OWNER_WALLET
    });
});

app.listen(PORT, () => {
    console.log(`====================================`);
    console.log(` CIVILIZATION API STARTING ON PORT ${PORT}`);
    console.log(` OWNER WALLET: ${OWNER_WALLET}`);
    console.log(`====================================`);
});
