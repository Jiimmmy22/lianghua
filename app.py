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
from requests.packages.urllib3.util.retry import Retry # type: ignore
from requests.packages.urllib3.poolmanager import PoolManager # type: ignore
import requests
import random
import numpy as np
from io import BytesIO
import json
from matplotlib.dates import date2num, DateFormatter
from api.stock_data import api

# 导入缠论分析库
from chanlib import analyze_chan

# 设置 matplotlib 使用非交互式后端 Agg
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前设置
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates

# 如果旧版matplotlib导入失败，尝试新版
try:
    from matplotlib.finance import candlestick_ohlc # type: ignore
except ImportError:
    try:
        from mpl_finance import candlestick_ohlc
    except ImportError:
        # 如果都导入失败，定义一个简单的K线绘制函数
        def candlestick_ohlc(ax, quotes, width=0.6, colorup='r', colordown='g', alpha=0.8):
            """
            绘制K线图的替代函数
            """
            for i, (date, open_price, high, low, close) in enumerate(quotes):
                # 计算K线宽度
                if close >= open_price:
                    color = colorup
                    ax.add_patch(plt.Rectangle((i-width/2, open_price), width, close-open_price, 
                                       fill=True, color=color, alpha=alpha))
                else:
                    color = colordown
                    ax.add_patch(plt.Rectangle((i-width/2, close), width, open_price-close, 
                                       fill=True, color=color, alpha=alpha))
                
                # 绘制上下影线
                ax.plot([i, i], [low, high], color='black', linewidth=1)

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

# 数据缓存目录
data_cache_dir = 'data_cache'
if not os.path.exists(data_cache_dir):
    os.makedirs(data_cache_dir)

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        import urllib3
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx
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
    """获取股票数据"""
    logger.info(f"获取股票数据: {stock_code}, {start_date}-{end_date}")
    
    # 尝试从本地缓存加载数据
    cache_file = os.path.join(data_cache_dir, f"{stock_code}_{start_date}_{end_date}.csv")
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file)
            logger.info(f"从缓存加载数据: {cache_file}")
            if not df.empty:
                return df
        except Exception as e:
            logger.warning(f"从缓存加载数据失败: {e}")
    
    try:
        # 使用akshare获取数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        if df.empty:
            raise ValueError("获取到的数据为空")
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 缓存数据
        try:
            df.to_csv(cache_file, index=False)
            logger.info(f"数据已缓存: {cache_file}")
        except Exception as e:
            logger.warning(f"缓存数据失败: {e}")
            
        return df
    
    except Exception as e:
        logger.error(f"获取股票数据失败: {str(e)}")
        raise

def get_yfinance_data(symbol, start_date, end_date):
    """使用yfinance获取数据，带重试和错误处理"""
    import time
    import random
    
    # 设置重试参数
    max_retries = 5
    base_delay = 1.0
    
    # 特殊处理股票代码
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith('6'):
            symbol = f"{symbol}.SS"  # 上交所
        else:
            symbol = f"{symbol}.SZ"  # 深交所
    elif symbol.isdigit() and len(symbol) <= 5:
        symbol = f"{symbol}.HK"  # 港股
    elif symbol.startswith('i'):
        # 处理指数
        idx_code = symbol[1:]
        if idx_code == '000001':
            symbol = "^SSE"  # 上证指数
        elif idx_code == '399001':
            symbol = "^SZSC"  # 深证成指
        else:
            # 其他指数可能需要特殊映射
            pass
    
    # 尝试不同的方法获取数据
    for attempt in range(max_retries):
        try:
            import yfinance as yf
            
            # 创建股票对象
            stock = yf.Ticker(symbol)
            
            # 添加随机延迟以减轻API负载
            if attempt > 0:
                delay = base_delay * (1 + random.random())
                logger.info(f"第{attempt+1}次尝试获取 {symbol} 数据，等待{delay:.1f}秒")
                time.sleep(delay)
            
            # 获取历史数据
            df = stock.history(start=start_date, end=end_date, interval="1d")
            
            if df.empty:
                raise Exception("未找到股票数据")
            
            # 重置索引并标准化列名
            df = df.reset_index()
            if 'Date' in df.columns:
                df.rename(columns={'Date': 'date'}, inplace=True)
            if 'Open' in df.columns:
                df.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }, inplace=True)
            
            return df
            
        except Exception as e:
            logger.warning(f"第{attempt+1}次尝试失败: {str(e)}")
            
            # 增加指数退避重试延迟
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) * (1 + random.random() * 0.1)
                time.sleep(delay)
    
    # 所有重试都失败
    raise Exception(f"在{max_retries}次尝试后仍未能获取数据")

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
    """下载文件"""
    return send_file(filename, as_attachment=True)

