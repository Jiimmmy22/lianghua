from flask import Flask, request, jsonify, render_template
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__, template_folder='../templates', static_folder='../static')

def get_stock_data(stock_code, start_date, end_date):
    """获取股票数据"""
    try:
        # 添加市场后缀
        if len(stock_code) == 6 and stock_code.isdigit():
            if stock_code.startswith('6'):
                stock_code += '.SS'  # 上证
            else:
                stock_code += '.SZ'  # 深证
        
        # 获取数据
        stock = yf.Ticker(stock_code)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            raise Exception("未找到股票数据")
            
        return df, stock.info.get('longName', stock_code)
    except Exception as e:
        raise Exception(f"获取股票数据失败: {str(e)}")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """分析股票数据"""
    try:
        stock_code = request.form.get('stock_code', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        
        if not all([stock_code, start_date, end_date]):
            raise ValueError("请填写完整的查询信息")
            
        # 获取股票数据
        df, stock_name = get_stock_data(stock_code, start_date, end_date)
        
        # 创建图表
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['Close'], label='收盘价')
        plt.title(f"{stock_name} ({stock_code})")
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.legend()
        plt.grid(True)
        
        # 转换图表为base64
        img = BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode()
        plt.close()
        
        # 准备数据
        data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'chart': img_base64,
            'data': df.tail().to_dict('records')
        }
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True) 