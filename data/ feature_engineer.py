"""
Feature Engineer — computes 30+ technical indicators.
"""
import numpy as np
import pandas as pd
from typing import List
from utils.logger import get_module_logger

log = get_module_logger("feature_engineer")


class FeatureEngineer:
    def __init__(self, config: dict):
        self.config = config
        self.feature_names: List[str] = []
    
    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 50:
            return df
        df = df.copy()
        
        # TREND
        df["ema_8"] = df["close"].ewm(span=8, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
        
        # MOMENTUM (RSI)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-8)
        df["rsi_14"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        
        # ADX
        df["adx"] = self._adx(df["high"], df["low"], df["close"], 14)
        
        # BOLLINGER BANDS
        sma = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        df["bb_upper"] = sma + 2 * std
        df["bb_mid"] = sma
        df["bb_lower"] = sma - 2 * std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
        df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-8)
        
        # ATR
        df["atr_14"] = self._atr(df["high"], df["low"], df["close"], 14)
        df["atr_pct"] = df["atr_14"] / df["close"]
        
        # VOLUME
        df["obv"] = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
        df["volume_sma_20"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma_20"].replace(0, 1e-8)
        
        # RETURNS
        for p in [1, 3, 5, 10, 20]:
            df[f"return_{p}"] = df["close"].pct_change(p)
        
        # MICROSTRUCTURE
        df["hl_range"] = (df["high"] - df["low"]) / df["close"]
        df["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / df["close"]
        df["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / df["close"]
        
        df.dropna(inplace=True)
        self.feature_names = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume"]]
        return df
    
    def _adx(self, high, low, close, period=14):
        prev_close = close.shift(1)
        tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        up = high.diff()
        down = -low.diff()
        plus_dm = ((up > down) & (up > 0)).astype(float) * up
        minus_dm = ((down > up) & (down > 0)).astype(float) * down
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, 1e-8))
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr.replace(0, 1e-8))
        di_sum = (plus_di + minus_di).replace(0, 1e-8)
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        return dx.ewm(alpha=1/period, adjust=False).mean()
    
    def _atr(self, high, low, close, period=14):
        prev_close = close.shift(1)
        tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        return tr.ewm(alpha=1/period, adjust=False).mean()
    
    def get_feature_matrix(self, df: pd.DataFrame) -> np.ndarray:
        if not self.feature_names:
            df = self.compute_features(df)
        return df[self.feature_names].values
