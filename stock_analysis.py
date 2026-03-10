import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz
import time

# ---------------------- 只改这里！其他内容不要动 ----------------------
# 1. 你的自选股+手动配置股票名称（彻底解决未知股票问题）
STOCK_CONFIG = {
    "000719": "中原传媒",
    "600361": "创新新材",
    "002759": "天际股份"
}
# 2. 你的163发件邮箱
SEND_EMAIL = "15133943269@163.com"
# 3. 你的163邮箱SMTP授权码（不是登录密码！）
EMAIL_AUTH_CODE = "XT3ZiXALfAJAzARW"
# 4. 你的收件邮箱
RECEIVE_EMAIL = "15133943269@163.com"
# -------------------------------------------------------------------

# 获取北京时间（彻底解决时区问题）
def get_beijing_time():
    return datetime.now(pytz.timezone('Asia/Shanghai'))

# 获取最近有效交易日
def get_valid_trade_date():
    now = get_beijing_time()
    # 最多往前找10天，排除周末
    for i in range(10):
        check_day = now - timedelta(days=i)
        if check_day.weekday() not in (5, 6):
            return check_day.strftime("%Y%m%d"), check_day
    return now.strftime("%Y%m%d"), now

# 补全股票代码前缀
def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    return code

# 带重试的股票数据获取（核心优化，提升国外服务器请求成功率）
def get_stock_data_with_retry(full_code, end_date, max_retry=5):
    for retry in range(max_retry):
        try:
            print(f"[第{retry+1}次尝试] 获取{full_code}的数据...")
            # 往前推30天拿足够的历史数据
            start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            # 接口加超时时间，避免无限等待
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
                timeout=20
            )
            if not df.empty:
                print(f"✅ {full_code} 数据获取成功，共{len(df)}条数据")
                return df
            else:
                print(f"⚠️ 第{retry+1}次尝试：接口返回空数据，1秒后重试")
                time.sleep(1)
        except Exception as e:
            print(f"❌ 第{retry+1}次尝试失败，错误：{str(e)}，2秒后重试")
            time.sleep(2)
    # 所有重试都失败
    print(f"❌ {full_code} 所有重试都失败，无法获取数据")
    return None

# 生成分析报告
def build_report():
    trade_date, today = get_valid_trade_date()
    print(f"📅 本次分析基准交易日：{trade_date}（北京时间）")
    report = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report += "="*30 + "\n"

    # 循环处理每只股票
    for code, stock_name in STOCK_CONFIG.items():
        full_code = add_code_prefix(code)
        print(f"\n==================== 正在处理：{stock_name}({full_code}) ====================")

        try:
            # 获取股票数据
            df = get_stock_data_with_retry(full_code, trade_date)
            if df is None or df.empty:
                report += f"◆ {stock_name}（代码：{code}）\n❌ 无有效交易数据/请求失败\n\n"
                report += "="*30 + "\n"
                continue

            # 提取最新交易日数据
            latest = df.iloc[-1]
            close = latest['收盘']
            ma5 = round(df['收盘'].tail(5).mean(), 2) if len(df)>=5 else "-"
            ma20 = round(df['收盘'].tail(20).mean(), 2) if len(df)>=20 else "-"
            vol_change = round(latest['成交量'] / df['成交量'].iloc[-2], 2) if len(df)>=2 else "-"

            # 写入报告
            report += f"◆ {stock_name}（代码：{code}）\n"
            report += f"🟡 中性持有信号\n"
            report += f"📊 最新收盘价：{close}元\n"
            report += f"📅 5日均线：{ma5}元\n"
            report += f"📅 20日均线：{ma20}元\n"
            report += f"📈 成交量变化：{vol_change}倍\n\n"
            report += "="*30 + "\n"
            print(f"✅ {stock_name} 分析完成")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ {stock_name} 分析出错：{error_msg}")
            report += f"◆ {stock_name}（代码：{code}）\n❌ 分析出错：{error_msg}\n\n"
            report += "="*30 + "\n"
            continue

    report += "⚠️ 本报告仅为量化分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report, today

# 发送邮件
def send_mail(report, send_date):
    try:
        print("\n正在准备发送邮件...")
        msg = MIMEText(report, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"

        # 邮件发送加超时
        server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=20)
        server.login(SEND_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")

# 主程序
if __name__ == "__main__":
    print("程序启动，开始执行股票分析...")
    report_content, send_date = build_report()
    print("\n==================== 最终报告内容 ====================")
    print(report_content)
    send_mail(report_content, send_date)