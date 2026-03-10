import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# ---------------------- 只改这里！只改这里！只改这里！----------------------
# 1. 你的自选股，只填纯数字代码，不要加sh/sz
STOCK_LIST = ["000719", "600361", "002759"]
# 2. 你的163发件邮箱
SEND_EMAIL = "15133943269@163.com"
# 3. 你的163邮箱SMTP授权码（不是登录密码！）
EMAIL_AUTH_CODE = "XT3ZiXALfAJAzARW"
# 4. 你的收件邮箱
RECEIVE_EMAIL = "15133943269@163.com"
# ---------------------- 下面的所有内容，一个字都不要改！----------------------

def get_stock_name_dict():
    try:
        print("正在获取股票名称映射表...")
        for retry in range(2):
            try:
                df = ak.stock_info_a_code_name()
                name_dict = dict(zip(df["code"].astype(str), df["name"]))
                print(f"✅ 名称映射表加载成功，共{len(name_dict)}只股票")
                return name_dict
            except:
                if retry == 1:
                    raise
                continue
    except Exception as e:
        print(f"⚠️ 名称映射表加载失败：{str(e)}")
        return {}

STOCK_NAME_DICT = get_stock_name_dict()

def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    else:
        return code

def get_last_trade_date():
    today = datetime.now()
    for i in range(10):
        check_date = today - timedelta(days=i)
        if check_date.weekday() not in (5,6):
            return check_date.strftime("%Y%m%d"), check_date
    return today.strftime("%Y%m%d"), today

def generate_stock_report():
    analysis_date, today = get_last_trade_date()
    print(f"📅 分析交易日：{analysis_date}")
    report = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report += "="*30 + "\n"

    for code in STOCK_LIST:
        code_str = str(code).strip()
        stock_name = STOCK_NAME_DICT.get(code_str, "未知股票")
        full_code = add_code_prefix(code_str)
        print(f"正在处理：{stock_name}({full_code})")

        try:
            start_date = (datetime.strptime(analysis_date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=analysis_date,
                adjust="qfq"
            )

            if df.empty:
                report += f"◆ {stock_name}（代码：{code_str}）\n❌ 无交易数据/停牌\n\n"
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

def send_email(report_content, send_date):
    try:
        print("正在发送邮件...")
        msg = MIMEText(report_content, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"

        server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=10)
        server.login(SEND_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except smtplib.SMTPAuthenticationError:
        print("❌ 授权码错误！请检查SMTP授权码是否正确")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")

if __name__ == "__main__":
    report, send_date = generate_stock_report()
    print("\n" + "="*30 + "报告内容" + "="*30)
    print(report)
    send_email(report, send_date)
