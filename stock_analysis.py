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

# ========== 修复1：优化股票名称映射表获取，增加重试+容错 ==========
def get_stock_name_dict():
    try:
        print("正在获取A股股票名称映射表...")
        # 重试2次，避免单次请求失败
        for retry in range(2):
            try:
                stock_name_df = ak.stock_info_a_code_name()
                # 转为字典：key=纯数字股票代码（字符串），value=股票名称
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

# 自动补全股票代码的交易所前缀（修复前缀补全逻辑）
def add_code_prefix(code):
    code = str(code).strip()
    if code.startswith(('600','601','603','605','688')):
        return f"sh{code}"
    elif code.startswith(('000','001','002','003','300')):
        return f"sz{code}"
    else:
        print(f"⚠️ 股票代码{code}无法识别交易所，将使用原始代码")
        return code

# ========== 修复2：新增获取最近一个交易日的函数，解决盘中/休市拿不到数据的问题 ==========
def get_last_trade_date():
    today = datetime.now()
    # 往前推最多10天，找到最近的交易日
    for i in range(10):
        check_date = today - timedelta(days=i)
        # 排除周六周日
        if check_date.weekday() not in (5,6):
            return check_date.strftime("%Y%m%d"), check_date
    return today.strftime("%Y%m%d"), today

# 生成分析报告
def generate_stock_report():
    # 获取最近一个交易日，解决盘中/休市无数据的问题
    analysis_date, today = get_last_trade_date()
    print(f"📅 本次分析使用的交易日：{analysis_date}")
    # 报告标题
    report_content = f"以下是{today.year}年{today.month}月{today.day}日的自选股分析报告：\n"
    report_content += "="*40 + "\n"

    # 循环处理每一只自选股
    for code in STOCK_LIST:
        # 修复股票名称匹配：确保代码是纯字符串，和映射表key格式一致
        code_str = str(code).strip()
        stock_name = STOCK_NAME_DICT.get(code_str, "未知股票")
        full_code = add_code_prefix(code_str)
        print(f"\n正在处理：{stock_name}({full_code})")

        try:
            # ========== 修复3：修复均线计算的时间范围，往前推30天拿足够的历史数据 ==========
            # 计算历史数据的开始日期（往前推30天，确保有足够数据算5/20日均线）
            start_date = (datetime.strptime(analysis_date, "%Y%m%d") - timedelta(days=30)).strftime("%Y%m%d")
            # 获取近30天的日线数据，一次性拿到，不用重复请求接口
            df = ak.stock_zh_a_hist(
                symbol=full_code,
                period="daily",
                start_date=start_date,
                end_date=analysis_date,
                adjust="qfq" # 前复权，保证均线计算准确
            )

            # 空数据判断
            if df.empty:
                print(f"❌ {stock_name} 无交易数据/停牌")
                report_content += f"◆ {stock_name}（股票代码：{code_str}）\n❌ 分析出错：当日无交易数据/停牌\n\n"
                report_content += "="*40 + "\n"
                continue

            # 提取最新交易日的数据（最后一行）
            latest_data = df.iloc[-1]
            close_price = latest_data['收盘']
            # 计算5日、20日均线（修复了之前只有1天数据的错误）
            ma5 = round(df['收盘'].tail(5).mean(), 2) if len(df)>=5 else "-"
            ma20 = round(df['收盘'].tail(20).mean(), 2) if len(df)>=20 else "-"
            # 计算成交量变化（当日成交量/前一日成交量）
            vol_change = round(latest_data['成交量'] / df['成交量'].iloc[-2], 2) if len(df)>=2 else "-"

            # 写入报告（已替换为真实股票名称）
            print(f"✅ {stock_name} 分析完成")
            report_content += f"◆ {stock_name}（股票代码：{code_str}）\n"
            report_content += f"🟡 中性持有信号\n"
            report_content += f"📊 当前收盘价：{close_price}元\n"
            report_content += f"📅 5日均线：{ma5}元\n"
            report_content += f"📅 20日均线：{ma20}元\n"
            report_content += f"📈 昨日成交量变化：{vol_change}倍\n\n"
            report_content += "="*40 + "\n"

        # 捕获异常，避免单只股票出错导致整个程序崩溃
        except Exception as e:
            print(f"❌ {stock_name} 分析出错：{str(e)}")
            report_content += f"◆ {stock_name}（股票代码：{code_str}）\n❌ 分析出错：{str(e)}\n\n"
            report_content += "="*40 + "\n"
            continue

    # 追加免责声明
    report_content += "⚠️ 本报告仅为量化模型分析结果，不构成任何投资建议，股市有风险，投资需谨慎。"
    return report_content, today

# 发送邮件（优化了报错提示）
def send_report_email(report_content, send_date):
    try:
        print("\n正在连接邮件服务器，准备发送报告...")
        msg = MIMEText(report_content, "plain", "utf-8")
        msg['From'] = f"股票小助手 <{SEND_EMAIL}>"
        msg['To'] = RECEIVE_EMAIL
        msg['Subject'] = f"{send_date.year}年{send_date.month}月{send_date.day}日 自选股分析报告"

        server = smtplib.SMTP_SSL("smtp
