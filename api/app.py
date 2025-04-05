from flask import Flask, request, jsonify, render_template
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.dirname(current_dir)

app = Flask(__name__,
           template_folder=os.path.join(root_dir, 'templates'),
           static_folder=os.path.join(root_dir, 'static'),
           static_url_path='')

def find_peaks_and_troughs(data, min_span=3):
    """寻找顶底分型"""
    peaks = []  # 顶分型
    troughs = []  # 底分型
    
    for i in range(min_span, len(data) - min_span):
        # 寻找顶分型
        if all(data[i] > data[i-j] for j in range(1, min_span+1)) and \
           all(data[i] > data[i+j] for j in range(1, min_span+1)):
            peaks.append(i)
        
        # 寻找底分型
        if all(data[i] < data[i-j] for j in range(1, min_span+1)) and \
           all(data[i] < data[i+j] for j in range(1, min_span+1)):
            troughs.append(i)
    
    return peaks, troughs

def find_trend_lines(highs, lows, dates, peaks, troughs):
    """寻找趋势线和通道"""
    trend_lines = []
    
    # 找出价格中枢
    price_centers = []
    for i in range(len(peaks) - 1):
        for j in range(len(troughs) - 1):
            if peaks[i] < troughs[j] < peaks[i+1]:
                center_price = (highs[peaks[i]] + lows[troughs[j]] + highs[peaks[i+1]] + lows[troughs[j+1]]) / 4
                center_start = dates[min(peaks[i], troughs[j])]
                center_end = dates[max(peaks[i+1], troughs[j+1])]
                price_centers.append({
                    'price': center_price,
                    'start': center_start,
                    'end': center_end
                })
    
    # 识别上升趋势线和下降趋势线
    if len(troughs) >= 2:
        # 上升趋势线 (连接底部)
        trend_lines.append({
            'type': 'uptrend',
            'points': [(dates[t], lows[t]) for t in troughs[:2]]
        })
    
    if len(peaks) >= 2:
        # 下降趋势线 (连接顶部)
        trend_lines.append({
            'type': 'downtrend',
            'points': [(dates[p], highs[p]) for p in peaks[:2]]
        })
    
    return trend_lines, price_centers

def chan_analysis(df_dict):
    """缠论分析"""
    # 提取数据
    dates = [item['Date'] for item in df_dict]
    closes = [item['Close'] for item in df_dict]
    highs = [item['High'] for item in df_dict]
    lows = [item['Low'] for item in df_dict]
    
    # 寻找顶底分型
    peaks, troughs = find_peaks_and_troughs(closes)
    
    # 识别趋势线和中枢
    trend_lines, price_centers = find_trend_lines(highs, lows, dates, peaks, troughs)
    
    # 构建分析结果
    analysis_result = {
        'peaks': [{'index': p, 'date': dates[p], 'price': closes[p]} for p in peaks],
        'troughs': [{'index': t, 'date': dates[t], 'price': closes[t]} for t in troughs],
        'trend_lines': trend_lines,
        'price_centers': price_centers
    }
    
    return analysis_result

def get_stock_data(stock_code, start_date, end_date):
    """获取股票数据"""
    try:
        print(f"正在获取股票数据: {stock_code}")
        
        try:
            # 判断股票市场
            if stock_code.startswith('6'):
                market = 'sh'
            elif stock_code.startswith(('0', '3')):
                market = 'sz'
            else:
                market = None
                
            if market:
                # 获取A股数据
                print(f"获取A股数据: {market}{stock_code}")
                try:
                    # 尝试使用新接口获取数据
                    df = ak.stock_zh_a_hist(symbol=f"{market}{stock_code}", 
                                          period="daily",
                                          start_date=start_date.replace('-', ''),
                                          end_date=end_date.replace('-', ''),
                                          adjust="qfq")  # 使用前复权数据
                    
                    if df is None or df.empty:
                        raise Exception("数据获取失败")
                        
                except Exception as e1:
                    print(f"新接口获取失败: {str(e1)}")
                    # 尝试使用备用接口
                    df = ak.stock_zh_a_daily(symbol=f"{market}{stock_code}", 
                                           start_date=start_date.replace('-', ''),
                                           end_date=end_date.replace('-', ''),
                                           adjust="qfq")  # 使用前复权数据
                
                # 获取股票名称
                try:
                    stock_info = ak.stock_info_a_code_name()
                    stock_info_filtered = stock_info[stock_info['code'] == stock_code]
                    if not stock_info_filtered.empty:
                        stock_name = stock_info_filtered.iloc[0]['name']
                    else:
                        stock_name = stock_code
                    print(f"获取到股票名称: {stock_name}")
                except Exception as e:
                    print(f"获取股票名称失败: {str(e)}")
                    stock_name = stock_code
            else:
                # 获取美股数据
                print(f"获取美股数据: {stock_code}")
                try:
                    # 尝试使用新接口
                    df = ak.stock_us_daily(symbol=stock_code)
                    if df is not None and not df.empty:
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                except Exception as e1:
                    print(f"美股数据获取失败: {str(e1)}")
                    # 尝试使用备用接口
                    df = ak.stock_us_hist(symbol=stock_code,
                                        start_date=start_date.replace('-', ''),
                                        end_date=end_date.replace('-', ''))
                stock_name = stock_code
            
            if df is None or df.empty:
                raise Exception(f"未找到股票 {stock_code} 的交易数据")
            
            # 确保数据按日期排序
            date_col = '日期' if '日期' in df.columns else 'date'
            df = df.sort_values(by=date_col)
            
            # 转换数据格式
            df_dict = []
            if '日期' in df.columns:  # A股数据
                df_records = df.to_dict('records')
                for row in df_records:
                    df_dict.append({
                        'Date': pd.to_datetime(row['日期']).strftime('%Y-%m-%d'),
                        'Open': float(row['开盘']),
                        'High': float(row['最高']),
                        'Low': float(row['最低']),
                        'Close': float(row['收盘']),
                        'Volume': float(row['成交量'])
                    })
            else:  # 美股数据
                df_records = df.to_dict('records')
                for row in df_records:
                    df_dict.append({
                        'Date': pd.to_datetime(row['date']).strftime('%Y-%m-%d'),
                        'Open': float(row['open']),
                        'High': float(row['high']),
                        'Low': float(row['low']),
                        'Close': float(row['close']),
                        'Volume': float(row['volume'])
                    })
            
            # 进行缠论分析
            chan_result = chan_analysis(df_dict)
                
            print(f"成功获取股票数据: {stock_name}, 共 {len(df_dict)} 条记录")
            return df_dict, stock_name, chan_result
            
        except Exception as e:
            print(f"获取股票数据失败: {str(e)}")
            raise Exception(f"获取股票数据失败: {str(e)}")
            
    except Exception as e:
        print(f"处理请求失败: {str(e)}")
        raise Exception(f"处理请求失败: {str(e)}")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """分析股票数据"""
    try:
        stock_code = request.form.get('stock_code', '').strip()
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        
        if not all([stock_code, start_date, end_date]):
            return jsonify({'error': "请填写完整的查询信息"}), 400
            
        # 获取股票数据
        data, stock_name, chan_result = get_stock_data(stock_code, start_date, end_date)
        
        # 准备返回数据
        response_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'data': data,
            'chan_analysis': chan_result
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080) 