@app.route('/download_data')  # 确保路由名与函数名一致
def download_stock_data():
    """下载股票数据为CSV文件"""
    global stock_data
    
    if not stock_data:
        return redirect(url_for('index'))
    
    # 创建CSV
    df = pd.DataFrame(stock_data)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    # 设置文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return send_file(
        output,
        as_attachment=True,
        download_name=f'stock_data_{timestamp}.csv',
        mimetype='text/csv'
    )

@app.route('/test')
def test():
    logger.debug("Accessing test route")
    return render_template('test.html', title="测试页面")

@app.route('/hello')
def hello():
    logger.debug("Accessing hello route")
    return "Hello World! 你好，世界！"

@app.route('/simple')
def simple():
    logger.debug("Accessing simple route")
    return render_template('simple.html', current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

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

# 修改图片保存路径
def save_plot_to_base64(fig):
    """将matplotlib图表保存为base64字符串"""
    img_stream = BytesIO()
    fig.savefig(img_stream, format='png', bbox_inches='tight')
    img_stream.seek(0)
    return base64.b64encode(img_stream.getvalue()).decode()

@app.route('/chan_analysis', methods=['POST'])
def chan_analysis():
    """处理缠论分析请求"""
    try:
        # 获取股票代码和日期范围
        stock_input = request.form.get('stock', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        
        # 验证输入
        if not stock_input or not start_date or not end_date:
            return render_template('index.html', error="请填写所有必填字段")
        
        # 获取标准化的股票代码
        stock_code = get_stock_code(stock_input.strip())
        if not stock_code:
            return render_template('index.html', error="无效的股票代码")
        
        # 获取股票名称（如有）
        stock_name = STOCK_MAP.get(stock_code, stock_code)
        
        # 获取股票数据
        try:
            df = get_stock_data(stock_code, start_date, end_date)
            if df.empty:
                return render_template('index.html', error="未找到股票数据")
        except Exception as e:
            logger.error(f"处理分析请求出错: {str(e)}", exc_info=True)
            return render_template('index.html', error=str(e))
        
        # 确保日期列存在并格式正确
        if 'Date' in df.columns:  # yfinance返回的是'Date'
            df['date'] = df['Date']
        elif 'time' in df.columns:  # 某些数据源可能用'time'
            df['date'] = df['time']
        
        # 重置索引，确保日期列可访问
        if df.index.name == 'date' or df.index.name == 'Date':
            df = df.reset_index()
            
        # 转换日期为数值
        df['date_num'] = date2num(pd.to_datetime(df['date']).values)
        
        # 执行缠论分析
        try:
            from chanlib import analyze_chan
            # 从chanlib导入买卖信号功能
            from chanlib.signals import add_trading_signals
            
            # 首先执行基础缠论分析
            chan_df = analyze_chan(df)
            
            # 然后添加买卖信号
            chan_df = add_trading_signals(chan_df)
            
            # 生成分析图表
            plt.figure(figsize=(12, 6))
            
            # 绘制简洁线图而不是K线图
            plt.plot(pd.to_datetime(df['date']), df['close'], color='white', linewidth=1.5)
            plt.title(f"{stock_name} ({stock_code}) 缠论分析图", color='white')
            
            # 设置灰色背景
            ax = plt.gca()
            ax.set_facecolor('#666666')
            plt.gcf().set_facecolor('#666666')
            
            # 设置y轴范围，留出一点边距
            min_price = df['low'].min() * 0.99
            max_price = df['high'].max() * 1.01
            plt.ylim(min_price, max_price)
            
            # 设置轴标签
            plt.xlabel('Date', color='white')
            plt.ylabel('Price', color='white')
            
            # 修改刻度颜色
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            
            # 格式化x轴日期
            date_format = mdates.DateFormatter('%Y/%m')
            ax.xaxis.set_major_formatter(date_format)
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            
            # 绘制网格线
            ax.grid(True, color='#777777', linestyle='-', linewidth=0.5, alpha=0.5)
            
            # 绘制分型点
            tops = chan_df[chan_df['fractal_mark'] == 1]
            bottoms = chan_df[chan_df['fractal_mark'] == -1]
            
            # 标记顶分型和底分型，使用较小的标记点使图表更清晰
            if not tops.empty:
                plt.scatter(pd.to_datetime(tops['date']), tops['high'], marker='^', color='red', s=30, alpha=0.7)
            if not bottoms.empty:
                plt.scatter(pd.to_datetime(bottoms['date']), bottoms['low'], marker='v', color='green', s=30, alpha=0.7)
            
            # 绘制笔，使用细线
            strokes = chan_df[chan_df['stroke_mark'] == True]
            if len(strokes) > 1:
                for i in range(len(strokes) - 1):
                    start_date = pd.to_datetime(strokes.iloc[i]['date'])
                    end_date = pd.to_datetime(strokes.iloc[i+1]['date'])
                    start_val = strokes.iloc[i]['high'] if strokes.iloc[i]['stroke_type'] == 'top' else strokes.iloc[i]['low']
                    end_val = strokes.iloc[i+1]['high'] if strokes.iloc[i+1]['stroke_type'] == 'top' else strokes.iloc[i+1]['low']
                    plt.plot([start_date, end_date], [start_val, end_val], 'b-', linewidth=1, alpha=0.7)
            
            # 简化买入卖出信号，只显示点，不显示标签
            if 'buy_signal' in chan_df.columns:
                buy_signals = chan_df[chan_df['buy_signal'] > 0]
                if not buy_signals.empty:
                    plt.scatter(pd.to_datetime(buy_signals['date']), buy_signals['low'], marker='^', color='lime', s=50, alpha=0.9)
            
            if 'sell_signal' in chan_df.columns:
                sell_signals = chan_df[chan_df['sell_signal'] > 0]
                if not sell_signals.empty:
                    plt.scatter(pd.to_datetime(sell_signals['date']), sell_signals['high'], marker='v', color='red', s=50, alpha=0.9)
            
            # 格式化x轴日期
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 统计分析结果
            stats = {
                "顶分型数量": len(chan_df[chan_df['fractal_mark'] == 1]),
                "底分型数量": len(chan_df[chan_df['fractal_mark'] == -1]),
                "笔的数量": len(chan_df[chan_df['stroke_mark'] == True]),
                "线段数量": len(chan_df[chan_df['segment_mark'] == True]),
                "中枢数量": len(set(chan_df[chan_df['hub_mark'] > 0]['hub_mark'])) if 'hub_mark' in chan_df.columns else 0,
                "买入信号数量": len(chan_df[chan_df['buy_signal'] > 0]) if 'buy_signal' in chan_df.columns else 0,
                "卖出信号数量": len(chan_df[chan_df['sell_signal'] > 0]) if 'sell_signal' in chan_df.columns else 0
            }
            
            # 收集买卖信号
            buy_signals = []
            sell_signals = []
            
            # 收集买入信号
            if 'buy_signal' in chan_df.columns:
                for i, row in chan_df[chan_df['buy_signal'] > 0].iterrows():
                    buy_signals.append({
                        'date': row['date'] if 'date' in row else str(i),
                        'type': int(row['buy_signal']),
                        'price': float(row['low']),
                        'index': int(i)
                    })
            
            # 收集卖出信号
            if 'sell_signal' in chan_df.columns:
                for i, row in chan_df[chan_df['sell_signal'] > 0].iterrows():
                    sell_signals.append({
                        'date': row['date'] if 'date' in row else str(i),
                        'type': int(row['sell_signal']),
                        'price': float(row['high']),
                        'index': int(i)
                    })
            
            # 准备前端需要的数据
            # 提取分型数据
            peaks = []
            for i, row in tops.iterrows():
                peaks.append({
                    'date': row['date'] if 'date' in row else str(i),
                    'price': float(row['high']),
                    'index': int(i)
                })
                
            troughs = []
            for i, row in bottoms.iterrows():
                troughs.append({
                    'date': row['date'] if 'date' in row else str(i),
                    'price': float(row['low']),
                    'index': int(i)
                })
            
            # 提取中枢数据
            price_centers = []
            if 'hub_mark' in chan_df.columns and 'zg' in chan_df.columns and 'zd' in chan_df.columns:
                hubs = chan_df[chan_df['hub_mark'] > 0]
                hub_ids = hubs['hub_mark'].unique()
                
                for hub_id in hub_ids:
                    hub_data = hubs[hubs['hub_mark'] == hub_id]
                    if not hub_data.empty:
                        start_date = hub_data.iloc[0]['date'] if 'date' in hub_data else str(hub_data.index[0])
                        end_date = hub_data.iloc[-1]['date'] if 'date' in hub_data else str(hub_data.index[-1])
                        
                        # 获取中枢的上下边界
                        zg = hub_data['zg'].iloc[0] if 'zg' in hub_data else hub_data['high'].max()
                        zd = hub_data['zd'].iloc[0] if 'zd' in hub_data else hub_data['low'].min()
                        
                        price_centers.append({
                            'start': start_date,
                            'end': end_date,
                            'zg': float(zg),
                            'zd': float(zd)
                        })
            
            # 提取绘制笔的数据
            strokes_data = []
            if len(strokes) > 1:
                for i in range(len(strokes) - 1):
                    start_date = strokes.iloc[i]['date'] if 'date' in strokes else str(strokes.index[i])
                    end_date = strokes.iloc[i+1]['date'] if 'date' in strokes else str(strokes.index[i+1])
                    start_val = float(strokes.iloc[i]['high'] if strokes.iloc[i]['stroke_type'] == 'top' else strokes.iloc[i]['low'])
                    end_val = float(strokes.iloc[i+1]['high'] if strokes.iloc[i+1]['stroke_type'] == 'top' else strokes.iloc[i+1]['low'])
                    
                    strokes_data.append({
                        'start_date': start_date,
                        'end_date': end_date,
                        'start_val': start_val,
                        'end_val': end_val
                    })
            
            # 保存图表为base64字符串
            img_base64 = save_plot_to_base64(plt)
            plt.close()
            
            # 准备显示的数据
            stock_data_list = []
            for i, row in df.iterrows():
                stock_data_list.append({
                    'date': row['date'] if 'date' in row else str(i),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume']) if 'volume' in row else 0
                })
            
            # 返回分析结果
            return render_template('index.html', 
                                  stock_data=stock_data_list, 
                                  stock_name=stock_name,
                                  stock_code=stock_code,
                                  stats=stats,
                                  buy_signals=buy_signals,
                                  sell_signals=sell_signals,
                                  peaks=peaks,
                                  troughs=troughs,
                                  price_centers=price_centers,
                                  strokes=strokes_data,
                                  chart_data=img_base64)
        
        except Exception as e:
            logger.error(f"执行缠论分析时出错: {str(e)}", exc_info=True)
            return render_template('index.html', error=f"分析错误: {str(e)}")
    
    except Exception as e:
        logger.error(f"处理分析请求出错: {str(e)}", exc_info=True)
        return render_template('index.html', error=f"处理请求出错: {str(e)}")

# 修改主程序入口
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8088))
    app.run(host='0.0.0.0', port=port, debug=False)

# Vercel环境设置
app.debug = False  # 生产环境禁用调试模式