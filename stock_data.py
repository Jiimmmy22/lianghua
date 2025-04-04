import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import baostock as bs

# 股票代码和名称映射字典
STOCK_MAP = {
    # A股
    '000001': '平安银行',
    '600000': '浦发银行',
    '000002': '万科A',
    '600519': '贵州茅台',
    '601318': '中国平安',
    '600036': '招商银行',
    '000858': '五粮液',
    '601398': '工商银行',
    '601288': '农业银行',
    '601988': '中国银行',
    '601328': '交通银行',
    '601166': '兴业银行',
    '600016': '民生银行',
    '600030': '中信证券',
    '601688': '华泰证券',
    '600837': '海通证券',
    '600031': '三一重工',
    '600276': '恒瑞医药',
    '000333': '美的集团',
    '000651': '格力电器',
    # 港股
    '00700': '腾讯控股',
    '00941': '中国移动',
    '01299': '友邦保险',
    '02318': '中国平安',
    '00939': '建设银行',
    '01398': '工商银行',
    '03988': '中国银行',
    '00883': '中国海洋石油',
    '00388': '香港交易所',
    '01088': '中国神华',
    '00857': '中国石油股份',
    '00386': '中国石油化工',
    '01171': '兖矿能源',
    '02333': '长城汽车',
    '02020': '安踏体育',
    '09618': '京东集团',
    '09988': '阿里巴巴',
    '03690': '美团',
    '09888': '百度集团',
    '09999': '网易'
}

# 反向映射字典（名称到代码）
NAME_TO_CODE = {v: k for k, v in STOCK_MAP.items()}

def get_stock_code(input_str):
    """
    根据输入获取股票代码
    :param input_str: 用户输入的股票代码或名称
    :return: 股票代码
    """
    # 如果是数字，直接返回
    if input_str.isdigit():
        return input_str
    
    # 如果是中文名称，查找对应的代码
    if input_str in NAME_TO_CODE:
        return NAME_TO_CODE[input_str]
    
    # 如果找不到，抛出异常
    raise ValueError(f"未找到股票代码或名称：{input_str}")

def validate_stock_code(code):
    """
    验证股票代码是否有效
    :param code: 股票代码
    :return: 验证后的股票代码
    """
    # 检查是否为数字
    if not code.isdigit():
        raise ValueError("股票代码必须是数字")
    
    # 检查长度
    if len(code) not in [5, 6]:
        raise ValueError("股票代码必须是5位（港股）或6位（A股）数字")
    
    # 处理港股
    if len(code) == 5:
        # 港股代码需要补零到9位
        padded_code = code.zfill(9)
        return f"hk.{padded_code}"  # 香港证券交易所
    
    # 处理A股
    if code.startswith(('6', '5')):
        return f"sh.{code}"  # 上海证券交易所
    elif code.startswith(('0', '3')):
        return f"sz.{code}"  # 深圳证券交易所
    else:
        raise ValueError("无效的股票代码，必须以6、5（上海）或0、3（深圳）开头")

def get_a_stock_data(symbol, start_date=None, end_date=None):
    """
    使用 baostock 获取股票数据
    :param symbol: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 股票数据DataFrame
    """
    try:
        # 获取股票代码
        stock_code = get_stock_code(symbol)
        # 验证股票代码
        symbol = validate_stock_code(stock_code)
        
        # 登录 Baostock
        bs.login()
        
        # 如果没有指定日期，使用默认值
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        print(f"\n正在获取 {symbol} 的数据...")
        print(f"开始日期: {start_date}")
        print(f"结束日期: {end_date}")
            
        # 获取日K线数据
        rs = bs.query_history_k_data_plus(
            symbol,
            "date,open,high,low,close,volume,amount,turn,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 复权类型，3：后复权
        )
        
        # 检查是否有错误
        if rs.error_code != '0':
            raise Exception(f"获取数据失败: {rs.error_msg}")
        
        # 转换数据
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            raise Exception("没有获取到数据")
        
        # 创建DataFrame
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 打印数据信息
        print(f"\n获取到 {len(df)} 条数据")
        print("\n数据示例：")
        print(df.head())
        
        # 重命名列
        df = df.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'close': 'Close',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume',
            'amount': 'Amount',
            'turn': 'Turnover',
            'pctChg': 'Change'
        })
        
        # 设置日期索引
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # 转换数据类型
        for col in ['Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Turnover', 'Change']:
            df[col] = pd.to_numeric(df[col])
        
        # 添加技术指标
        df['MA5'] = df['Close'].rolling(window=5).mean()  # 5日均线
        df['MA10'] = df['Close'].rolling(window=10).mean()  # 10日均线
        df['MA20'] = df['Close'].rolling(window=20).mean()  # 20日均线
        
        # 登出 Baostock
        bs.logout()
        
        return df
        
    except Exception as e:
        bs.logout()
        raise Exception(f"从 Baostock 获取数据时出错: {str(e)}")

