import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

def send_wecom_msg(message):
    if not WECOM_WEBHOOK:
        print("Error: WECOM_WEBHOOK environment variable not set.")
        return
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "markdown", "markdown": {"content": message}}
    try:
        response = requests.post(WECOM_WEBHOOK, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"发送失败: {e}")

def calculate_z(series, window):
    # 避免标准差为 0 导致除以零错误
    std = series.rolling(window).std()
    return (series - series.rolling(window).mean()) / std

def monitor():
    monitors = {
        "金银比(GSR)": "GC=F/SI=F",
        "铜价格(Copper)": "HG=F",
        "天然气(NatGas)": "NG=F",
        "以星航运(ZIM)": "ZIM",
        "欧元/人民币(EURCNY)": "EURCNY=X",
        "美光科技(MU)": "MU"
    }

    print(f"[{datetime.now()}] 启动全矩阵扫描...")
    alerts = []
    
    for name, ticker in monitors.items():
        try:
            # 数据抓取
            if "/" in ticker:
                t1, t2 = ticker.split("/")
                d1 = yf.download(t1, period="2y", progress=False, auto_adjust=True)['Close']
                d2 = yf.download(t2, period="2y", progress=False, auto_adjust=True)['Close']
                series = (d1.squeeze() / d2.squeeze()).ffill().dropna()
            else:
                data = yf.download(ticker, period="2y", progress=False, auto_adjust=True)['Close']
                series = data.squeeze().ffill().dropna()

            if series.empty or len(series) < 252:
                print(f"警告: {name} 数据量不足，跳过。")
                continue

            # 计算 Z-Score
            z_short_series = calculate_z(series, 60).dropna()
            z_long_series = calculate_z(series, 252).dropna()

            if z_short_series.empty or z_long_series.empty:
                continue

            # 强制标量化，防止真值歧义报错
            z_short = float(z_short_series.iloc[-1])
            z_long = float(z_long_series.iloc[-1])
            price = float(series.iloc[-1])

            # 策略逻辑
            if z_short > 2.8:
                alerts.append(f"### ⚠️ {name} 高位过热\n> **现价**: {price:.2f}\n> **短线Z轴**: <font color=\"warning\">{z_short:.2f}</font>\n> 提示: 波动率异常偏离，警惕回撤。")
            
            if z_long < -2.2:
                alerts.append(f"### 🟢 {name} 周期大底\n> **现价**: {price:.2f}\n> **长线Z轴**: <font color=\"info\">{z_long:.2f}</font>\n> 提示: 进入历史低估区。")

            if name == "欧元/人民币(EURCNY)" and z_long < -1.5:
                alerts.append(f"### 🏥 医疗项目锁汇建议\n> **欧元汇率**: {price:.4f} (Z:{z_long:.2f})\n> 建议: 汇率窗口利好，考虑锁定欧洲设备采购成本。")

            print(f"成功扫描 {name}: Z-Short={z_short:.2f}")

        except Exception as e:
            print(f"扫描异常 [{name}]: {e}")

    # 发送汇总
    if alerts:
        header = f"🏹 **狙击手矩阵报告** ({datetime.now().strftime('%m-%d %H:%M')})\n---\n"
        send_wecom_msg(header + "\n\n".join(alerts))
    else:
        print("扫描完成，暂无极端信号。")

if __name__ == "__main__":
    monitor()
