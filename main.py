"""
AI Trading Empire — Main Entry Point
====================================
Owner Agent orchestrates the entire civilization of trading agents.

Usage:
    python main.py                    # Start paper trading (default)
    python main.py --mode live        # Live trading (real money)
    python main.py --backtest         # Run backtests only
    python main.py --config <path>    # Use custom config

Author: AI Trading Empire Architect
License: MIT
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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
    config_path = args.config or "configs/config.yaml"
    config = load_config(config_path)
    logger = setup_logger(config["system"]["log_level"])
    
    # 🧠 Load civilization memory FIRST
    logger.info("🧠 Loading Empire Memory (doctrine, prompts, lessons)...")
    empire_memory = load_empire_memory()
    
    logger.info("🚀 Starting AI Trading Empire")
    logger.info(f"Mode: {config['system']['mode']}")
    logger.info(f"Vision: {empire_memory.get('VISION.core_statement', 'N/A')[:100]}")
    logger.info(f"Timeframes: {', '.join(empire_memory.get_timeframes())}")
    logger.info(f"Sacred guardrails: {len(empire_memory.get_guardrails())} hard rules active")
    
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
    
    # === Initialize Agent Factory (Evolutionary Engine) ===
    factory = None
    if config["factory"]["enabled"]:
        factory = AgentFactory(config, owner, db)
        await factory.initialize()
        logger.success("✓ Agent Factory initialized (genetic evolution enabled)")
    
    # === Initialize Paper Trader ===
    paper_trader = PaperTrader(config, owner)
    logger.success("✓ Paper Trader initialized (virtual execution)")
    
    # === Initialize serving layer ===
    if config["serving"]["telegram"]["enabled"]:
        bot = TelegramBot(config, owner)
        await bot.start()
        logger.success("✓ Telegram bot started")
    
    if config["serving"]["api"]["enabled"]:
        start_api_server(owner, config)
        logger.success(f"✓ API server running on port {config['serving']['api']['port']}")
    
    if config["serving"]["dashboard"]["enabled"]:
        start_dashboard(owner, config)
        logger.success(f"✓ Dashboard running on port {config['serving']['dashboard']['port']}")
    
    # === Main orchestration loop ===
    logger.info("=" * 70)
    logger.success("✅ System online. Entering main loop.")
    logger.info(f"📊 Civilization: {len(owner.agents)} specialist agents")
    logger.info(f"🛡️ Guardrails: Active (max DD: {config['guardrails']['max_drawdown_pct']*100:.0f}%)")
    logger.info(f"🧬 Evolution: {'Enabled' if factory else 'Disabled'}")
    logger.info("=" * 70)
    
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
            
            # Owner agent's main loop tick
            await owner.tick()
            
            # Paper trader: check open positions for SL/TP
            await paper_trader.check_exits()
            
            # Factory evolution tick (if enabled)
            if factory:
                await factory.tick()
            
            # Sleep for review interval
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
        logger.info("=" * 70)
        logger.info("Shutting down gracefully...")
        await owner.shutdown()
        if factory:
            await factory.shutdown()
        await db.close()
        logger.success("👋 Goodbye — Empire shutdown complete")
        logger.info("=" * 70)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Trading Empire — Self-improving multi-agent civilization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Paper trading (default)
  python main.py --mode live              # Live trading (be careful!)
  python main.py --backtest               # Run backtests then exit
  python main.py --config my_config.yaml  # Use custom config
  
For more info: https://github.com/your-username/x402-earnings-api
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["paper", "live", "backtest"],
        default="paper",
        help="Trading mode (default: paper)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (default: configs/config.yaml)"
    )
    
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest suite and exit"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # === Backtest mode ===
    if args.backtest:
        from backtest.engine import run_full_backtest
        config = load_config(args.config or "configs/config.yaml")
        run_full_backtest(config)
        return
    
    # === Trading mode (paper or live) ===
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n\nEmpire shutdown by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
