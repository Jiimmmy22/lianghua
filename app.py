from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
import pandas as pd
import os
from datetime import datetime, timedelta
import io
import base64
import logging
import yfinance as yf
import baostock as bs
import akshare as ak
import time
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.packages.urllib3.poolmanager import PoolManager
import requests
import random
import numpy as np
from io import BytesIO

# 导入缠论分析库
from chanlib import analyze_chan

# 设置 matplotlib 使用非交互式后端 Agg
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前设置
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 设置中文字体
import matplotlib.font_manager as fm
# 查找系统中的中文字体
font_path = '/System/Library/Fonts/PingFang.ttc'  # macOS 的 PingFang 字体
if os.path.exists(font_path):
    plt.rcParams['font.family'] = ['PingFang HK']
else:
    # 备选字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

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

# 股票代码映射
STOCK_MAP = {
    # A股
    '000001': '平安银行', '600036': '招商银行', '601318': '中国平安',
    '600519': '贵州茅台', '000858': '五粮液', '601888': '中国中免',
    
    # 港股
    '00700': '腾讯控股', '09988': '阿里巴巴-SW', '00941': '中国移动',
    '03690': '美团-W', '09999': '网易-S', '02020': '安踏体育',
    '01810': '小米集团-W',  # 添加小米集团
    
    # 美股
    'AAPL': '苹果公司', 'MSFT': '微软', 'GOOGL': '谷歌',
    'AMZN': '亚马逊', 'TSLA': '特斯拉', 'META': 'Meta平台',
    'NVDA': '英伟达', 'NFLX': '奈飞', 'BABA': '阿里巴巴',
    'PDD': '拼多多', 'NKE': '耐克'
}

# 创建名称到代码的反向映射
NAME_TO_CODE = {name: code for code, name in STOCK_MAP.items()}

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )

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

def get_stock_data(stock_code, start_date, end_date):
    """获取股票数据，支持全球市场"""
    try:
        logger.debug(f"开始获取股票数据: {stock_code}, {start_date} - {end_date}")
        
        # 标准化股票代码
        stock_code = stock_code.strip().upper()
        
        # 根据股票代码特征判断市场和获取方式
        if len(stock_code) == 6 and stock_code[0] in ['6', '0', '3']:  # A股
            try:
                logger.debug(f"尝试使用akshare获取A股数据: {stock_code}")
                if stock_code.startswith('6'):
                    ak_code = f"sh{stock_code}"
                else:
                    ak_code = f"sz{stock_code}"
                df = ak.stock_zh_a_daily(symbol=ak_code)
                if df.empty:
                    raise Exception("未找到A股数据")
            except Exception as e:
                logger.warning(f"使用akshare获取A股数据失败: {str(e)}")
                return get_yfinance_data(stock_code, start_date, end_date)
                
        elif len(stock_code) <= 5 and stock_code.isdigit():  # 港股
            try:
                logger.debug(f"尝试使用akshare获取港股数据: {stock_code}")
                df = ak.stock_hk_daily(symbol=f"{int(stock_code):04d}.HK")
                if df.empty:
                    raise Exception("未找到港股数据")
            except Exception as e:
                logger.warning(f"使用akshare获取港股数据失败: {str(e)}")
                return get_yfinance_data(f"{int(stock_code):04d}.HK", start_date, end_date)
                
        elif '.T' in stock_code:  # 日本股票
            try:
                logger.debug(f"尝试获取日本股票数据: {stock_code}")
                return get_yfinance_data(stock_code, start_date, end_date)
            except Exception as e:
                logger.warning(f"获取日本股票数据失败: {str(e)}")
                # 尝试使用其他数据源
                try:
                    df = ak.stock_jp_daily(symbol=stock_code.replace('.T', ''))
                    if not df.empty:
                        return df
                except:
                    pass
                raise
                
        else:  # 美股和其他市场
            try:
                logger.debug(f"尝试使用akshare获取美股/其他市场数据: {stock_code}")
                df = ak.stock_us_daily(symbol=stock_code)
                if df.empty:
                    raise Exception("未找到美股数据")
            except Exception as e:
                logger.warning(f"使用akshare获取美股数据失败: {str(e)}")
                return get_yfinance_data(stock_code, start_date, end_date)
        
        if df.empty:
            raise Exception("未找到股票数据")
            
        # 标准化数据格式
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= pd.to_datetime(start_date)) & 
               (df['date'] <= pd.to_datetime(end_date))]
               
        if df.empty:
            raise Exception("选定日期范围内没有数据")
            
        # 统一列名并排序
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('date')
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        logger.debug(f"成功获取股票数据，共{len(df)}条记录")
        return df
        
    except Exception as e:
        logger.exception(f"获取股票数据失败: {str(e)}")
        raise Exception(f"获取股票数据失败: {str(e)}")

