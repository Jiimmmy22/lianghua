"""
线段划分模块
实现缠论的线段划分，基于邢不行的缠论方法
"""

import pandas as pd
import numpy as np

def check_line_segment_break(df, stroke_points, start_idx, end_idx, direction):
    """
    检查线段是否被破坏
    
    参数:
        df: DataFrame, K线数据
        stroke_points: DataFrame, 笔的端点数据
        start_idx: int, 起始笔在stroke_points中的索引
        end_idx: int, 结束笔在stroke_points中的索引
        direction: str, 线段方向，'up'或'down'
        
    返回:
        bool, 线段是否被破坏
    """
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 获取线段的起点和终点
    start_point = stroke_points.iloc[start_idx]
    end_point = stroke_points.iloc[end_idx]
    
    # 线段间必须至少有一笔
    if end_idx - start_idx < 2:
        return False
    
    # 检查中间的笔是否破坏了线段
    if direction == 'up':
        # 上涨线段的破坏条件：中间有笔的底点低于线段起点的底点
        start_low = df.loc[start_point.name, low_col]
        
        for i in range(start_idx + 1, end_idx):
            point = stroke_points.iloc[i]
            if df.loc[point.name, low_col] < start_low:
                # 如果有确认点，确认这种破坏
                if i + 1 < end_idx:
                    confirm_point = stroke_points.iloc[i + 1]
                    if df.loc[confirm_point.name, low_col] < start_low:
                        return True
    else:  # direction == 'down'
        # 下跌线段的破坏条件：中间有笔的顶点高于线段起点的顶点
        start_high = df.loc[start_point.name, high_col]
        
        for i in range(start_idx + 1, end_idx):
            point = stroke_points.iloc[i]
            if df.loc[point.name, high_col] > start_high:
                # 如果有确认点，确认这种破坏
                if i + 1 < end_idx:
                    confirm_point = stroke_points.iloc[i + 1]
                    if df.loc[confirm_point.name, high_col] > start_high:
                        return True
    
    return False

def check_gap_segment(df, current_point, next_point):
    """
    检查是否通过缺口形成新的线段
    
    参数:
        df: DataFrame, K线数据
        current_point: Series, 当前点
        next_point: Series, 下一个点
        
    返回:
        bool, 是否通过缺口形成新的线段
    """
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 获取两点在原始df中的索引
    current_idx = df.index.get_loc(current_point.name)
    next_idx = df.index.get_loc(next_point.name)
    
    # 避免索引超出范围
    if current_idx >= len(df) - 1 or next_idx <= 0:
        return False
    
    # 获取下一K线
    next_k = df.iloc[current_idx + 1]
    prev_k = df.iloc[next_idx - 1]
    
    # 检查是否有向上缺口
    if (next_k[low_col] > current_point[high_col] and 
        prev_k[low_col] > current_point[high_col]):
        return True
    
    # 检查是否有向下缺口
    if (next_k[high_col] < current_point[low_col] and 
        prev_k[high_col] < current_point[low_col]):
        return True
    
    return False

def find_segments(df):
    """
    寻找线段，基于邢不行的缠论方法
    
    参数:
        df: DataFrame, 带有笔标记的K线数据
        
    返回:
        带有线段标记的DataFrame
    """
    if df.empty or 'stroke_mark' not in df.columns or 'stroke_type' not in df.columns:
        return df
    
    # 确保我们使用预处理后的数据
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 复制数据帧，避免修改原始数据
    result_df = df.copy()
    
    # 筛选出所有笔的端点
    stroke_points = result_df[result_df['stroke_mark'] == True].copy()
    
    if len(stroke_points) < 3:
        return result_df
    
    # 初始化线段的标记
    result_df['segment_mark'] = False  # 是否是线段的端点
    result_df['segment_type'] = None   # 线段的类型，'up'表示上涨线段，'down'表示下跌线段
    
    # 记录线段的端点
    segment_points = []
    
    # 寻找第一个有效线段作为起点
    segment_start_idx = 0
    segment_end_idx = None
    
    # 尝试寻找第一个线段
    for i in range(len(stroke_points)-2):
        # 检查是否有第二个同向笔
        if stroke_points.iloc[i]['stroke_type'] == stroke_points.iloc[i+2]['stroke_type']:
            # 找到了同向笔，确认是否构成线段
            segment_start_idx = i
            segment_direction = stroke_points.iloc[i]['stroke_type']
            
            # 记录线段的起点
            segment_points.append((stroke_points.index[i], segment_direction))
            result_df.at[stroke_points.index[i], 'segment_mark'] = True
            result_df.at[stroke_points.index[i], 'segment_type'] = segment_direction
            
            break
    
    # 没有找到起始线段
    if segment_start_idx is None:
        return result_df
    
    # 寻找后续线段
    i = segment_start_idx
    current_direction = stroke_points.iloc[i]['stroke_type']
    
    while i < len(stroke_points) - 2:
        # 如果下一笔与当前线段方向相同，则检查是否构成新的线段
        if stroke_points.iloc[i+1]['stroke_type'] == current_direction:
            # 同向，检查是否满足线段条件
            if check_line_segment_break(result_df, stroke_points, i, i+1, current_direction):
                # 满足条件，添加线段终点
                segment_points.append((stroke_points.index[i+1], current_direction))
                result_df.at[stroke_points.index[i+1], 'segment_mark'] = True
                result_df.at[stroke_points.index[i+1], 'segment_type'] = current_direction
                
                # 切换线段方向
                current_direction = 'up' if current_direction == 'down' else 'down'
                i = i + 1
            else:
                # 不满足条件，继续检查下一笔
                i = i + 1
        else:  # 不同向
            # 检查是否通过缺口破坏线段
            if check_gap_segment(result_df, stroke_points.iloc[i], stroke_points.iloc[i+1]):
                # 有缺口，形成新的线段
                segment_points.append((stroke_points.index[i+1], current_direction))
                result_df.at[stroke_points.index[i+1], 'segment_mark'] = True
                result_df.at[stroke_points.index[i+1], 'segment_type'] = current_direction
                
                # 切换线段方向
                current_direction = 'up' if current_direction == 'down' else 'down'
                i = i + 1
            else:
                # 无缺口，正常笔转向
                segment_points.append((stroke_points.index[i+1], current_direction))
                result_df.at[stroke_points.index[i+1], 'segment_mark'] = True
                result_df.at[stroke_points.index[i+1], 'segment_type'] = current_direction
                
                # 切换线段方向
                current_direction = stroke_points.iloc[i+1]['stroke_type']
                i = i + 1
    
    # 处理线段之间的中间K线标记
    for i in range(len(segment_points) - 1):
        start_point = segment_points[i][0]
        end_point = segment_points[i+1][0]
        segment_type = segment_points[i][1]
        
        start_idx = result_df.index.get_loc(start_point)
        end_idx = result_df.index.get_loc(end_point)
        
        # 对线段中间的K线进行标记
        for j in range(start_idx + 1, end_idx):
            result_df.at[result_df.index[j], 'segment_type'] = segment_type
    
    return result_df 