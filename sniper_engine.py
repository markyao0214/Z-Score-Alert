import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

# 从系统环境变量读取配置（GitHub Secrets）
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def monitor():
    tickers = {"Gold": "GC=F", "Silver": "SI=F", "Crude_Oil": "CL=F", "Micron": "MU"}
    data = yf.download(list(tickers.values()), period="3y")['Close']
    data = data.rename(columns={v: k for k, v in tickers.items()})
    data['GSR'] = data['Gold'] / data['Silver']
    
    def get_z(series):
        return (series - series.rolling(252).mean()) / series.rolling(252).std()

    gsr_z = get_z(data['GSR']).iloc[-1]
    oil_z = get_z(data['Crude_Oil']).iloc[-1]
    mu_z = get_z(data['Micron']).iloc[-1]
    
    alerts = []
    if gsr_z < -2.5: alerts.append(f"🔴 *白银过热*! GSR Z: `{gsr_z:.2f}` (警惕崩盘)")
    if gsr_z > 2.5: alerts.append(f"🟢 *白银低估*! GSR Z: `{gsr_z:.2f}` (考虑布局)")
    if oil_z < -2.5: alerts.append(f"🛢️ *原油见底*! Z: `{oil_z:.2f}`")
    if mu_z < -2.0: alerts.append(f"💾 *内存黄金坑*! MU Z: `{mu_z:.2f}`")

    if alerts:
        msg = f"🚀 *狙击手报告 ({datetime.now().strftime('%Y-%m-%d')})*\n\n" + "\n".join(alerts)
        send_telegram_msg(msg)

if __name__ == "__main__":
    monitor()