def get_yfinance_data(symbol, start_date, end_date):
    """使用yfinance获取数据，包含重试机制"""
    max_retries = 3  # 减少重试次数
    retry_delay = 1  # 减少初始重试延迟
    
    # 标准化股票代码
    if len(symbol) == 6 and symbol[0] in ['6', '0', '3']:  # A股
        if symbol.startswith('6'):
            symbol = f"{symbol}.SS"  # 上海证券交易所
        else:
            symbol = f"{symbol}.SZ"  # 深圳证券交易所
    elif len(symbol) <= 5 and symbol.isdigit():  # 港股
        symbol = f"{symbol}.HK"
    elif '.T' in symbol:  # 日本股票
        symbol = symbol.replace('.T.SS', '.T')  # 修复错误的后缀
        symbol = symbol.replace('.T.SZ', '.T')
    
    # 配置SSL上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # 配置请求会话
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=retry_delay,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # 添加随机延迟以避免请求限制，但缩短时间
    time.sleep(random.uniform(0.5, 1))
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(symbol)
            stock.session = session
            df = stock.history(start=start_date, end=end_date, interval="1d")
            if df.empty:
                raise Exception("未找到股票数据")
                
            df = df.reset_index()
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            logger.debug(f"成功使用yfinance获取数据，共{len(df)}条记录")
            return df
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (1.5 ** attempt)  # 线性增长而不是指数增长
                logger.warning(f"第{attempt + 1}次尝试失败: {str(e)}，等待{wait_time:.1f}秒后重试")
                time.sleep(wait_time)
            else:
                raise Exception(f"在{max_retries}次尝试后仍未能获取数据: {str(e)}")

def plot_stock_data(df, symbol):
    """绘制股票数据图表"""
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['close'], label='收盘价', linewidth=2)
    plt.title(f'{STOCK_MAP.get(symbol, symbol)} 股票走势')
    plt.xlabel('日期')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    
    # 保存图表到内存
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    plt.close()
    
    return img

# 更新热门股票列表
hot_stocks = {
    'A股': {
        '000001': '平安银行',
        '600519': '贵州茅台',
        '601318': '中国平安',
        '000858': '五粮液',
        '600036': '招商银行',
        '601888': '中国中免'
    },
    '港股': {
        '0700': '腾讯控股',
        '9988': '阿里巴巴',
        '0941': '中国移动',
        '3690': '美团',
        '9999': '网易'
    },
    '美股': {
        'AAPL': '苹果',
        'MSFT': '微软',
        'GOOGL': '谷歌',
        'AMZN': '亚马逊',
        'TSLA': '特斯拉',
        'META': 'Meta',
        'NVDA': '英伟达',
        'NKE': '耐克'
    },
    '其他市场示例': {
        'TM': '丰田汽车(日本)',
        'SONY': '索尼(日本)',
        'SAP': '思爱普(德国)',
        'LVMH': '路威酩轩(法国)',
        'ASML': 'ASML(荷兰)',
        '005930.KS': '三星电子(韩国)'
    }
}

