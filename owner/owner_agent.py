import asyncio
import random
from utils.logger import logger

class OwnerAgent:
    def __init__(self, config):
        self.config = config
        self.equity = 10000
        self.agents = []
        self.recent_signals = []

    async def initialize(self):
        # Create 50 initial agents
        for i in range(self.config["owner"]["max_population"]):
            self.agents.append({
                "ID": f"Agent_{i:03d}",
                "Strategy": random.choice(["Scalping", "Trend", "RSI-HFT", "News-Arb"]),
                "Winrate": f"{random.uniform(65, 88):.1f}%",
                "Status": "Initializing..."
            })
        logger.info(f"👑 Civilization of {len(self.agents)} Agents ready.")

    def get_agent_list(self):
        # Dashboard ko dikhane ke liye list
        return self.agents

    async def tick(self):
        logger.info("📡 Scanning market confluence...")
        # Update agent status to show they are working
        for a in self.agents:
            a["Status"] = random.choice(["Analyzing BTC", "Checking Gold", "Waiting Confluence", "Voted BUY"])
        
        # Simulated Signal for Dashboard
        self.recent_signals = [{
            "Symbol": "BTC/USDT",
            "Action": "HOLD",
            "Confidence": "72%",
            "Reasoning": "Waiting for 5m EMA cross"
        }]
        logger.info("✅ Tick complete.")