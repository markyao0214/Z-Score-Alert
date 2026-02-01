import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

# 从 GitHub Secrets 读取配置
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

def send_wecom_msg(message):
    """发送企业微信机器人消息"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": message
        }
    }
    try:
        r = requests.post(WECOM_WEBHOOK, json=payload, headers=headers)
        print(f"微信响应状态: {r.status_code}")
    except Exception as e:
        print(f"告警发送失败: {e}")

def monitor():
    # 监控品种
    tickers = {"Gold": "GC=F", "Silver": "SI=F", "Crude_Oil": "CL=F", "Micron": "MU"}
    
    print("正在获取数据...")
    data = yf.download(list(tickers.values()), period="3y", progress=False)['Close']
    data = data.rename(columns={v: k for k, v in tickers.items()})
    data['GSR'] = data['Gold'] / data['Silver']
    
    def get_z(series):
        return (series - series.rolling(252).mean()) / series.rolling(252).std()

    # 获取最新一天的 Z-Score
    gsr_z = get_z(data['GSR']).iloc[-1]
    oil_z = get_z(data['Crude_Oil']).iloc[-1]
    mu_z = get_z(data['Micron']).iloc[-1]
    
    # --- 💓 核心测试逻辑：强制发送心跳包 ---
    heartbeat_msg = (
        f"🔋 **狙击手系统心跳测试**\n"
        f"> 状态: <font color=\"info\">运行中</font>\n"
        f"> 当前金银比 Z轴: `{gsr_z:.2f}`\n"
        f"> 提示: 你收到此消息说明 GitHub 链路已完全打通！"
    )
    send_wecom_msg(heartbeat_msg)
    # ---------------------------------------

    alerts = []
    if gsr_z < -2.5: alerts.append(f"> 🔴 **白银过热警报** (Z: {gsr_z:.2f})")
    if gsr_z > 2.5: alerts.append(f"> 🟢 **白银低估警报** (Z: {gsr_z:.2f})")
    if oil_z < -2.5: alerts.append(f"> 🛢️ **原油见底预警** (Z: {oil_z:.2f})")

    if alerts:
        msg = f"🏹 **实时极值警报** ({datetime.now().strftime('%Y-%m-%d')})\n\n" + "\n\n".join(alerts)
        send_wecom_msg(msg)

if __name__ == "__main__":
    monitor()