def get_stock_list():
    """获取全球主要市场的股票列表"""
    stocks = {
        'A股': [],
        '港股': [],
        '美股': [],
        '日股': []
    }
    
    try:
        # 获取A股列表
        df_a = ak.stock_zh_a_spot_em()
        stocks['A股'] = [{'code': row['代码'], 'name': row['名称']} 
                      for _, row in df_a.iterrows()]
    except Exception as e:
        logger.error(f"获取A股列表失败: {str(e)}")
        # 使用热门股票作为备选
        stocks['A股'] = [{'code': code, 'name': name} for code, name in hot_stocks['A股'].items()]
    
    try:
        # 获取港股列表
        df_hk = ak.stock_hk_spot_em()
        stocks['港股'] = [{'code': row['代码'], 'name': row['名称']} 
                       for _, row in df_hk.iterrows()]
    except Exception as e:
        logger.error(f"获取港股列表失败: {str(e)}")
        # 使用热门股票作为备选
        stocks['港股'] = [{'code': code, 'name': name} for code, name in hot_stocks['港股'].items()]
    
    try:
        # 获取美股列表
        df_us = ak.stock_us_spot_em()
        stocks['美股'] = [{'code': row['代码'], 'name': row['名称']} 
                       for _, row in df_us.iterrows()]
    except Exception as e:
        logger.error(f"获取美股列表失败: {str(e)}")
        # 使用热门股票作为备选
        stocks['美股'] = [{'code': code, 'name': name} for code, name in hot_stocks['美股'].items()]
        
    try:
        # 日本股票列表 - 由于 akshare 不支持直接获取日本股票列表，使用预定义的热门股票
        stocks['日股'] = [
            {'code': '7203.T', 'name': '丰田汽车'},
            {'code': '6758.T', 'name': '索尼集团'},
            {'code': '9984.T', 'name': '软银集团'},
            {'code': '6501.T', 'name': '日立制作所'},
            {'code': '7267.T', 'name': '本田汽车'},
            {'code': '9432.T', 'name': 'NTT'},
            {'code': '8306.T', 'name': '三菱UFJ金融'},
            {'code': '6502.T', 'name': '东芝'},
            {'code': '7751.T', 'name': '佳能'},
            {'code': '6752.T', 'name': '松下电器'}
        ]
        # 添加其他市场的例子
        stocks['其他市场'] = [
            {'code': '005930.KS', 'name': '三星电子(韩国)'},
            {'code': 'SAP.DE', 'name': '思爱普(德国)'},
            {'code': 'MC.PA', 'name': '路威酩轩(法国)'},
            {'code': 'ASML.AS', 'name': 'ASML(荷兰)'}
        ]
    except Exception as e:
        logger.error(f"获取其他市场股票列表失败: {str(e)}")
    
    return stocks

@app.route('/')
def index():
    """主页路由"""
    try:
        stocks = get_stock_list()
        return render_template('index.html', stocks=stocks)
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        return render_template('index.html', error="获取股票列表失败，请稍后重试")

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

@app.route('/download_file')
def download_stock_data():
    """下载股票数据"""
    try:
        if 'stock_data' not in globals():
            return "没有可下载的数据", 404
            
        # 创建一个Excel文件
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        pd.DataFrame(stock_data).to_excel(writer, index=False, sheet_name='股票数据')
        writer._save()  # 使用_save()而不是close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='stock_data.xlsx'
        )
    except Exception as e:
        logger.exception("下载数据失败")
        return str(e), 500

@app.route('/query_stock', methods=['POST'])
def query_stock():
    """查询股票数据"""
    logger.debug("Processing stock query")
    try:
        stock_code = request.form.get('stock', '').strip()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not stock_code:
            return render_template('index.html', error="请输入股票代码", stocks=get_stock_list())
            
        logger.debug(f"Query parameters: stock={stock_code}, start_date={start_date}, end_date={end_date}")
        
        # 获取股票数据
        try:
            df = get_stock_data(stock_code, start_date, end_date)
            if df.empty:
                return render_template('index.html', error="未找到股票数据", stocks=get_stock_list())
            
            # 保存数据到全局变量，供下载使用
            global stock_data
            stock_data = df.to_dict('records')
            
            # 生成图表
            img = plot_stock_data(df, stock_code)
            img_base64 = base64.b64encode(img.getvalue()).decode()
            
            stock_name = STOCK_MAP.get(stock_code, stock_code)
            
            return render_template('index.html',
                                stock_data=stock_data,
                                chart_data=img_base64,
                                stock_code=stock_code,
                                stock_name=stock_name,
                                stocks=get_stock_list())
                                
        except Exception as e:
            logger.exception("Error processing stock data")
            return render_template('index.html', error=str(e), stocks=get_stock_list())
            
    except Exception as e:
        logger.exception("Error in query_stock route")
        return render_template('index.html', error=str(e), stocks=get_stock_list())

