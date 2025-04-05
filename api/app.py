from flask import Flask, request, jsonify, render_template, current_app
import yfinance as yf
import pandas as pd
from datetime import datetime
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.dirname(current_dir)

app = Flask(__name__, 
    template_folder=os.path.join(root_dir, 'templates'),
    static_folder=os.path.join(root_dir, 'static'))

def get_stock_data(stock_code, start_date, end_date):
    """获取股票数据"""
    try:
        logger.info(f"开始获取股票数据: {stock_code}, {start_date} - {end_date}")
        
        # 添加市场后缀
        if len(stock_code) == 6 and stock_code.isdigit():
            if stock_code.startswith('6'):
                stock_code += '.SS'  # 上证
            else:
                stock_code += '.SZ'  # 深证
        
        logger.info(f"处理后的股票代码: {stock_code}")
        
        # 获取数据
        stock = yf.Ticker(stock_code)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            logger.warning(f"未找到股票数据: {stock_code}")
            raise Exception("未找到股票数据")
            
        # 转换数据格式
        df_dict = df.reset_index().to_dict('records')
        for record in df_dict:
            record['Date'] = record['Date'].strftime('%Y-%m-%d')
            
        stock_name = stock.info.get('longName', stock_code)
        logger.info(f"成功获取股票数据: {stock_name}")
        
        return df_dict, stock_name
    except Exception as e:
        logger.error(f"获取股票数据失败: {str(e)}")
        raise Exception(f"获取股票数据失败: {str(e)}")

@app.route('/')
def index():
    """主页"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"渲染主页失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """分析股票数据"""
    try:
        stock_code = request.form.get('stock_code', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        
        logger.info(f"收到分析请求: {stock_code}, {start_date} - {end_date}")
        
        if not all([stock_code, start_date, end_date]):
            raise ValueError("请填写完整的查询信息")
            
        # 获取股票数据
        data, stock_name = get_stock_data(stock_code, start_date, end_date)
        
        # 准备返回数据
        response_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'data': data
        }
        
        logger.info(f"分析完成: {stock_code}")
        return jsonify(response_data)
        
    except ValueError as e:
        logger.warning(f"输入验证失败: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"分析过程出错: {str(e)}")
        return jsonify({'error': '服务器内部错误，请稍后重试'}), 500

@app.errorhandler(500)
def handle_500(error):
    logger.error(f"服务器错误: {error}")
    return jsonify({'error': '服务器内部错误，请稍后重试'}), 500

@app.errorhandler(404)
def handle_404(error):
    logger.error(f"页面未找到: {error}")
    return jsonify({'error': '页面未找到'}), 404

if __name__ == '__main__':
    app.run(debug=True) 