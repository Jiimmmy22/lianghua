import yfinance as yf
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
import random
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataEnhanced:
    def __init__(self, cache_dir='./data_cache'):
        """初始化股票数据获取器
        Args:
            cache_dir: 数据缓存目录
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, symbol, start_date, end_date):
        """获取缓存文件路径"""
        cache_file = f"{symbol}_{start_date}_{end_date}.json"
        return os.path.join(self.cache_dir, cache_file)
    
    def _load_cache(self, cache_path):
        """从缓存加载数据"""
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    return pd.DataFrame(data)
            return None
        except Exception as e:
            logger.warning(f"加载缓存失败: {str(e)}")
            return None
    
    def _save_cache(self, cache_path, df):
        """保存数据到缓存"""
        try:
            data = df.to_dict('records')
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")
    
    def _format_symbol(self, symbol):
        """格式化股票代码"""
        if symbol.isdigit() and len(symbol) == 6:
            if symbol.startswith('6'):
                return f"{symbol}.SS"  # 上交所
            else:
                return f"{symbol}.SZ"  # 深交所
        elif symbol.isdigit() and len(symbol) <= 5:
            return f"{symbol}.HK"  # 港股
        return symbol
    
    def get_stock_data(self, symbol, start_date=None, end_date=None, adjust='qfq'):
        """获取股票数据
        Args:
            symbol: 股票代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            adjust: 复权方式，'qfq'前复权，'hfq'后复权，None不复权
        Returns:
            DataFrame: 股票数据
        """
        # 设置默认日期
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 格式化股票代码
        formatted_symbol = self._format_symbol(symbol)
        
        # 尝试从缓存加载
        cache_path = self._get_cache_path(formatted_symbol, start_date, end_date)
        df = self._load_cache(cache_path)
        if df is not None:
            logger.info(f"从缓存加载数据: {formatted_symbol}")
            return df
        
        # 从API获取数据
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # 创建股票对象
                stock = yf.Ticker(formatted_symbol)
                
                # 添加随机延迟
                if attempt > 0:
                    delay = base_delay * (1 + random.random())
                    logger.info(f"第{attempt+1}次尝试获取 {formatted_symbol} 数据，等待{delay:.1f}秒")
                    time.sleep(delay)
                
                # 获取历史数据
                df = stock.history(start=start_date, end=end_date, interval="1d")
                
                if df.empty:
                    raise Exception("未找到股票数据")
                
                # 重置索引并标准化列名
                df = df.reset_index()
                df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }, inplace=True)
                
                # 保存到缓存
                self._save_cache(cache_path, df)
                
                logger.info(f"成功获取数据: {formatted_symbol}")
                return df
                
            except Exception as e:
                logger.warning(f"第{attempt+1}次尝试失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) * (1 + random.random() * 0.1)
                    time.sleep(delay)
        
        raise Exception(f"在{max_retries}次尝试后仍未能获取数据")
    
    def get_multiple_stocks_data(self, symbols, start_date=None, end_date=None, adjust='qfq'):
        """批量获取多个股票的数据
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式
        Returns:
            dict: 股票代码到数据的映射
        """
        results = {}
        for symbol in symbols:
            try:
                df = self.get_stock_data(symbol, start_date, end_date, adjust)
                results[symbol] = df
            except Exception as e:
                logger.error(f"获取{symbol}数据失败: {str(e)}")
                results[symbol] = None
        return results