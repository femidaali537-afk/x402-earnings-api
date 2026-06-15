import asyncio
import uvicorn
from fastapi import FastAPI
from owner.owner_agent import OwnerAgent
from utils.logger import setup_logger

app = FastAPI()
setup_logger()

# Global engine instance
config = {
    "data": {
        "symbols": ["BTC/USDT"],
        "timeframes": ["1m", "3m", "5m", "15m"],
        "forex_symbols": ["XAUUSD=X", "EURUSD=X"],
        "news_source": "https://cryptopanic.com/api/v1/posts/?auth_token=PUBLIC"
    },
    "owner": {"max_population": 50} # 50 agents
}
engine = OwnerAgent(config)

@app.get("/health")
def health(): return {"status": "healthy"}

@app.get("/status")
def get_status():
    return {
        "equity": engine.equity,
        "agents": engine.get_agent_list(), # Agents ki details yahan se jayengi
        "signals": engine.recent_signals
    }

async def trading_loop():
    await engine.initialize()
    while True:
        await engine.tick()
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(trading_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)