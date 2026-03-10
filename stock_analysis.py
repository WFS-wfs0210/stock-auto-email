import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# ---------------------- 必须改成你自己的配置 ----------------------
# 你的自选股列表（只填纯数字代码，不要加sh/sz前缀，程序会自动补全）
STOCK_LIST = ["000719", "600361", "002759"]
# 发件邮箱（完整的163邮箱地址）
SEND_EMAIL = "15133943269@163.com"
# 163邮箱SMTP授权码（不是邮箱登录密码！）
EMAIL_AUTH_CODE = "XT3ZiXALfAJAzARW"
# 收件邮箱
RECEIVE_EMAIL = "15133943269@163.com"
# -------------------------------------------------------------------

# 获取A股股票名称映射表，增加重试容错
def get_stock_name_dict():
    try:
        print("正在获取A股股票名称映射表...")
        for retry in range(2):
            try:
                stock_name_df = ak.stock_info_a_code_name()
                name_dict = dict(zip(stock_name_df["code"].astype(str), stock_name_df["name"]))
                print(f"✅ 股票名称映射表获取成功，共加载 {len(name_dict)} 只股票")
                return name_dict
            except:
                if retry == 1:
                    raise
                print(f"⚠️ 第{retry+1}次获取失败，正在重试...")
                continue
    except Exception as e:
        print(f"❌ 股票名称映射表获取失败，将默认显示未知股票，错误原因：{str(e)}")
        return {}

# 加载股票名称映射表
STOCK_NAME_DICT = get_stock_name_dict()

# 自动补全股票代码的交易所前缀
def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    else:
        print(f"⚠️ 股票代码{code}无法识别交易所，将使用原始代码")
        return code

# 获取最近一个交易日，解决盘中/休市无数据问题
def get_last_trade_date():
    today = datetime.now()
    for i in range(10):
        check_date = today - timedelta(days=i)
        if check_date.weekday() not in (5,6):
            return check_date.strftime("%Y%m%d"), check_date
    return today.strftime("%Y%m%d"), today

# 生成分析报告
def generate_stock_report():
    analysis_date, today = get_last_trade_date()
    print(f"📅 本次分析使用的交易日：{analysis_date}")
    report_content = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report_content += "="*40 + "\n"

    for code in STOCK_LIST:
        code_str = str(code).strip()
        stock_name = STOCK_NAME_DICT.get(code_str, "未知股票")
        full_code = add_code_prefix(code_str)
        print(f"\n正在处理：{stock_name}({full_code})")

        try:
            # 往前推30天拿足够的历史数据，计算均线
            start_date = (datetime.strptime(analysis_date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=analysis_date,
                adjust="qfq"
            )

            if df.empty:
                print(f"❌ {stock_name} 无交易数据/停牌")
                report_content += f"◆ {stock_name}（股票代码：{code_str}）\n❌ 分析出错：当日无交易数据/停牌\n\n"
                report_content += "="*40 + "\n"
                continue

            # 提取最新交易日数据
            latest_data = df.iloc[-1]
            close_price = latest_data['收盘']
            ma5 = round(df['收盘'].tail(5).mean(), 2) if len(df)>=5 else "-"
            ma20 = round(df['收盘'].tail(20).mean(), 2) if len(df)>=20 else "-"
            vol_change = round(latest_data['成交量'] / df['成交量'].iloc[-2], 2) if len(df)>=2 else "-"

            print(f"✅ {stock_name} 分析完成")
            report_content += f"◆ {stock_name}（股票代码：{code_str}）\n"
            report_content += f"🟡 中性持有信号\n"
            report_content += f"📊 当前收盘价：{close_price}元\n"
            report_content += f"📅 5日均线：{ma5}元\n"
            report_content += f"📅 20日均线：{ma20}元\n"
            report_content += f"📈 昨日成交量变化：{vol_change}倍\n\n"
            report_content += "="*40 + "\n"

        except Exception as e:
            print(f"❌ {stock_name} 分析出错：{str(e)}")
            report_content += f"◆ {stock_name}（股票代码：{code_str}）\n❌ 分析出错：{str(e)}\n\n"
            report_content += "="*40 + "\n"
            continue

    report_content += "⚠️ 本报告仅为量化模型分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report_content, today

# 发送邮件（修复了所有引号配对问题，无语法错误）
def send_report_email(report_content, send_date):
    try:
        print("\n正在连接邮件服务器，准备发送报告...")
        msg = MIMEText(report_content, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"

        # 完整无错误的SMTP连接行，引号完全配对
        server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=10)
        server.login(SEND_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SEND_EMAIL, RECEIVE_EMAIL, msg.as_string())
        server.quit()
        print("✅ 报告邮件发送成功！请去收件箱查看")
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮件发送失败：SMTP授权码错误！请检查授权码是否正确，不要填邮箱登录密码")
    except smtplib.SMTPConnectError:
        print("❌ 邮件发送失败：无法连接163邮件服务器！请检查网络配置")
    except Exception as e:
        print(f"❌ 邮件发送失败，错误原因：{str(e)}")

# 主程序入口
if __name__ == "__main__":
    report, send_date = generate_stock_report()
    print("\n==========
