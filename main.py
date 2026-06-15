"""
AI Trading Empire — Main Entry Point
====================================
Owner Agent orchestrates the entire civilization of trading agents.
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Imports shifted to match the new folder structure
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.guardrails import GuardrailSystem
from data.database import Database
from memory.empire_memory import load_empire_memory
from owner.owner_agent import OwnerAgent
from owner.performance_tracker import PerformanceTracker
from owner.capital_allocator import CapitalAllocator
from factory.agent_factory import AgentFactory
from serve.telegram_bot import TelegramBot
from serve.api_server import start_api_server
from serve.dashboard import start_dashboard
from execution.paper_trader import PaperTrader

async def main_async(args):
    """Async main loop."""
    # === Load configuration ===
    config_path = args.config or "config.yaml"
    config = load_config(config_path)
    logger = setup_logger(config["system"]["log_level"])

    # 🧠 Load civilization memory FIRST
    logger.info("🧠 Loading Empire Memory (doctrine, prompts, lessons)...")
    empire_memory = load_empire_memory()

    logger.info("🚀 Starting AI Trading Empire")
    logger.info(f"Mode: {config['system']['mode']}")
    
    # === Initialize core systems ===
    db = Database(config)
    await db.init()
    guardrails = GuardrailSystem(config["guardrails"])
    perf_tracker = PerformanceTracker(db)
    capital_allocator = CapitalAllocator(config["owner"])

    # === Initialize Owner Agent ===
    owner = OwnerAgent(
        config=config,
        db=db,
        guardrails=guardrails,
        perf_tracker=perf_tracker,
        capital_allocator=capital_allocator,
    )
    await owner.initialize()

    # === Initialize Agent Factory ===
    factory = None
    if config["factory"]["enabled"]:
        factory = AgentFactory(config, owner, db)
        await factory.initialize()
        logger.info("✓ Agent Factory initialized (genetic evolution enabled)")

    # === Initialize Paper Trader ===
    paper_trader = PaperTrader(config, owner)
    logger.info("✓ Paper Trader initialized (virtual execution)")

    # === Initialize serving layer ===
    if config["serving"]["telegram"]["enabled"]:
        bot = TelegramBot(config, owner)
        await bot.start()
        logger.info("✓ Telegram bot started")

    if config["serving"]["api"]["enabled"]:
        start_api_server(owner, config)
        logger.info(f"✓ API server running on port {config['serving']['api']['port']}")

    if config["serving"]["dashboard"]["enabled"]:
        start_dashboard(owner, config)
        logger.info(f"✓ Dashboard running on port {config['serving']['dashboard']['port']}")

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()
    def signal_handler(sig, frame):
        logger.warning(f"Received signal {sig}, shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        iteration = 0
        while not shutdown_event.is_set():
            iteration += 1
            await owner.tick()
            await paper_trader.check_exits()
            if factory:
                await factory.tick()

            interval = config["owner"]["review_interval_minutes"] * 60
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            
            if iteration % 10 == 0:
                logger.info(f"💓 Heartbeat: iteration {iteration}, uptime OK")
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received")
    finally:
        logger.info("Shutting down gracefully...")
        await owner.shutdown()
        if factory:
            await factory.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--config", type=str)
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        pass
