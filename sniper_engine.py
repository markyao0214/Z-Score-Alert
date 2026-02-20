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
        # 生产环境建议设置 timeout 避免挂起
        requests.post(WECOM_WEBHOOK, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"发送失败: {e}")

def calculate_z(series, window):
    # Z-Score = (当前值 - 均值) / 标准差
    # 这里的 LaTeX 表达式为: $$Z = \frac{x - \mu}{\sigma}$$
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    return (series - rolling_mean) / rolling_std

def monitor():
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
    
    raw_data = {}
    for name, ticker in monitors.items():
        try:
            if "/" in ticker: 
                t1, t2 = ticker.split("/")
                d1 = yf.download(t1, period="2y", progress=False)['Close']
                d2 = yf.download(t2, period="2y", progress=False)['Close']
                # 关键修复 1：squeeze() 降维并前向填充处理交易日差
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
            # 核心逻辑计算
            z_short_series = calculate_z(series, 60)
            z_long_series = calculate_z(series, 252)
            
            if len(z_short_series) < 1 or len(z_long_series) < 1:
                continue

            # 关键修复 2：float() 转换确保逻辑判断不报错
            z_short = float(z_short_series.iloc[-1])
            z_long = float(z_long_series.iloc[-1])
            current_price = float(series.iloc[-1])

            # 3. 交易策略矩阵 (逻辑 B 和 C 移入 try 块防止变量未定义)
            # 逻辑 A：极度超涨
            if z_short > 2.8:
                alerts.append(f"### ⚠️ {name} 高位过热\n> **当前值**: {current_price:.2f}\n> **短线Z轴**: <font color=\"warning\">{z_short:.2f}</font>\n> 提示: 警惕类似白银的高位跳水风险。")
            
            # 逻辑 B：极度超跌
            if z_long < -2.2:
                alerts.append(f"### 🟢 {name} 周期大底\n> **当前值**: {current_price:.2f}\n> **长线Z轴**: <font color=\"info\">{z_long:.2f}</font>\n> 提示: 价格已进入历史性低位区间。")

            # 逻辑 C：专属商业逻辑 (跨境医疗项目)
            if name == "欧元/人民币(EURCNY)" and z_long < -1.5:
                alerts.append(f"### 🏥 医疗项目成本锁定建议\n> **欧元汇率低迷**: {current_price:.4f} (Z:{z_long:.2f})\n> 建议: 考虑提前为上海诊所购买欧洲设备或支付预付款以对冲汇率风险。")

        except Exception as e:
            print(f"指标计算异常 [{name}]: {e}")

    # 4. 发送报告
    if alerts:
        header = f"🏹 **全天候狙击手矩阵报告** ({datetime.now().strftime('%m-%d %H:%M')})\n---\n"
        send_wecom_msg(header + "\n\n".join(alerts))
    else:
        # 仅在收盘时段或手动运行时打印，防止静默运行让人心慌
        print("扫描完毕，暂无极端信号。")

if __name__ == "__main__":
    monitor()
