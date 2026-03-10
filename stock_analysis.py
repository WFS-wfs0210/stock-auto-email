import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

# ---------------------- 只改这里！其他所有内容一个字都不要动！----------------------
# 1. 你的自选股，只填纯数字代码
STOCK_LIST = ["000719", "600361", "002759"]
# 2. 你的163发件邮箱
SEND_EMAIL = "15133943269@163.com"
# 3. 你的163邮箱SMTP授权码（不是登录密码！）
EMAIL_AUTH_CODE = "XT3ZiXALfAJAzARW"
# 4. 你的收件邮箱
RECEIVE_EMAIL = "15133943269@163.com"
# ---------------------- 下面的所有内容，绝对不要改！----------------------

# 获取北京时间
def get_beijing_time():
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz)

# 获取最近有效交易日
def get_trade_date():
    now = get_beijing_time()
    for i in range(10):
        check_day = now - timedelta(days=i)
        if check_day.weekday() not in (5,6):
            return check_day.strftime("%Y%m%d"), check_day
    return now.strftime("%Y%m%d"), now

# 获取股票名称映射
def get_name_dict():
    try:
        df = ak.stock_info_a_code_name()
        return dict(zip(df["code"].astype(str), df["name"]))
    except:
        return {}

# 补全股票代码前缀
def add_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    return code

# 获取股票数据
def get_stock_data(full_code, end_date):
    for i in range(5):
        current_end = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
        start_date = (datetime.strptime(current_end, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
        try:
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=current_end,
                adjust="qfq"
            )
            if not df.empty:
                return df, current_end
        except:
            continue
    return None, None

# 生成报告
def build_report():
    trade_date, today = get_trade_date()
    name_dict = get_name_dict()
    report = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report += "="*30 + "\n"

    for code in STOCK_LIST:
        code_str = str(code).strip()
        stock_name = name_dict.get(code_str, "未知股票")
        full_code = add_prefix(code_str)

        try:
            df, use_date = get_stock_data(full_code, trade_date)
            if df is None or df.empty:
                report += f"◆ {stock_name}（代码：{code_str}）\n❌ 无有效交易数据\n\n"
                report += "="*30 + "\n"
                continue

            latest = df.iloc[-1]
            close = latest['收盘']
            ma5 = round(df['收盘'].tail(5).mean(), 2) if len(df)>=5 else "-"
            ma20 = round(df['收盘'].tail(20).mean(), 2) if len(df)>=20 else "-"
            vol_change = round(latest['成交量'] / df['成交量'].iloc[-2], 2) if len(df)>=2 else "-"

            report += f"◆ {stock_name}（代码：{code_str}）\n"
            report += f"🟡 中性持有信号\n"
            report += f"📊 收盘价：{close}元\n"
            report += f"📅 5日均线：{ma5}元\n"
            report += f"📅 20日均线：{ma20}元\n"
            report += f"📈 成交量变化：{vol_change}倍\n\n"
            report += "="*30 + "\n"

        except Exception as e:
            report += f"◆ {stock_name}（代码：{code_str}）\n❌ 分析出错：{str(e)}\n\n"
            report += "="*30 + "\n"
            continue

    report += "⚠️ 本报告仅为量化分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report, today

# 发送邮件
def send_mail(report, send_date):
    try:
        msg = MIMEText(report, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        # 拆成短行，彻底避免复制断行
        subject = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"
        msg['Subject'] = subject

        server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=15)
        server.login(SEND_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")

# 主程序
if __name__ == "__main__":
    report_content, send_date = build_report()
    print(report_content)
    send_mail(report_content, send_date)