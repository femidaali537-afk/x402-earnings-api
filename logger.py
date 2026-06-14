"""
Logger — centralized logging setup using loguru.

Provides colorized console output + rotating file logs.
Every agent, every module uses this logger. NEVER use print().
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(level: str = "INFO", log_dir: str = "logs"):
    """
    Configure loguru with console + file sinks.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
    
    Returns:
        Configured logger instance (singleton — all modules share this)
    
    Features:
        - Colorized console output
        - Auto-rotating log files (100 MB max)
        - 30-day retention
        - Separate error log file
        - Async-safe (multi-agent safe)
    
    Example:
        >>> from utils.logger import setup_logger
        >>> logger = setup_logger("INFO")
        >>> logger.info("🚀 System started")
        🚀 System started
    """
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Remove default sink
    logger.remove()
    
    # ============ CONSOLE SINK (colorized) ============
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
        enqueue=True,  # Async-safe for multi-agent use
    )
    
    # ============ FILE SINK — all logs ============
    logger.add(
        f"{log_dir}/empire.log",
        level="DEBUG",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
    )
    
    # ============ FILE SINK — errors only ============
    logger.add(
        f"{log_dir}/errors.log",
        level="ERROR",
        rotation="50 MB",
        retention="90 days",
        backtrace=True,
        diagnose=True,  # Full stack trace for errors
        enqueue=True,
    )
    
    # ============ FILE SINK — trades only ============
    logger.add(
        f"{log_dir}/trades.log",
        level="INFO",
        rotation="100 MB",
        retention="365 days",
        filter=lambda record: "trade" in record["message"].lower() or "TRADE" in record["message"],
        enqueue=True,
    )
    
    logger.success(f"✓ Logger initialized (level={level}, dir={log_dir})")
    return logger


# Convenience: pre-configured module loggers
def get_module_logger(module_name: str):
    """
    Get a logger bound to a specific module name.
    
    Example:
        >>> log = get_module_logger("trend_follower")
        >>> log.info("BUY signal generated")
        [INFO] trend_follower - BUY signal generated
    """
    return logger.bind(module=module_name)
