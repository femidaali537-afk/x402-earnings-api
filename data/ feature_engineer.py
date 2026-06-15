import pandas as pd
import numpy as np

class FeatureEngineer:
    def __init__(self, config):
        self.config = config

    def compute_features(self, df):
        if df.empty or len(df) < 20: return df
        df = df.copy()
        
        # Simple RSI calculation (No library needed)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Simple EMA
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        return df.dropna()