def plot_stock_data(data, title):
    """
    绘制股票数据图表
    :param data: 股票数据DataFrame
    :param title: 图表标题
    """
    try:
        plt.figure(figsize=(15, 10))
        
        # 创建子图
        ax1 = plt.subplot(2, 1, 1)
        ax2 = plt.subplot(2, 1, 2)
        
        # 打印数据信息
        print("\n绘图数据示例：")
        print(data[['Close', 'MA5', 'MA10', 'MA20']].head())
        
        # 绘制价格和均线
        ax1.plot(data.index, data['Close'], label='收盘价', color='blue', linewidth=2)
        ax1.plot(data.index, data['MA5'], label='5日均线', color='orange', linewidth=1)
        ax1.plot(data.index, data['MA10'], label='10日均线', color='green', linewidth=1)
        ax1.plot(data.index, data['MA20'], label='20日均线', color='red', linewidth=1)
        ax1.set_title(title)
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True)
        
        # 绘制成交量
        ax2.bar(data.index, data['Volume'], color='gray', alpha=0.5)
        ax2.set_ylabel('成交量')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()
    except Exception as e:
        raise Exception(f"绘制图表时出错: {str(e)}")

def main():
    print("股票数据获取程序")
    print("=" * 50)
    print("支持的股票：")
    print("A股：")
    for code, name in STOCK_MAP.items():
        if len(code) == 6:
            print(f"- {code} ({name})")
    print("\n港股：")
    for code, name in STOCK_MAP.items():
        if len(code) == 5:
            print(f"- {code} ({name})")
    print("=" * 50)
    print("注意：")
    print("1. 可以直接输入股票代码或股票名称")
    print("2. A股：")
    print("   - 上海证券交易所股票代码以6或5开头")
    print("   - 深圳证券交易所股票代码以0或3开头")
    print("   - 所有A股代码必须是6位数字")
    print("3. 港股：")
    print("   - 所有港股代码必须是5位数字")
    print("   - 程序会自动补零到9位")
    print("=" * 50)
    
    while True:
        try:
            # 获取用户输入
            symbol = input("\n请输入股票代码或名称（输入'q'退出）：")
            if symbol.lower() == 'q':
                break
                
            start_date = input("请输入开始日期（格式：YYYY-MM-DD，直接回车使用默认值）：")
            end_date = input("请输入结束日期（格式：YYYY-MM-DD，直接回车使用默认值）：")
            
            # 如果用户没有输入日期，则使用None（将使用默认值）
            start_date = start_date if start_date else None
            end_date = end_date if end_date else None
            
            # 获取股票数据
            data = get_a_stock_data(symbol, start_date, end_date)
            
            # 显示数据基本信息
            print("\n数据统计信息：")
            print(data.describe())
            
            # 显示最近5天的数据
            print("\n最近5天的数据：")
            print(data.tail())
            
            # 获取股票名称
            stock_code = get_stock_code(symbol)
            stock_name = STOCK_MAP.get(stock_code, symbol)
            
            # 绘制图表
            plot_stock_data(data, f"{stock_name} ({stock_code}) 股票价格走势图")
            
            # 保存数据到CSV文件
            filename = f"{stock_name}_{stock_code}_stock_data.csv"
            data.to_csv(filename, encoding='utf-8-sig')  # 使用utf-8-sig编码以支持中文
            print(f"\n数据已保存到文件：{filename}")
            
        except Exception as e:
            print(f"\n错误：{str(e)}")
            continue

if __name__ == "__main__":
    main()