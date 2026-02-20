import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime

# 配置企业微信 Webhook
WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK")

def send_wecom_msg(message):
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "markdown", "markdown": {"content": message}}
    try:
        requests.post(WECOM_WEBHOOK, json=payload, headers=headers)
    except Exception as e:
        print(f"发送失败: {e}")

def calculate_z(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

def monitor():
    # 1. 定义多维度监控矩阵
    # 格式：{名称: 雅虎财经代码}
    monitors = {
        "金银比(GSR)": "GC=F/SI=F",
        "铜价格(Copper)": "HG=F",
        "天然气(NatGas)": "NG=F",
        "大豆价格(Soy)": "ZS=F",
        "以星航运(ZIM)": "ZIM",
        "欧元/人民币(EURCNY)": "EURCNY=X",
        "美光科技(MU)": "MU"
    }

    print("启动全矩阵扫描...")
    
# 抓取数据
    raw_data = {}
    for name, ticker in monitors.items():
        try:
            if "/" in ticker: # 处理比例逻辑
                t1, t2 = ticker.split("/")
                d1 = yf.download(t1, period="2y", progress=False)['Close']
                d2 = yf.download(t2, period="2y", progress=False)['Close']
                # squeeze() 将单列 DataFrame 转为 Series，ffill 处理节假日不一致
                combined = (d1.squeeze() / d2.squeeze()).ffill().dropna()
                raw_data[name] = combined
            else:
                data = yf.download(ticker, period="2y", progress=False)['Close']
                raw_data[name] = data.squeeze().ffill().dropna()
        except Exception as e:
            print(f"数据抓取失败 [{name}]: {e}")

    alerts = []
    
    for name, series in raw_data.items():
        try:
            # 计算 Z-Score 并强制转为标量 (float)
            z_short_series = calculate_z(series, 60)
            z_long_series = calculate_z(series, 252)
            
            if len(z_short_series) < 1 or len(z_long_series) < 1:
                continue

            # 关键修复：使用 float() 确保它是单一数值
            z_short = float(z_short_series.iloc[-1])
            z_long = float(z_long_series.iloc[-1])
            
            # 2. 核心狙击逻辑 (后续 if 判断现在可以正常运行了)
            if z_short > 2.8:
                alerts.append(f"> ⚠️ **{name} 高位过热**\n> 短线Z轴: <font color=\"warning\">{z_short:.2f}</font>\n> 提示: 警惕类似白银的高位跳水风险。")
        
        # 逻辑 B：极度超跌 (抄底信号)
        if z_long < -2.2:
            alerts.append(f"> 🟢 **{name} 周期大底**\n> 长线Z轴: <font color=\"info\">{z_long:.2f}</font>\n> 提示: 价格已进入历史性低位区间。")

        # 逻辑 C：专属商业逻辑 (欧元结算)
        if name == "欧元/人民币(EURCNY)" and z_long < -1.5:
            alerts.append(f"> 🏥 **医疗项目成本锁定建议**\n> 欧元汇率低迷(Z:{z_long:.2f})\n> 建议: 考虑提前为上海诊所购买欧洲设备或支付预付款。")

    # 3. 发送报告
    if alerts:
        header = f"🏹 **全天候狙击手矩阵报告** ({datetime.now().strftime('%m-%d %H:%M')})\n\n"
        send_wecom_msg(header + "\n\n".join(alerts))
    else:
        # 心跳保持，确认系统活着
        send_wecom_msg(f"✅ 系统运行正常 | 当前扫描品种: {len(monitors)} | 暂无极端信号。")

if __name__ == "__main__":
    monitor()
