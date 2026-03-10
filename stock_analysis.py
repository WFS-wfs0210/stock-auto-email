import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ---------------------- 必须改成你自己的配置 ----------------------
# 你的自选股列表（只填纯数字代码，不要加sh/sz前缀）
STOCK_LIST = ["000719", "600361", "002759"]
# 发件邮箱（完整的163邮箱地址）
SEND_EMAIL = "15133943269@163.com"
# 163邮箱SMTP授权码（不是邮箱登录密码！）
EMAIL_AUTH_CODE = "XT3ZiXALfAJAzARW"
# 收件邮箱
RECEIVE_EMAIL = "15133943269@163.com"
# -------------------------------------------------------------------

# 获取A股股票代码-名称映射表
try:
    print("正在获取股票名称映射表...")
    stock_name_df = ak.stock_info_a_code_name()
    STOCK_NAME_DICT = dict(zip(stock_name_df["code"], stock_name_df["name"]))
    print(f"✅ 股票名称映射表获取成功，共加载 {len(STOCK_NAME_DICT)} 只股票")
except Exception as e:
    print(f"⚠️ 股票名称映射表获取失败，将默认显示未知股票：{str(e)}")
    STOCK_NAME_DICT = {}

# 自动补全股票代码前缀
def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    else:
        return code

# 生成分析报告
def generate_stock_report():
    today = datetime.now()
    analysis_date = today.strftime("%Y%m%d")
    report_content = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report_content += "="*40 + "\n"

    for code in STOCK_LIST:
        stock_name = STOCK_NAME_DICT.get(str(code).strip(), "未知股票")
        full_code = add_code_prefix(code)
        try:
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=analysis_date,
                end_date=analysis_date,
                adjust=""
            )

            if df.empty:
                report_content += f"◆ {stock_name}（股票代码：{code}）\n❌ 分析出错：当日无交易数据/停牌\n\n"
                report_content += "="*40 + "\n"
                continue

            close_price = df['收盘'].iloc[0]
            df_20 = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=(datetime.strptime(analysis_date, "%Y%m%d")).strftime("%Y%m%d"),
                end_date=analysis_date,
                adjust=""
            )
            ma5 = round(df_20['收盘'].tail(5).mean(), 2) if len(df_20)>=5 else "-"
            ma20 = round(df_20['收盘'].tail(20).mean(), 2) if len(df_20)>=20 else "-"
            vol_change = round(df['成交量'].iloc[0] / df_20['成交量'].iloc[-2], 2) if len(df_20)>=2 else "-"

            report_content += f"◆ {stock_name}（股票代码：{code}）\n"
            report_content += f"🟡 中性持有信号\n"
            report_content += f"📊 当前收盘价：{close_price}元\n"
            report_content += f"📅 5日均线：{ma5}元\n"
            report_content += f"📅 20日均线：{ma20}元\n"
            report_content += f"📈 昨日成交量变化：{vol_change}倍\n\n"
            report_content += "="*40 + "\n"

        except Exception as e:
            report_content += f"◆ {stock_name}（股票代码：{code}）\n❌ 分析出错：{str(e)}\n\n"
            report_content += "="*40 + "\n"
            continue

    report_content += "⚠️ 本报告仅为量化模型分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report_content, today

# 发送邮件（优化了报错提示）
def send_report_email(report_content, send_date):
    try:
        print("正在连接邮件服务器，准备发送报告...")
        msg = MIMEText(report_content, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"

        server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=10)
        server.login(SEND_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())
        server.quit()
        print("✅ 报告邮件发送成功！请去收件箱查看")
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮件发送失败：SMTP授权码错误！请检查授权码是否正确，不要填邮箱登录密码")
    except smtplib.SMTPConnectError:
        print("❌ 邮件发送失败：无法连接163邮件服务器！请检查网络，关掉VPN/防火墙，或换手机热点重试")
    except Exception as e:
        print(f"❌ 邮件发送失败，错误原因：{str(e)}")

# 主程序入口
if __name__ == "__main__":
    print("正在生成股票分析报告...")
    report, send_date = generate_stock_report()
    print("\n生成的报告内容：\n")
    print(report)
    # 这里已经开启了邮件发送，不需要再改#号
    send_report_email(report, send_date)
