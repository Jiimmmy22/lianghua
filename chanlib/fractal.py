"""
分型判断模块
实现缠论的顶底分型判断
"""

import pandas as pd
import numpy as np

def find_fractal_point(df, n=3):
    """
    寻找顶底分型
    
    参数:
        df: DataFrame, 预处理后的K线数据
        n: int, 分型需要的K线数量，默认为3
        
    返回:
        带有分型标记的DataFrame
    """
    if df.empty or len(df) < n:
        return df
    
    # 确保我们使用预处理后的数据
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 复制数据帧，避免修改原始数据
    result_df = df.copy()
    result_df['fractal_type'] = None  # 分型类型，'top'表示顶分型，'bottom'表示底分型
    
    # 顶底分型判断
    for i in range(n-1, len(result_df)-(n-1)):
        # 取中间K线
        mid_idx = i
        mid_high = result_df.iloc[mid_idx][high_col]
        mid_low = result_df.iloc[mid_idx][low_col]
        
        is_top = True
        is_bottom = True
        
        # 判断是否为顶分型
        for j in range(1, n):
            # 判断左侧
            if result_df.iloc[mid_idx-j][high_col] >= mid_high:
                is_top = False
                break
            # 判断右侧
            if result_df.iloc[mid_idx+j][high_col] >= mid_high:
                is_top = False
                break
        
        # 判断是否为底分型
        for j in range(1, n):
            # 判断左侧
            if result_df.iloc[mid_idx-j][low_col] <= mid_low:
                is_bottom = False
                break
            # 判断右侧
            if result_df.iloc[mid_idx+j][low_col] <= mid_low:
                is_bottom = False
                break
        
        if is_top:
            result_df.at[result_df.index[mid_idx], 'fractal_type'] = 'top'
        elif is_bottom:
            result_df.at[result_df.index[mid_idx], 'fractal_type'] = 'bottom'
    
    return result_df 