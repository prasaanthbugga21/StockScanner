"""
NSE India Stock Scanner — Minervini + Qullamaggie Criteria
Runs every Sunday 9PM EST via GitHub Actions
Outputs: sector_heatmap_data.json + updates Notion dashboard
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import requests
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CUSTOM JSON ENCODER — fixes numpy/bool types
# ─────────────────────────────────────────────
class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):   return int(obj)
        if isinstance(obj, (np.floating,)):  return float(obj)
        if isinstance(obj, (np.bool_,)):     return bool(obj)
        if isinstance(obj, np.ndarray):      return obj.tolist()
        return super().default(obj)

def to_bool(val):  return bool(val)
def to_float(val): return float(val)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

NSE_SECTORS = {
    "IT":                 ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS","MPHASIS.NS","COFORGE.NS","PERSISTENT.NS","KPITTECH.NS"],
    "Banking":            ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS","INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","RBLBANK.NS"],
    "Pharma":             ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","BIOCON.NS","LUPIN.NS","AUROPHARMA.NS","TORNTPHARM.NS","ALKEM.NS","GLENMARK.NS"],
    "Auto":               ["MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS","TVSMOTOR.NS","ASHOKLEY.NS","BALKRISIND.NS","MOTHERSON.NS"],
    "FMCG":               ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS","MARICO.NS","COLPAL.NS","GODREJCP.NS","EMAMILTD.NS","VBL.NS"],
    "Metals":             ["TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","SAIL.NS","VEDL.NS","COALINDIA.NS","NMDC.NS","MOIL.NS","NATIONALUM.NS","HINDCOPPER.NS"],
    "Energy":             ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","GAIL.NS","POWERGRID.NS","NTPC.NS","ADANIGREEN.NS","TATAPOWER.NS","CESC.NS"],
    "Realty":             ["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","BRIGADE.NS","SOBHA.NS","PHOENIXLTD.NS","MAHLIFE.NS","SUNTECK.NS","LODHA.NS"],
    "Chemicals":          ["PIDILITIND.NS","SRF.NS","AARTIIND.NS","DEEPAKNITRITE.NS","NAVINFLUOR.NS","TATACHEM.NS","GALAXYSURF.NS","VINATI.NS","CLEAN.NS","ATUL.NS"],
    "Capital Goods":      ["LT.NS","SIEMENS.NS","ABB.NS","BHEL.NS","THERMAX.NS","CUMMINSIND.NS","AIAENG.NS","GRINDWELL.NS","SCHAEFFLER.NS","TIINDIA.NS"],
    "Consumer Durables":  ["TITAN.NS","HAVELLS.NS","VOLTAS.NS","BLUESTARCO.NS","CROMPTON.NS","DIXON.NS","AMBER.NS","VGUARD.NS","BAJAJELEC.NS","ORIENTELEC.NS"],
    "Financial Services": ["BAJFINANCE.NS","BAJAJFINSV.NS","SBILIFE.NS","HDFCLIFE.NS","ICICIPRULI.NS","CHOLAFIN.NS","MUTHOOTFIN.NS","MANAPPURAM.NS","PNBHOUSING.NS","IIFL.NS"],
}

# ─────────────────────────────────────────────
# HELPER: Fetch & clean OHLCV data
# ─────────────────────────────────────────────
def fetch_data(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close","Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return None

# ─────────────────────────────────────────────
# MINERVINI SEPA CRITERIA
# ─────────────────────────────────────────────
def check_minervini(df):
    try:
        close = df["Close"].squeeze()
        sma50  = close.rolling(50).mean()
        sma150 = close.rolling(150).mean()
        sma200 = close.rolling(200).mean()

        price = float(close.iloc[-1])
        s50   = float(sma50.iloc[-1])
        s150  = float(sma150.iloc[-1])
        s200  = float(sma200.iloc[-1])
        high_52w = float(close.rolling(252).max().iloc[-1])
        low_52w  = float(close.rolling(252).min().iloc[-1])
        sma200_1m_ago = float(sma200.iloc[-22]) if len(sma200) > 22 else float(sma200.iloc[0])

        criteria = {
            "price_above_sma50":       to_bool(price > s50),
            "sma50_above_sma150":      to_bool(s50 > s150),
            "sma150_above_sma200":     to_bool(s150 > s200),
            "sma200_trending_up":      to_bool(s200 > sma200_1m_ago),
            "price_within_25pct_high": to_bool(price >= 0.75 * high_52w),
            "price_30pct_above_low":   to_bool(price >= 1.30 * low_52w),
        }
        passed = int(sum(criteria.values()))
        score  = round(passed / len(criteria) * 100, 1)
        return {"passed": to_bool(passed == len(criteria)), "score": score, "criteria": criteria}
    except Exception:
        return {"passed": False, "score": 0.0, "criteria": {}}

# ─────────────────────────────────────────────
# QULLAMAGGIE VCP + MOMENTUM CRITERIA
# ─────────────────────────────────────────────
def check_qullamaggie(df):
    try:
        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        adr = float(((high - low) / close).rolling(21).mean().iloc[-1]) * 100
        recent_range = float((high.iloc[-15:].max() - low.iloc[-15:].min()) / close.iloc[-15])
        prior_range  = float((high.iloc[-45:-15].max() - low.iloc[-45:-15].min()) / close.iloc[-45])
        vol_recent   = float(volume.iloc[-10:].mean())
        vol_prior    = float(volume.iloc[-30:-10].mean())
        rs_period    = min(63, len(close) - 1)
        stock_return = float((close.iloc[-1] / close.iloc[-rs_period] - 1) * 100)
        high_52w     = float(high.rolling(252).max().iloc[-1])

        c = close.squeeze()
        up_d   = df[c > c.shift(1)].tail(20)
        down_d = df[c < c.shift(1)].tail(20)
        avg_up_vol   = float(up_d["Volume"].mean())   if len(up_d)   > 0 else 0.0
        avg_down_vol = float(down_d["Volume"].mean()) if len(down_d) > 0 else 1.0

        criteria = {
            "adr_above_3pct":  to_bool(adr > 3),
            "vcp_contraction": to_bool(recent_range < prior_range * 0.6),
            "volume_dryup":    to_bool(vol_recent < vol_prior * 0.8),
            "near_52w_high":   to_bool(float(close.iloc[-1]) >= 0.85 * high_52w),
            "vol_on_up_days":  to_bool(avg_up_vol > avg_down_vol),
            "strong_rs":       to_bool(stock_return > 10),
        }
        passed = int(sum(criteria.values()))
        score  = round(passed / len(criteria) * 100, 1)
        return {"passed": to_bool(passed >= 4), "score": score, "adr": round(adr,2), "rs_return": round(stock_return,2), "criteria": criteria}
    except Exception:
        return {"passed": False, "score": 0.0, "adr": 0.0, "rs_return": 0.0, "criteria": {}}

# ─────────────────────────────────────────────
# VOLUME SURGE INDICATOR
# ─────────────────────────────────────────────
def check_volume_surge(df):
    try:
        volume = df["Volume"].squeeze()
        close  = df["Close"].squeeze()
        avg_vol_50    = float(volume.rolling(50).mean().iloc[-1])
        last_week_vol = float(volume.iloc[-5:].mean())
        surge_ratio   = round(last_week_vol / avg_vol_50, 2) if avg_vol_50 > 0 else 1.0
        price_change  = float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
        return {
            "surge_ratio":     surge_ratio,
            "surge_detected":  to_bool(surge_ratio > 1.5),
            "price_change_5d": round(price_change, 2),
            "bullish_surge":   to_bool(surge_ratio > 1.5 and price_change > 0),
        }
    except Exception:
        return {"surge_ratio": 1.0, "surge_detected": False, "price_change_5d": 0.0, "bullish_surge": False}

# ─────────────────────────────────────────────
# SCAN ALL SECTORS
# ─────────────────────────────────────────────
def scan_all_sectors():
    results   = {}
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    print(f"\n{'='*60}\n  NSE MARKET SCAN — {scan_date}\n{'='*60}\n")

    for sector, tickers in NSE_SECTORS.items():
        print(f"Scanning {sector}...", end=" ", flush=True)
        sd = {"sector": sector, "total_stocks": len(tickers),
              "minervini_passed":0, "qullamaggie_passed":0,
              "volume_surge_count":0, "bullish_surge_count":0, "stocks":[]}
        m_scores, q_scores, adrs = [], [], []

        for ticker in tickers:
            df = fetch_data(ticker)
            if df is None: continue
            m = check_minervini(df)
            q = check_qullamaggie(df)
            v = check_volume_surge(df)
            if m["passed"]:          sd["minervini_passed"]    += 1
            if q["passed"]:          sd["qullamaggie_passed"]  += 1
            if v["surge_detected"]:  sd["volume_surge_count"]  += 1
            if v["bullish_surge"]:   sd["bullish_surge_count"] += 1
            m_scores.append(m["score"]); q_scores.append(q["score"]); adrs.append(q["adr"])
            sd["stocks"].append({"ticker":ticker,
                "minervini_score":m["score"], "qullamaggie_score":q["score"],
                "minervini_passed":m["passed"], "qullamaggie_passed":q["passed"],
                "adr":q["adr"], "rs_return":q["rs_return"], "volume_surge":v})

        n = len(sd["stocks"]) or 1
        sd["avg_minervini_score"]   = round(float(np.mean(m_scores)) if m_scores else 0.0, 1)
        sd["avg_qullamaggie_score"] = round(float(np.mean(q_scores)) if q_scores else 0.0, 1)
        sd["avg_adr"]               = round(float(np.mean(adrs))     if adrs     else 0.0, 2)
        sd["minervini_pct"]         = round(sd["minervini_passed"]    / n * 100, 1)
        sd["qullamaggie_pct"]       = round(sd["qullamaggie_passed"]  / n * 100, 1)
        sd["surge_pct"]             = round(sd["bullish_surge_count"] / n * 100, 1)
        sd["bullish_score"]         = round(sd["avg_minervini_score"]*0.4 + sd["avg_qullamaggie_score"]*0.4 + min(sd["surge_pct"],100)*0.2, 1)
        results[sector] = sd
        print(f"✓  M:{sd['minervini_pct']}%  Q:{sd['qullamaggie_pct']}%  Score:{sd['bullish_score']}")

    output = {"scan_date": scan_date, "sectors": results}
    with open("sector_heatmap_data.json", "w") as f:
        json.dump(output, f, indent=2, cls=SafeEncoder)
    print("\n✅ Scan complete. Saved to sector_heatmap_data.json")
    return output

# ─────────────────────────────────────────────
# NOTION INTEGRATION
# ─────────────────────────────────────────────
def update_notion(scan_data):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        print("⚠️  Notion credentials not set — skipping"); return
    headers = {"Authorization":f"Bearer {NOTION_TOKEN}","Content-Type":"application/json","Notion-Version":"2022-06-28"}
    for name, data in scan_data["sectors"].items():
        s = data["bullish_score"]
        sentiment = "🟢 Bullish" if s >= 60 else ("🟡 Neutral" if s >= 35 else "🔴 Bearish")
        payload = {"parent":{"database_id":NOTION_DB_ID},"properties":{
            "Sector":         {"title": [{"text":{"content":name}}]},
            "Scan Date":      {"date":  {"start":datetime.now().strftime("%Y-%m-%d")}},
            "Bullish Score":  {"number":data["bullish_score"]},
            "Minervini %":    {"number":data["minervini_pct"]},
            "Qullamaggie %":  {"number":data["qullamaggie_pct"]},
            "Volume Surge %": {"number":data["surge_pct"]},
            "Avg ADR %":      {"number":data["avg_adr"]},
            "Stocks Scanned": {"number":data["total_stocks"]},
            "Sentiment":      {"select":{"name":sentiment}},
        }}
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        status = "✓" if resp.status_code == 200 else f"✗ {resp.text[:80]}"
        print(f"  {status} {name}")

if __name__ == "__main__":
    scan_data = scan_all_sectors()
    update_notion(scan_data)
    print("\n🎯 Done!")
