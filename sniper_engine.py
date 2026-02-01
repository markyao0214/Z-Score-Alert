import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

# 核心配置：从 GitHub Secrets 获取 Webhook
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

def send_wecom_msg(message):
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "markdown", "markdown": {"content": message}}
    try:
        r = requests.post(WECOM_WEBHOOK, json=payload, headers=headers)
        print(f"微信响应状态: {r.status_code}")
    except Exception as e:
        print(f"发送失败: {e}")

def monitor():
    # 监控品种
    tickers = {"Gold": "GC=F", "Silver": "SI=F", "Crude_Oil": "CL=F", "Micron": "MU"}
    print("正在抓取金融数据...")
    data = yf.download(list(tickers.values()), period="3y", progress=False)['Close']
    data = data.rename(columns={v: k for k, v in tickers.items()})
    data['GSR'] = data['Gold'] / data['Silver']
    
    # 计算极值 (Z-Score)
    def get_z(series):
        return (series - series.rolling(252).mean()) / series.rolling(252).std()

    gsr_z = get_z(data['GSR']).iloc[-1]
    
    # --- 💓 强制测试消息：只要运行就发这一条 ---
    test_msg = (
        f"✅ **狙击手系统重置成功**\n"
        f"> 当前金银比 Z轴: `{gsr_z:.2f}`\n"
        f"> 提示: 你能看到这条说明 GitHub 已经带火药上膛了！"
    )
    send_wecom_msg(test_msg)
    # ---------------------------------------

if __name__ == "__main__":
    monitor()
