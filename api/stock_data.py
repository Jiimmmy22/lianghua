import baostock as bs
import pandas as pd
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import os
import json
from functools import lru_cache

# 配置缓存目录
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

api = Blueprint('api', __name__)

def get_cache_path(stock_code, start_date, end_date, period):
    """生成缓存文件路径"""
    return os.path.join(CACHE_DIR, f'{stock_code}_{start_date}_{end_date}_{period}.json')

def load_cache(cache_path):
    """从缓存加载数据"""
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None
    except Exception:
        return None

def save_cache(cache_path, data):
    """保存数据到缓存"""
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

@lru_cache(maxsize=100)
def get_stock_name(bs_code):
    """获取股票名称（使用内存缓存）"""
    rs = bs.query_stock_basic(code=bs_code)
    if rs.error_code == '0' and rs.next():
        return rs.get_row_data()[1]
    return '未知'

@api.route('/stock_data')
def get_stock_data():
    try:
        # 获取请求参数
        stock_code = request.args.get('code')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'd')  # 默认日K

        # 参数验证
        if not all([stock_code, start_date, end_date]):
            # 准备返回数据
            return jsonify({'error': '缺少必要参数'})

        # 转换股票代码格式
        if stock_code.startswith('6'):
            bs_code = f'sh.{stock_code}'
        else:
            bs_code = f'sz.{stock_code}'

        # 登录baostock
        bs.login()

        try:
            # 检查缓存
            cache_path = get_cache_path(stock_code, start_date, end_date, period)
            cached_data = load_cache(cache_path)
            if cached_data:
                return jsonify(cached_data)
                
            # 获取股票名称（使用缓存）
            stock_name = get_stock_name(bs_code)

            # 获取K线数据
            period_map = {
                'day': 'd',
                'week': 'w',
                'month': 'm'
            }
            freq = period_map.get(period, 'd')

            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency=freq,
                adjustflag="2"  # 前复权
            )

            if rs.error_code != '0':
                # 准备返回数据
                return jsonify({'error': f'获取数据失败：{rs.error_msg}'})

            # 处理数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                data_list.append({
                    'date': row[0],
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5]),
                    'amount': float(row[6])
                })

            # 准备返回数据
            response_data = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'period': period,
                'data': data_list
            }
            
            # 保存到缓存
            save_cache(cache_path, response_data)
            return jsonify(response_data)

        finally:
            bs.logout()

    except Exception as e:
        return jsonify({'error': str(e)})

def process_technical_indicators(df, indicators):
    """批量处理技术指标"""
    result = {}
    
    def calculate_macd(data):
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def calculate_rsi(data, period=14):
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_kdj(data, n=9):
        low_list = data['low'].rolling(window=n, min_periods=n).min()
        high_list = data['high'].rolling(window=n, min_periods=n).max()
        rsv = (data['close'] - low_list) / (high_list - low_list) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d
        return k, d, j
    
    # 并行处理多个指标
    for indicator in indicators:
        indicator = indicator.lower()
        
        if indicator == 'macd':
            macd, signal, hist = calculate_macd(df)
            result['macd'] = macd.tolist()
            result['macd_signal'] = signal.tolist()
            result['macd_hist'] = hist.tolist()
        
        elif indicator == 'rsi':
            result['rsi'] = calculate_rsi(df).tolist()
        
        elif indicator == 'kdj':
            k, d, j = calculate_kdj(df)
            result['k'] = k.tolist()
            result['d'] = d.tolist()
            result['j'] = j.tolist()
    
    return result

@api.route('/technical_indicators')
def get_technical_indicators():
    try:
        # 获取请求参数
        stock_code = request.args.get('code')
        indicators = request.args.getlist('indicators')
        data = request.args.get('data')

        if not all([stock_code, indicators, data]):
            return jsonify({'error': '缺少必要参数'})

        try:
            # 将数据转换为DataFrame
            df = pd.DataFrame(json.loads(data))
        except Exception as e:
            return jsonify({'error': f'数据格式错误: {str(e)}'})

        # 批量处理技术指标
        result = process_technical_indicators(df, indicators)
        
        # 返回处理结果
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})