from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from datetime import datetime, timedelta
import io
import base64
import logging

# 设置 matplotlib 使用非交互式后端 Agg
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前设置
import matplotlib.pyplot as plt

import baostock as bs

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.debug = True

# 确保模板目录存在
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
logger.debug(f"Template directory: {template_dir}")
logger.debug(f"Static directory: {static_dir}")

# 股票代码和名称映射
STOCK_MAP = {
    # A股
    '000001': '平安银行',
    '600000': '浦发银行',
    '000002': '万科A',
    '600519': '贵州茅台',
    '601318': '中国平安',
    '600036': '招商银行',
    '601166': '兴业银行',
    '600016': '民生银行',
    '601328': '交通银行',
    '601288': '农业银行',
    '601398': '工商银行',
    '601988': '中国银行',
    '601939': '建设银行',
    '601628': '中国人寿',
    '601601': '中国太保',
    '601336': '新华保险',
    '600030': '中信证券',
    '600837': '海通证券',
    '601688': '华泰证券',
    '600999': '招商证券',
    '601211': '国泰君安',
    '600031': '三一重工',
    '000333': '美的集团',
    '000651': '格力电器',
    '600887': '伊利股份',
    '600276': '恒瑞医药',
    '600104': '上汽集团',
    '600028': '中国石化',
    '601857': '中国石油',
    '601088': '中国神华',
    '600900': '长江电力',
    '601899': '紫金矿业',
    '600547': '山东黄金',
    '600585': '海螺水泥',
    '600309': '万华化学',
    '600019': '宝钢股份',
    '600050': '中国联通',
    '600048': '保利地产',
    '600383': '金地集团',
    '601318': '中国平安',
    '601398': '工商银行',
    '601988': '中国银行',
    '601939': '建设银行',
    '601328': '交通银行',
    '601166': '兴业银行',
    '600036': '招商银行',
    '600000': '浦发银行',
    '600016': '民生银行',
    '601169': '北京银行',
    '601009': '南京银行',
    '601998': '中信银行',
    '601818': '光大银行',
    '601288': '农业银行',
    '601398': '工商银行',
    '601988': '中国银行',
    '601939': '建设银行',
    '601328': '交通银行',
    '601166': '兴业银行',
    '600036': '招商银行',
    '600000': '浦发银行',
    '600016': '民生银行',
    '601169': '北京银行',
    '601009': '南京银行',
    '601998': '中信银行',
    '601818': '光大银行',
    # 港股
    '00700': '腾讯控股',
    '00941': '中国移动',
    '01299': '友邦保险',
    '02318': '中国平安',
    '03988': '中国银行',
    '00939': '建设银行',
    '01398': '工商银行',
    '00883': '中国海洋石油',
    '00857': '中国石油股份',
    '00388': '香港交易所',
    '00762': '中国联通',
    '00883': '中国海洋石油',
    '00857': '中国石油股份',
    '00388': '香港交易所',
    '00762': '中国联通',
    '00939': '建设银行',
    '01398': '工商银行',
    '03988': '中国银行',
    '02318': '中国平安',
    '01299': '友邦保险',
    '00941': '中国移动',
    '00700': '腾讯控股'
}

# 创建名称到代码的反向映射
NAME_TO_CODE = {name: code for code, name in STOCK_MAP.items()}

def get_stock_code(input_str):
    """根据输入获取股票代码"""
    if input_str.isdigit():
        return input_str
    return NAME_TO_CODE.get(input_str)

def validate_stock_code(code):
    """验证股票代码并返回正确的格式"""
    if not code.isdigit():
        return None, "股票代码必须是数字"
    
    if len(code) == 6:  # A股
        if code.startswith('6'):
            return f"sh.{code}", None
        elif code.startswith('0') or code.startswith('3'):
            return f"sz.{code}", None
        else:
            return None, "无效的A股代码"
    elif len(code) == 5:  # 港股
        return f"hk.{code.zfill(9)}", None
    else:
        return None, "股票代码长度不正确"

