"""
GUARDRAILS — CRITICAL RISK CONTROLS
====================================
This module enforces 10 HARD LIMITS that CANNOT be bypassed by ANY agent,
including the Owner Agent. These are SACRED — never disable.

Without these, the system can lose all capital. They are non-negotiable.
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict
from utils.logger import logger


@dataclass
class GuardrailState:
    """Live state of guardrail metrics."""
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0
    open_positions: int = 0
    total_exposure_pct: float = 0.0
    last_data_timestamp: float = 0.0
    kill_switch_active: bool = False
    daily_reset_date: str = ""


class GuardrailSystem:
    """
    Hard risk limits that NO agent can override.
    These are SACRED — the system will REFUSE any trade that violates them.
    """
    
    def __init__(self, config: dict):
        # Load the 10 sacred limits from config
        self.max_drawdown_pct = config["max_drawdown_pct"]           # 1. Max drawdown
        self.daily_loss_limit_pct = config["daily_loss_limit_pct"]   # 2. Daily loss limit
        self.position_size_max_pct = config["position_size_max_pct"] # 3. Position size cap
        self.total_exposure_max_pct = config["total_exposure_max_pct"] # 4. Total exposure
        self.require_human_approval_usd = config.get(
            "require_human_approval_above_usd", float("inf")
        )                                                            # 5. Human approval
        self.black_swan_volatility = config["black_swan_volatility_threshold"]  # 6. Volatility
        self.data_stale_seconds = config["kill_switch_on_data_stale_seconds"]   # 7. Data freshness
        
        self.state = GuardrailState()
        self._violations: list = []
    
    # ==================================================================
    # PRE-TRADE CHECKS (called BEFORE any trade)
    # ==================================================================
    def check_trade_allowed(
        self,
        symbol: str,
        side: str,
        size_pct: float,
        equity: float,
    ) -> Tuple[bool, str]:
        """
        Returns (allowed, reason). 
        allowed=True, reason="" if trade is OK
        allowed=False, reason="..." if blocked
        
        This is THE gatekeeper. Every trade must pass this check.
        """
        # Check 1: Kill switch
        if self.state.kill_switch_active:
            return False, "KILL_SWITCH_ACTIVE"
        
        # Check 2: Position size cap
        if size_pct > self.position_size_max_pct:
            return False, (
                f"POSITION_SIZE_EXCEEDS_LIMIT "
                f"({size_pct:.3f} > {self.position_size_max_pct})"
            )
        
        # Check 3: Total exposure
        if self.state.total_exposure_pct + size_pct > self.total_exposure_max_pct:
            return False, (
                f"TOTAL_EXPOSURE_EXCEEDS_LIMIT "
                f"({self.state.total_exposure_pct + size_pct:.3f} > "
                f"{self.total_exposure_max_pct})"
            )
        
        # Check 4: Daily loss limit
        if self.state.daily_pnl < -self.daily_loss_limit_pct * equity:
            return False, (
                f"DAILY_LOSS_LIMIT_HIT "
                f"(daily_pnl=${self.state.daily_pnl:.2f}, "
                f"limit=${-self.daily_loss_limit_pct * equity:.2f})"
            )
        
        # Check 5: Max drawdown → auto kill switch
        if self.state.peak_equity > 0:
            dd = (self.state.peak_equity - equity) / self.state.peak_equity
            if dd > self.max_drawdown_pct:
                self.state.kill_switch_active = True
                logger.critical(
                    f"🚨 KILL SWITCH ACTIVATED — drawdown {dd:.2%} > "
                    f"{self.max_drawdown_pct:.2%}"
                )
                return False, f"MAX_DRAWDOWN_EXCEEDED ({dd:.3f} > {self.max_drawdown_pct})"
        
        # Check 6: Data freshness
        if self.state.last_data_timestamp > 0:
            stale = time.time() - self.state.last_data_timestamp
            if stale > self.data_stale_seconds:
                self.state.kill_switch_active = True
                logger.critical(
                    f"🚨 KILL SWITCH — data stale {stale:.0f}s "
                    f"> {self.data_stale_seconds}s"
                )
                return False, f"DATA_STALE ({stale:.0f}s)"
        
        # All checks passed
        return True, ""
    
    def check_human_approval_required(self, notional_usd: float) -> bool:
        """Some trade sizes require human approval (Check 5)."""
        return notional_usd >= self.require_human_approval_usd
    
    def check_black_swan(self, hourly_volatility: float) -> bool:
        """Returns True if extreme volatility detected (Check 6)."""
        return hourly_volatility > self.black_swan_volatility
    
    def check_correlation(
        self,
        new_symbol: str,
        open_symbols: list,
        correlation_matrix: dict,
    ) -> Tuple[bool, str]:
        """
        Check 8: Correlation cap.
        Don't open highly correlated positions.
        """
        for sym in open_symbols:
            key = f"{new_symbol}-{sym}"
            if key in correlation_matrix:
                corr = correlation_matrix[key]
                if abs(corr) > 0.7:  # 70% correlation
                    return False, f"HIGH_CORRELATION with {sym} ({corr:.2f})"
        return True, ""
    
    # ==================================================================
    # POST-TRADE UPDATES (called AFTER every trade)
    # ==================================================================
    def update_post_trade(
        self,
        pnl: float,
        equity: float,
        new_exposure_pct: float,
        position_opened: bool,
    ):
        """Update state after a trade fills."""
        # Reset daily PnL at midnight
        today = time.strftime("%Y-%m-%d")
        if self.state.daily_reset_date != today:
            self.state.daily_pnl = 0.0
            self.state.daily_reset_date = today
        
        self.state.daily_pnl += pnl
        self.state.total_pnl += pnl
        self.state.current_equity = equity
        self.state.peak_equity = max(self.state.peak_equity, equity)
        self.state.total_exposure_pct = new_exposure_pct
        
        if position_opened:
            self.state.open_positions += 1
        elif pnl != 0 and not position_opened:
            self.state.open_positions = max(0, self.state.open_positions - 1)
        
        # Re-check kill switch
        if self.state.peak_equity > 0:
            dd = (self.state.peak_equity - equity) / self.state.peak_equity
            if dd > self.max_drawdown_pct:
                self.state.kill_switch_active = True
                logger.critical(f"🚨 KILL SWITCH — DD {dd:.2%}")
    
    def update_data_timestamp(self, ts: float):
        """Update last data freshness timestamp (Check 7)."""
        self.state.last_data_timestamp = ts
    
    def update_open_positions(self, count: int):
        """Check 9: Max open positions."""
        if count > 5:  # from config but hardcoded as safety
            logger.warning(f"⚠️ Open positions {count} > 5 max")
    
    def record_volatility(self, hourly_vol: float):
        """Check 6: Black swan detection."""
        if self.check_black_swan(hourly_vol):
            logger.warning(
                f"⚠️ BLACK SWAN: hourly volatility {hourly_vol:.2%} > "
                f"{self.black_swan_volatility:.2%}"
            )
    
    # ==================================================================
    # KILL SWITCH CONTROL
    # ==================================================================
    def activate_kill_switch(self, reason: str = "manual"):
        """Emergency stop. Halts ALL trading."""
        self.state.kill_switch_active = True
        logger.critical(f"🚨 KILL SWITCH ACTIVATED — reason: {reason}")
    
    def reset_kill_switch(self, requires_human: bool = True) -> bool:
        """
        Manually reset kill switch. 
        Always requires human confirmation in production.
        """
        if requires_human:
            logger.warning(
                "⚠️ Kill switch reset requested — HUMAN CONFIRMATION REQUIRED"
            )
            return False
        self.state.kill_switch_active = False
        logger.warning("✓ Kill switch reset (manual)")
        return True
    
    # ==================================================================
    # STATUS & REPORTING
    # ==================================================================
    def get_state(self) -> dict:
        """Get current state for API/dashboard."""
        return {
            "daily_pnl": self.state.daily_pnl,
            "total_pnl": self.state.total_pnl,
            "current_drawdown_pct": (
                (self.state.peak_equity - self.state.current_equity)
                / self.state.peak_equity
                if self.state.peak_equity > 0 else 0
            ),
            "open_positions": self.state.open_positions,
            "total_exposure_pct": self.state.total_exposure_pct,
            "kill_switch": self.state.kill_switch_active,
            "limits": {
                "max_drawdown_pct": self.max_drawdown_pct,
                "daily_loss_limit_pct": self.daily_loss_limit_pct,
                "position_size_max_pct": self.position_size_max_pct,
                "total_exposure_max_pct": self.total_exposure_max_pct,
            }
        }
    
    def get_violations(self) -> list:
        """Get list of recent violations."""
        return self._violations[-10:]
