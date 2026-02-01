import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

# 从 GitHub Secrets 读取企业微信 Webhook 地址
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

# 加这一行调试：
if not WECOM_WEBHOOK:
    print("❌ 错误：未能从环境变量中读取到 WECOM_WEBHOOK，请检查 GitHub Secrets 配置！")
else:
    print("✅ 成功读取到 Webhook 地址，准备发送...")

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
        requests.post(WECOM_WEBHOOK, json=payload, headers=headers)
        print("企业微信告警已发送")
    except Exception as e:
        print(f"告警发送失败: {e}")

def monitor():
    # 监控品种：金银比(GSR), 原油(WTI), 美光(MU)
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
    # 极值逻辑：偏离曲线触及阈值
    if gsr_z < -2.5: alerts.append(f"> 🔴 **白银过热警报**\n> 当前金银比 Z-Score: <font color=\"warning\">{gsr_z:.2f}</font>\n> **动作**: 考虑布局 SLV 远期 Put。")
    if gsr_z > 2.5: alerts.append(f"> 🟢 **白银低估警报**\n> 当前金银比 Z-Score: <font color=\"info\">{gsr_z:.2f}</font>\n> **动作**: 关注白银长线做多机会。")
    if oil_z < -2.5: alerts.append(f"> 🛢️ **原油见底预警**\n> Z-Score: <font color=\"info\">{oil_z:.2f}</font>")
    if mu_z < -2.0: alerts.append(f"> 💾 **内存行业黄金坑**\n> 美光 Z-Score: <font color=\"info\">{mu_z:.2f}</font>")

    # 在最后加入这一段进行强制测试
    test_msg = "🔔 GitHub Actions 连通性测试：如果你看到这条消息，说明环境变量配置正确！"
    send_wecom_msg(test_msg) # 强制发送一条消息

    if alerts:
        msg = f"🏹 **极值狙击手报告** ({datetime.now().strftime('%Y-%m-%d')})\n\n" + "\n\n".join(alerts)
        send_wecom_msg(msg)

if __name__ == "__main__":
    monitor()
