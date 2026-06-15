import asyncio
from owner.owner_agent import OwnerAgent
from utils.config_loader import load_config
from utils.logger import setup_logger

async def main():
    config = {
        "data": {
            "symbols": ["BTC/USDT"],
            "timeframes": ["1m", "3m", "5m", "15m"],
            "forex_symbols": ["XAUUSD=X", "EURUSD=X"],
            "news_source": "https://cryptopanic.com/api/v1/posts/?auth_token=PUBLIC"
        },
        "owner": {"max_population": 1000}
    }
    setup_logger()
    owner = OwnerAgent(config)
    await owner.initialize()
    
    while True:
        await owner.tick()
        await asyncio.sleep(60) # Har 1 minute mein refresh

if __name__ == "__main__":
    asyncio.run(main())