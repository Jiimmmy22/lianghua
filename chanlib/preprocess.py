"""
K线预处理模块
包含K线合并、包含关系处理等功能
"""

import pandas as pd
import numpy as np

def preprocess_kline(df, include_method='high_low'):
    """
    K线预处理，处理包含关系
    
    参数:
        df: DataFrame, 包含OHLC数据的DataFrame
        include_method: str, 包含关系处理方法，可选'high_low'或'close'
        
    返回:
        处理后的DataFrame
    """
    if df.empty:
        return df
    
    # 确保列名标准化
    required_cols = ['open', 'high', 'low', 'close']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"输入数据缺少必要的列: {col}")
    
    # 复制数据，避免修改原始数据
    result_df = df.copy()
    
    # 确保数据按日期排序
    if 'date' in result_df.columns:
        result_df = result_df.sort_values('date')
    else:
        if isinstance(result_df.index, pd.DatetimeIndex):
            result_df = result_df.sort_index()
        else:
            # 如果没有date列也没有日期索引，尝试按索引排序
            result_df = result_df.sort_index()
    
    # 创建新列用于存储处理后的值
    result_df['processed_open'] = result_df['open']
    result_df['processed_high'] = result_df['high']
    result_df['processed_low'] = result_df['low']
    result_df['processed_close'] = result_df['close']
    
    # 处理包含关系
    for i in range(1, len(result_df)):
        current = result_df.iloc[i]
        prev = result_df.iloc[i-1]
        
        # 判断是否有包含关系
        is_include = (current['processed_high'] >= prev['processed_high'] and 
                     current['processed_low'] <= prev['processed_low']) or \
                     (current['processed_high'] <= prev['processed_high'] and 
                     current['processed_low'] >= prev['processed_low'])
                     
        if is_include:
            # 处理包含关系
            if include_method == 'high_low':
                # 向上趋势，取高点高值、低点高值
                if current['processed_close'] > prev['processed_close']:
                    high = max(current['processed_high'], prev['processed_high'])
                    low = max(current['processed_low'], prev['processed_low'])
                # 向下趋势，取低点低值、高点低值
                else:
                    high = min(current['processed_high'], prev['processed_high'])
                    low = min(current['processed_low'], prev['processed_low'])
            else:  # 'close'方法
                # 简单取极值
                high = max(current['processed_high'], prev['processed_high'])
                low = min(current['processed_low'], prev['processed_low'])
            
            # 更新当前K线
            result_df.at[result_df.index[i], 'processed_high'] = high
            result_df.at[result_df.index[i], 'processed_low'] = low
            
            # 开盘价和收盘价取前一个K线的值
            result_df.at[result_df.index[i], 'processed_open'] = prev['processed_open']
            result_df.at[result_df.index[i], 'processed_close'] = prev['processed_close']
    
    return result_df 