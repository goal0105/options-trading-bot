import numpy as np
import pandas as pd

def percent_change_from_first_open_to_last_close(df: pd.DataFrame) -> float:
    """(last(c) - first(o))/first(o) * 100"""
    first_o = df['o'].iloc[0]
    last_c = df['c'].iloc[-1]
    return (last_c - first_o) / first_o * 100.0

def average_volume(df: pd.DataFrame) -> float:
    return float(df['v'].mean())

def atr_simple(df: pd.DataFrame) -> float:
    return float((df['h'] - df['l']).mean())

def gap_fill_pct(df: pd.DataFrame) -> float:
    """(first(o) - last(c))/first(o)*100"""
    first_o = df['o'].iloc[0]
    last_c = df['c'].iloc[-1]
    return (first_o - last_c) / first_o * 100.0

def last_above_20ma(df: pd.DataFrame) -> bool:
    # 20-period moving average of close
    if len(df) < 20:
        return False
    ma20 = df['c'].rolling(window=20).mean().iloc[-1]
    return float(df['c'].iloc[-1]) > float(ma20)

def pct_reclaim_of_level(df: pd.DataFrame, level: float) -> float:
    """Utility to compute % change from a level to last close"""
    last = df['c'].iloc[-1]
    return (last - level) / level * 100.0