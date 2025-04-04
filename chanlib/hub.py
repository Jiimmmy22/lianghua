"""
中枢划分模块
实现缠论的中枢识别
"""

import pandas as pd
import numpy as np

def find_hubs(df):
    """
    寻找中枢
    
    参数:
        df: DataFrame, 带有线段标记的K线数据
        
    返回:
        中枢信息的DataFrame
    """
    if df.empty or 'segment_mark' not in df.columns or 'segment_type' not in df.columns:
        return pd.DataFrame()
    
    # 确保我们使用预处理后的数据
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 筛选出所有线段的端点
    segment_points = df[df['segment_mark'] == True].copy()
    
    if len(segment_points) < 4:
        return pd.DataFrame()  # 至少需要4个点才能形成中枢
    
    # 记录中枢信息
    hubs = []
    
    # 寻找中枢
    for i in range(len(segment_points) - 3):
        # 取连续的4个点
        p1 = segment_points.iloc[i]
        p2 = segment_points.iloc[i+1]
        p3 = segment_points.iloc[i+2]
        p4 = segment_points.iloc[i+3]
        
        # 计算三段的最高和最低点
        max_high = max(p1[high_col], p2[high_col], p3[high_col])
        min_low = min(p1[low_col], p2[low_col], p3[low_col])
        
        # 计算重叠区间
        overlap_high = min(max(p1[high_col], p3[high_col]), max(p2[high_col], p4[high_col]))
        overlap_low = max(min(p1[low_col], p3[low_col]), min(p2[low_col], p4[low_col]))
        
        # 确定是否形成中枢
        if overlap_high > overlap_low:
            # 计算中枢的时间范围
            start_date = p1.name if isinstance(p1.name, pd.Timestamp) else pd.to_datetime(p1.name)
            end_date = p4.name if isinstance(p4.name, pd.Timestamp) else pd.to_datetime(p4.name)
            
            # 添加中枢信息
            hubs.append({
                'start_date': start_date,
                'end_date': end_date,
                'high': overlap_high,
                'low': overlap_low,
                'mid': (overlap_high + overlap_low) / 2,
                'strength': (overlap_high - overlap_low) / ((max_high - min_low) or 1)  # 中枢强度
            })
    
    return pd.DataFrame(hubs) 