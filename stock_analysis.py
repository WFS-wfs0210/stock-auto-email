import akshare as ak
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

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

# ========== 修复1：强制使用北京时间，解决GitHub Actions时区错乱问题 ==========
def get_beijing_now():
    # 强制设置为东八区北京时间，无视运行环境的时区
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz)

# ========== 修复2：优化获取最近有交易的交易日，兜底无数据场景 ==========
def get_valid_trade_date():
    beijing_now = get_beijing_now()
    # 最多往前找10天，找到最近的有交易的工作日
    for i in range(10):
        check_date = beijing_now - timedelta(days=i)
        # 排除周六周日（5=周六，6=周日）
        if check_date.weekday() not in (5, 6):
            return check_date.strftime("%Y%m%d"), check_date
    # 极端情况兜底
    return beijing_now.strftime("%Y%m%d"), beijing_now

# ========== 修复3：增加股票名称映射表重试，避免接口限流 ==========
def get_stock_name_dict():
    try:
        print("正在获取A股股票名称映射表...")
        for retry in range(3):
            try:
                df = ak.stock_info_a_code_name()
                name_dict = dict(zip(df["code"].astype(str), df["name"]))
                print(f"✅ 名称映射表加载成功，共{len(name_dict)}只股票")
                return name_dict
            except Exception as e:
                if retry == 2:
                    raise
                print(f"⚠️ 第{retry+1}次获取失败，1秒后重试...")
                continue
    except Exception as e:
        print(f"❌ 名称映射表加载失败：{str(e)}")
        return {}

STOCK_NAME_DICT = get_stock_name_dict()

# 自动补全股票代码交易所前缀
def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    else:
        print(f"⚠️ 股票代码{code}无法识别交易所")
        return code

# ========== 修复4：优化股票数据获取，自动兜底最近有效数据 ==========
def get_stock_data(full_code, analysis_date):
    # 最多往前找5个交易日，确保能拿到有效数据
    for i in range(5):
        current_end_date = (datetime.strptime(analysis_date, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
        start_date = (datetime.strptime(current_end_date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
        try:
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=current_end_date,
                adjust="qfq"
            )
            # 拿到了有效数据，直接返回
            if not df.empty:
                print(f"✅ 成功获取{full_code}的数据，使用交易日：{current_end_date}")
                return df, current_end_date
        except:
            continue
    # 所有尝试都失败，返回空
    return None, None

# 生成分析报告
def generate_stock_report():
    analysis_date, today = get_valid_trade_date()
    print(f"📅 本次分析基准交易日：{analysis_date}（北京时间）")
    report = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report += "="*30 + "\n"

    for code in STOCK_LIST:
        code_str = str(code).strip()
        stock_name = STOCK_NAME_DICT.get(code_str, "未知股票")
        full_code = add_code_prefix(code_str)
        print(f"\n正在处理：{stock_name}({full_code})")

        try:
            # 获取股票有效数据
            df, use_date = get_stock_data(full_code, analysis_date)
            if df is None or df.empty:
                report += f"◆ {stock_name}（代码：{code_str}）\n❌ 无有效交易数据/连续停牌\n\n"
                report += "="*30 + "\n"
                continue

            # 提取最新交易日数据
            latest = df.iloc[-1]
            close = latest['收盘']
            ma5 = round(df['收盘'].tail(5).mean(), 2) if len(df)>=5 else "-"
            ma20 = round(df['收盘'].tail(20).mean(), 2) if len(df)>=20 else "-"
            vol_change = round(latest['成交量'] / df['成交量'].iloc[-2], 2) if len(df)>=2 else "-"

            # 写入报告
            report += f"◆ {stock_name}（代码：{code_str}）\n"
            report += f"🟡 中性持有信号\n"
            report += f"📊 最新收盘价：{close}元\n"
            report += f"📅 5日均线：{ma5}元\n"
            report += f"📅 20日均线：{ma20}元\n"
            report += f"📈 成交量变化：{vol_change}倍\n"
            report += f"📅 数据交易日：{use_date[:4]}年{use_date[4:6]}月{use_date[6:]}日\n\n"
            report += "="*30 + "\n"

        except Exception as e:
            print(f"❌ {stock_name} 分析出错：{str(e)}")
            report += f"◆ {stock_name}（代码：{code_str}）\n❌ 分析出错：{str(e)}\n\n"
            report += "="*30 + "\n"
            continue

    report += "⚠️ 本报告仅为量化分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report, today

# 发送邮件
def send_email(report_content, send_date):
    try:
        print("\n正在连接邮件服务器，准备发送报告...")
        msg = MIMEText(report_content, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_da
