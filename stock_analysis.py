import akshare as ak

# 获取全市场A股代码与名称的映射表
try:
    stock_name_df = ak.stock_info_a_code_name()
    stock_name_dict = dict(zip(stock_name_df["code"], stock_name_df["name"]))
    print("✅ 股票名称映射表获取成功")
    
    # 测试你的3只股票
    test_codes = ["000719", "600361", "002759"]
    for code in test_codes:
        name = stock_name_dict.get(code, "未知股票")
        print(f"股票代码 {code} → 名称：{name}")
except Exception as e:
    print(f"❌ 获取映射表失败：{str(e)}")