@app.route('/chan_analysis', methods=['POST'])
def chan_analysis():
    """根据用户输入分析股票数据"""
    if request.method == 'POST':
        try:
            stock_input = request.form.get('stock')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            # 验证输入
            if not stock_input or not start_date or not end_date:
                return render_template('index.html', error="请输入完整信息")
            
            # 确保日期格式正确
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                return render_template('index.html', error="日期格式不正确，请使用YYYY-MM-DD格式")
            
            # 获取股票代码
            stock_code = get_stock_code(stock_input)
            if not stock_code:
                stock_code = stock_input
            
            # 检查是否为指数代码 - 添加对指数的支持
            is_index = False
            if stock_code.isdigit() and len(stock_code) == 6 and stock_code.startswith(('0', '3', '9')):
                # 可能是指数
                if stock_code.startswith('0') or stock_code.startswith('3') or stock_code.startswith('9'):
                    # 尝试获取作为指数的数据
                    try:
                        test_df = ak.stock_zh_index_daily(symbol=f"sz{stock_code}")
                        if not test_df.empty:
                            is_index = True
                            stock_code = f"i{stock_code}"  # 添加前缀表示这是指数
                    except:
                        pass
                    
            # 检查是否为ETF代码 - 添加对ETF的支持
            is_etf = False
            if stock_code.isdigit() and len(stock_code) == 6 and stock_code.startswith(('1', '5')):
                # 可能是ETF
                try:
                    test_df = ak.fund_etf_hist_em(symbol=f"sh{stock_code}", start_date=start_date, end_date=end_date)
                    if not test_df.empty:
                        is_etf = True
                        stock_code = f"e{stock_code}"  # 添加前缀表示这是ETF
                except:
                    pass
            
            # 获取股票数据
            df = get_stock_data(stock_code, start_date, end_date)
            
            if df.empty:
                return render_template('index.html', error="未找到股票数据")
            
            # 执行缠论分析
            try:
                from chanlib import analyze_chan
                
                # 分析结果（现在包含买卖信号）
                result_df = analyze_chan(df)
                
                # 统计买卖信号数量
                buy_signals = len(result_df[result_df['buy_signal'] > 0]) if 'buy_signal' in result_df.columns else 0
                sell_signals = len(result_df[result_df['sell_signal'] > 0]) if 'sell_signal' in result_df.columns else 0
                
                # 生成图表
                plt.switch_backend('Agg')
                
                # 创建图形
                fig = plt.figure(figsize=(15, 10))
                
                # 设置主图和子图的高度比例
                gs = plt.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
                
                # 主图 - K线和分析结果
                ax1 = plt.subplot(gs[0])
                ax2 = plt.subplot(gs[1])  # 成交量
                ax3 = plt.subplot(gs[2])  # 买入信号
                ax4 = plt.subplot(gs[3])  # 卖出信号
                
                # 在主图上绘制K线
                for i in range(len(df)):
                    # 绘制K线
                    open_price = df['open'].iloc[i]
                    close_price = df['close'].iloc[i]
                    high_price = df['high'].iloc[i]
                    low_price = df['low'].iloc[i]
                    
                    # 计算K线宽度
                    if len(df) > 100:
                        width = 0.6
                    else:
                        width = 0.8
                        
                    # 根据开盘收盘价格决定K线颜色
                    if close_price >= open_price:
                        color = 'red'
                        ax1.add_patch(plt.Rectangle((i-width/2, open_price), width, close_price-open_price, 
                                              fill=True, color=color, alpha=0.6))
                    else:
                        color = 'green'
                        ax1.add_patch(plt.Rectangle((i-width/2, close_price), width, open_price-close_price, 
                                              fill=True, color=color, alpha=0.6))
                        
                    # 绘制上下影线
                    ax1.plot([i, i], [low_price, high_price], color='black', linewidth=1)
                
                # 绘制分型点
                if 'fractal_type' in result_df.columns:
                    top_idx = result_df[result_df['fractal_type'] == 'top'].index
                    bottom_idx = result_df[result_df['fractal_type'] == 'bottom'].index
                    
                    for idx in top_idx:
                        if idx in df.index:
                            pos = df.index.get_loc(idx)
                            high = df['high'].iloc[pos]
                            ax1.scatter(pos, high, color='blue', marker='v', s=50)
                            
                    for idx in bottom_idx:
                        if idx in df.index:
                            pos = df.index.get_loc(idx)
                            low = df['low'].iloc[pos]
                            ax1.scatter(pos, low, color='blue', marker='^', s=50)
                
                # 绘制笔
                if 'stroke_mark' in result_df.columns:
                    stroke_points = result_df[result_df['stroke_mark'] == True]
                    # 至少需要两个点才能绘制线段
                    if len(stroke_points) >= 2:
                        x_coords = []
                        y_coords = []
                        for idx in stroke_points.index:
                            if idx in df.index:
                                pos = df.index.get_loc(idx)
                                x_coords.append(pos)
                                if 'stroke_type' in stroke_points.columns and stroke_points.loc[idx, 'stroke_type'] == 'top':
                                    y_coords.append(df['high'].iloc[pos])
                                else:
                                    y_coords.append(df['low'].iloc[pos])
                        
                        ax1.plot(x_coords, y_coords, 'g-', linewidth=1.5, label='笔')
                        
                        # 标记笔端点
                        for i in range(len(x_coords)):
                            ax1.scatter(x_coords[i], y_coords[i], color='g', marker='o', s=50)
                
                # 绘制线段
                if 'segment_mark' in result_df.columns:
                    segment_points = result_df[result_df['segment_mark'] == True]
                    # 至少需要两个点才能绘制线段
                    if len(segment_points) >= 2:
                        x_coords = []
                        y_coords = []
                        for idx in segment_points.index:
                            if idx in df.index:
                                pos = df.index.get_loc(idx)
                                x_coords.append(pos)
                                if 'segment_type' in segment_points.columns and segment_points.loc[idx, 'segment_type'] == 'top':
                                    y_coords.append(df['high'].iloc[pos])
                                else:
                                    y_coords.append(df['low'].iloc[pos])
                        
                        ax1.plot(x_coords, y_coords, 'b-', linewidth=2, label='线段')
                        
                        # 标记线段端点
                        for i in range(len(x_coords)):
                            ax1.scatter(x_coords[i], y_coords[i], color='b', marker='s', s=60)
                
                # 绘制成交量
                if 'volume' in df.columns:
                    for i in range(len(df)):
                        open_price = df['open'].iloc[i]
                        close_price = df['close'].iloc[i]
                        volume = df['volume'].iloc[i]
                        
                        # 计算宽度
                        if len(df) > 100:
                            width = 0.6
                        else:
                            width = 0.8
                            
                        # 根据开盘收盘价格决定成交量柱状图颜色
                        if close_price >= open_price:
                            color = 'red'
                        else:
                            color = 'green'
                            
                        ax2.bar(i, volume, width=width, color=color, alpha=0.6)
                
                # 绘制买入信号
                if 'buy_signal' in result_df.columns:
                    buy_signals_df = result_df[result_df['buy_signal'] > 0]
                    for idx in buy_signals_df.index:
                        if idx in df.index:
                            pos = df.index.get_loc(idx)
                            signal_type = buy_signals_df.loc[idx, 'buy_signal']
                            
                            # 绘制买入信号
                            if signal_type == 1:
                                signal_name = "底分型买入"
                            elif signal_type == 2:
                                signal_name = "线段底部买入"
                            elif signal_type == 3:
                                signal_name = "中枢突破买入"
                            else:
                                signal_name = "买入信号"
                            
                            ax3.bar(pos, 1, color='red', alpha=0.7)
                            ax3.text(pos, 1.1, signal_name, rotation=90, fontsize=8)
                
                # 绘制卖出信号
                if 'sell_signal' in result_df.columns:
                    sell_signals_df = result_df[result_df['sell_signal'] > 0]
                    for idx in sell_signals_df.index:
                        if idx in df.index:
                            pos = df.index.get_loc(idx)
                            signal_type = sell_signals_df.loc[idx, 'sell_signal']
                            
                            # 绘制卖出信号
                            if signal_type == 1:
                                signal_name = "顶分型卖出"
                            elif signal_type == 2:
                                signal_name = "线段顶部卖出"
                            elif signal_type == 3:
                                signal_name = "中枢跌破卖出"
                            else:
                                signal_name = "卖出信号"
                            
                            ax4.bar(pos, 1, color='green', alpha=0.7)
                            ax4.text(pos, 1.1, signal_name, rotation=90, fontsize=8)
                
                # 设置图表样式
                ax1.set_ylabel('价格')
                ax1.set_xlim(0, len(df)-1)
                ax1.legend(loc='best')
                
                ax2.set_ylabel('成交量')
                ax2.set_xlim(0, len(df)-1)
                
                ax3.set_ylabel('买入信号')
                ax3.set_xlim(0, len(df)-1)
                ax3.set_ylim(0, 2)
                ax3.set_yticks([])
                
                ax4.set_ylabel('卖出信号')
                ax4.set_xlim(0, len(df)-1)
                ax4.set_ylim(0, 2)
                ax4.set_yticks([])
                
                # 设置x轴刻度和标签
                x_ticks = np.linspace(0, len(df)-1, min(10, len(df)))
                x_labels = [df['date'].iloc[int(i)] for i in x_ticks]
                
                for ax in [ax1, ax2, ax3, ax4]:
                    ax.set_xticks(x_ticks)
                    ax.set_xticklabels(x_labels, rotation=45)
                
                # 显示股票名称
                stock_name = stock_input
                if is_index:
                    stock_name = f"指数: {stock_input}"
                elif is_etf:
                    stock_name = f"ETF: {stock_input}"
                
                plt.suptitle(f"{stock_name} 缠论分析 ({start_date} 至 {end_date})", fontsize=16)
                
                plt.tight_layout()
                
                # 保存图表
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=100)
                img_buffer.seek(0)
                plt.close()
                
                # 将图片编码为base64
                img_str = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                # 统计分析结果
                analysis_summary = {
                    "stock_code": stock_input,
                    "period": f"{start_date} 至 {end_date}",
                    "data_count": len(df),
                    "top_fractal_count": len(result_df[result_df['fractal_type'] == 'top']) if 'fractal_type' in result_df.columns else 0,
                    "bottom_fractal_count": len(result_df[result_df['fractal_type'] == 'bottom']) if 'fractal_type' in result_df.columns else 0,
                    "stroke_count": len(result_df[result_df['stroke_mark'] == True]) if 'stroke_mark' in result_df.columns else 0,
                    "segment_count": len(result_df[result_df['segment_mark'] == True]) if 'segment_mark' in result_df.columns else 0,
                    "buy_signal_count": buy_signals,
                    "sell_signal_count": sell_signals
                }
                
                return render_template('analysis.html',
                                     stock_code=stock_input,
                                     start_date=start_date,
                                     end_date=end_date,
                                     analysis=analysis_summary,
                                     image=img_str)
                
            except Exception as e:
                logger.error(f"执行缠论分析出错: {str(e)}", exc_info=True)
                return render_template('index.html', error=f"分析出错: {str(e)}")
            
        except Exception as e:
            logger.error(f"处理分析请求出错: {str(e)}", exc_info=True)
            return render_template('index.html', error=f"处理请求出错: {str(e)}")
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, use_reloader=True, port=8088, host='localhost') 