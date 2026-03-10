# ===================== 小白注意：敏感信息后面在GitHub里填，这里不用改 =====================
import akshare as ak
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# 从GitHub加密保险箱读取敏感信息，不用在这里写密码！
EMAIL_SENDER = os.getenv("EMAIL_SENDER")  # 发件人163邮箱
EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")  # 163邮箱授权码
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")  # 收件人邮箱

# ===================== 这里唯一要改：你要监控的股票代码！ =====================
# 格式：["股票代码1", "股票代码2", "股票代码3"]，最多填10只，太多会超时
STOCK_CODES = ["sz000719", "sh600361", "sz002759"]  # 示例：中原传媒、创新新材、天际股份
# ==========================================================================

def analyze_stock(stock_code):
    """单只股票分析函数，小白不用改"""
    try:
        # 获取最近30天的股票日线数据（前复权，除权除息不影响）
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        df = ak.stock_zh_a_daily(symbol=stock_code, start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df.empty:
            return "❌ 数据获取失败，请检查股票代码是否正确"

        # 计算核心技术指标
        current_price = df["close"].iloc[-1]  # 当前最新收盘价
        ma_5 = df["close"].tail(5).mean()     # 5日均线
        ma_20 = df["close"].tail(20).mean()   # 20日均线
        # 成交量对比（今日 vs 昨日）
        volume_increase = df["volume"].iloc[-1] / df["volume"].iloc[-2] if len(df) >= 2 else 1

        # 交易信号判断（小白可以自己改判断规则）
        if current_price > ma_5 and current_price > ma_20 and volume_increase > 1.1:
            status = "🟢 强势买入信号"
        elif current_price < ma_5 and current_price < ma_20:
            status = "🔴 弱势观望信号"
        else:
            status = "🟡 中性持有信号"
        
        # 拼接分析结果
        result = f"{status}\n"
        result += f"📈 当前收盘价：{current_price:.2f}元\n"
        result += f"📅 5日均线：{ma_5:.2f}元\n"
        result += f"📅 20日均线：{ma_20:.2f}元\n"
        result += f"📊 昨日成交量变化：{volume_increase:.2f}倍\n"
        return result
    
    except Exception as e:
        return f"❌ 分析出错：{str(e)}"

def send_to_163_email(message):
    """163邮箱发信函数，小白不用改"""
    # 163邮箱固定配置
    smtp_server = "smtp.163.com"
    smtp_port = 465

    # 构建邮件内容
    msg = MIMEText(message, "plain", "utf-8")
    msg["From"] = f"股票小助手<{EMAIL_SENDER}>"  # 发件人显示
    msg["To"] = EMAIL_RECEIVER  # 收件人
    msg["Subject"] = f"📅 {datetime.now().strftime('%Y年%m月%d日')} A股股票分析报告"  # 邮件标题

    try:
        # 连接163邮箱服务器，发邮件
        smtp = smtplib.SMTP_SSL(smtp_server, smtp_port)
        smtp.login(EMAIL_SENDER, EMAIL_AUTH_CODE)
        smtp.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        smtp.quit()
        print("✅ 邮件发送成功！请去邮箱查收")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")

# 主程序入口，小白不用改
if __name__ == "__main__":
    print("🚀 开始执行股票分析任务...")
    # 拼接邮件正文
    email_content = f"以下是{datetime.now().strftime('%Y年%m月%d日')}的自选股分析报告：\n\n"
    
    for code in STOCK_CODES:
        # 获取股票名称
        try:
            stock_info = ak.stock_info_sina(symbol=code)
            stock_name = stock_info["name"].values[0] if not stock_info.empty else "未知股票"
        except:
            stock_name = "未知股票"
        # 拼接单只股票的分析结果
        email_content += f"====================\n"
        email_content += f"🔹 {stock_name}（股票代码：{code}）\n"
        email_content += analyze_stock(code) + "\n\n"
    
    email_content += "====================\n⚠️ 本报告仅为量化模型分析结果，不构成任何投资建议，股市有风险，入市需谨慎！"
    
    # 发送邮件

    send_to_163_email(email_content)
