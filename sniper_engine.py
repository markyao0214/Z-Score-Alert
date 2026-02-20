import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

def send_wecom_msg(message):
    if not WECOM_WEBHOOK:
        print("未检测到 Webhook 配置，跳过发送")
        return
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "markdown", "markdown": {"content": message}}
    try:
        requests.post(WECOM_WEBHOOK, json=payload, headers=headers, timeout=15)
    except Exception as e:
        print(f"发送失败: {e}")

def calculate_z(series, window):
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    return (series - rolling_mean) / rolling_std

def monitor():
    monitors = {
        "金银比(GSR)": "GC=F/SI=F",
        "铜价格(Copper)": "HG=F",
        "以星航运(ZIM)": "ZIM",
        "欧元/人民币(EURCNY)": "EURCNY=X"
    }

    raw_data = {}
    for name, ticker in monitors.items():
        try:
            if "/" in ticker:
                t1, t2 = ticker.split("/")
                d1 = yf.download(t1, period="2y", progress=False, auto_adjust=True)['Close']
                d2 = yf.download(t2, period="2y", progress=False, auto_adjust=True)['Close']
                combined = (d1.squeeze() / d2.squeeze()).ffill().dropna()
                if not combined.empty:
                    raw_data[name] = combined
            else:
                data = yf.download(ticker, period="2y", progress=False, auto_adjust=True)['Close']
                s = data.squeeze().ffill().dropna()
                if not s.empty:
                    raw_data[name] = s
        except Exception as e:
            print(f"数据抓取失败 [{name}]: {e}")

    alerts = []
    for name, series in raw_data.items():
        try:
            if len(series) < 252: continue
            
            zs = calculate_z(series, 60).dropna()
            zl = calculate_z(series, 252).dropna()
            
            if zs.empty or zl.empty: continue

            z_short, z_long = float(zs.iloc[-1]), float(zl.iloc[-1])
            curr = float(series.iloc[-1])

            if z_short > 2.8:
                alerts.append(f"### ⚠️ {name} 过热\n> Z:{z_short:.2f} | 价:{curr:.2f}")
            if z_long < -2.2:
                alerts.append(f"### 🟢 {name} 周期底\n> Z:{z_long:.2f} | 价:{curr:.2f}")
            if name == "欧元/人民币(EURCNY)" and z_long < -1.5:
                alerts.append(f"### 🏥 医疗项目锁汇建议\n> 欧元低迷: {curr:.4f}")

        except Exception as e:
            print(f"计算失败 [{name}]: {e}")

    if alerts:
        send_wecom_msg(f"🏹 **狙击手矩阵报告**\n\n" + "\n\n".join(alerts))
    else:
        print("扫描完成，无触发信号")

if __name__ == "__main__":
    monitor()