def get_a_stock_data(symbol, start_date=None, end_date=None):
    """获取A股数据"""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 登录系统
    bs.login()
    
    # 获取股票数据
    rs = bs.query_history_k_data_plus(
        symbol,
        "date,open,high,low,close,volume,amount,adjustflag",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3"
    )
    
    if rs.error_code != '0':
        bs.logout()
        return None, f"获取数据失败: {rs.error_msg}"
    
    # 处理数据
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    if not data_list:
        return None, "未获取到数据"
    
    # 转换为DataFrame
    df = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'adjustflag'])
    df['date'] = pd.to_datetime(df['date'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        df[col] = df[col].astype(float)
    
    return df, None

def plot_stock_data(df, symbol):
    """绘制股票数据图表"""
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['close'], label='收盘价', linewidth=2)
    plt.title(f'{STOCK_MAP.get(symbol, symbol)} 股票走势')
    plt.xlabel('日期')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True)
    
    # 保存图表到内存
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    
    return img

@app.route('/', methods=['GET', 'POST'])
def index():
    logger.debug("Accessing index route")
    try:
        if request.method == 'POST':
            logger.debug("Processing POST request")
            stock_input = request.form.get('stock_input')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            logger.debug(f"Input parameters: stock={stock_input}, start_date={start_date}, end_date={end_date}")
            
            # 获取股票代码
            stock_code = get_stock_code(stock_input)
            if not stock_code:
                logger.debug("Invalid stock code or name")
                return render_template('index.html', error="无效的股票代码或名称", stocks=STOCK_MAP)
            
            # 验证股票代码
            formatted_code, error = validate_stock_code(stock_code)
            if error:
                logger.debug(f"Stock code validation error: {error}")
                return render_template('index.html', error=error, stocks=STOCK_MAP)
            
            # 获取股票数据
            df, error = get_a_stock_data(formatted_code, start_date, end_date)
            if error:
                logger.debug(f"Error getting stock data: {error}")
                return render_template('index.html', error=error, stocks=STOCK_MAP)
            
            # 生成图表
            img = plot_stock_data(df, stock_code)
            
            # 创建 static 目录（如果不存在）
            os.makedirs(static_dir, exist_ok=True)
            
            # 保存数据到CSV
            csv_path = os.path.join('static', f'stock_data_{stock_code}.csv')
            df.to_csv(os.path.join(static_dir, f'stock_data_{stock_code}.csv'), index=False)
            
            # 转换图像为base64
            img_base64 = base64.b64encode(img.getvalue()).decode()
            chart_path = f"data:image/png;base64,{img_base64}"
            
            logger.debug("Rendering template with data")
            return render_template('index.html', 
                              stock_name=STOCK_MAP.get(stock_code, stock_code),
                              stock_code=stock_code,
                              data=df.tail().to_html(classes='table table-striped'),
                              chart_path=chart_path,
                              csv_path=csv_path,
                              stocks=STOCK_MAP)
        
        logger.debug("Rendering initial template")
        return render_template('index.html', stocks=STOCK_MAP)
    except Exception as e:
        logger.exception("Error in index route")
        return render_template('index.html', error=str(e), stocks=STOCK_MAP)

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        logger.debug(f"Downloading file: {filename}")
        return send_file(os.path.join(static_dir, filename), as_attachment=True)
    except Exception as e:
        logger.exception("Error downloading file")
        return str(e), 404

@app.route('/test')
def test():
    logger.debug("Accessing test route")
    return render_template('test.html')

@app.route('/hello')
def hello():
    logger.debug("Accessing hello route")
    return "Hello World! 你好，世界！"

@app.route('/simple')
def simple():
    logger.debug("Accessing simple route")
    return render_template('simple.html', current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, use_reloader=True, port=8081, host='localhost') 