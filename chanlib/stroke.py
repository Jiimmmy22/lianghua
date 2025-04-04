"""
笔的划分模块
实现缠论的笔划分，基于邢不行的缠论方法
"""

import pandas as pd
import numpy as np

def verify_gap(df, point1_idx, point2_idx):
    """
    检查两点之间是否有缺口
    
    参数:
        df: DataFrame, K线数据
        point1_idx: int, 第一个点的索引
        point2_idx: int, 第二个点的索引
        
    返回:
        bool, 是否存在缺口
    """
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 获取两点
    point1 = df.iloc[point1_idx]
    point2 = df.iloc[point2_idx]
    
    # 从两点中找出高点和低点
    if point1[high_col] >= point2[high_col]:
        high_point = point1
        low_point = point2
    else:
        high_point = point2
        low_point = point1
    
    # 检查是否有缺口
    # 当低点的最高价小于高点的最低价，则存在缺口
    return low_point[high_col] < high_point[low_col]

def check_stroke_condition(df, fractal_points, idx, direction):
    """
    检查笔的有效条件
    
    参数:
        df: DataFrame, K线数据
        fractal_points: DataFrame, 分型点数据
        idx: int, 当前分型点在fractal_points中的索引
        direction: str, 笔的方向，'up'或'down'
        
    返回:
        bool, 是否满足笔的条件
    """
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 如果索引超出范围，不满足条件
    if idx < 1 or idx >= len(fractal_points):
        return False
    
    # 获取相邻的两个分型点
    curr_point = fractal_points.iloc[idx]
    prev_point = fractal_points.iloc[idx-1]
    
    # 获取两个点在原始df中的索引
    curr_idx = df.index.get_loc(curr_point.name)
    prev_idx = df.index.get_loc(prev_point.name)
    
    # 检查方向是否一致
    if direction == 'up':
        # 上涨笔应该从底分型到顶分型
        if prev_point['fractal_type'] != 'bottom' or curr_point['fractal_type'] != 'top':
            return False
        
        # 顶分型高点应该高于底分型的高点
        if curr_point[high_col] <= prev_point[high_col]:
            return False
    else:  # direction == 'down'
        # 下跌笔应该从顶分型到底分型
        if prev_point['fractal_type'] != 'top' or curr_point['fractal_type'] != 'bottom':
            return False
        
        # 底分型低点应该低于顶分型的低点
        if curr_point[low_col] >= prev_point[low_col]:
            return False
    
    # 检查中间是否有其他分型点使得本笔无效
    for i in range(prev_idx+1, curr_idx):
        k = df.iloc[i]
        
        if direction == 'up':
            # 如果中间有K线的低点低于起始底分型的低点，则笔无效
            if k[low_col] < prev_point[low_col]:
                return False
        else:  # direction == 'down'
            # 如果中间有K线的高点高于起始顶分型的高点，则笔无效
            if k[high_col] > prev_point[high_col]:
                return False
    
    # 增加新的有效性检查：相邻的两笔起点不共用一个K线
    if idx >= 2:
        prev_prev_point = fractal_points.iloc[idx-2]
        prev_prev_idx = df.index.get_loc(prev_prev_point.name)
        
        # 检查前两个分型点是否在同一K线上
        if prev_idx == prev_prev_idx:
            return False
    
    # 增加缺口检查，如果有缺口则不构成笔
    if verify_gap(df, prev_idx, curr_idx):
        # 缠论中的特例：如果有缺口，可能构成笔破坏
        return False
    
    return True

def find_strokes(df):
    """
    寻找笔，基于邢不行的缠论方法
    
    参数:
        df: DataFrame, 带有分型标记的K线数据
        
    返回:
        带有笔标记的DataFrame
    """
    if df.empty or 'fractal_type' not in df.columns:
        return df
    
    # 确保我们使用预处理后的数据
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 复制数据帧，避免修改原始数据
    result_df = df.copy()
    
    # 筛选出所有顶底分型点
    fractal_points = result_df[result_df['fractal_type'].notna()].copy()
    
    if len(fractal_points) < 2:
        return result_df
    
    # 初始化笔的标记
    result_df['stroke_mark'] = False  # 是否是笔的端点
    result_df['stroke_type'] = None   # 笔的类型，'up'表示上涨笔，'down'表示下跌笔
    
    # 记录笔的端点
    stroke_points = []
    
    # 寻找第一个有效分型点作为起点
    for i in range(len(fractal_points)-1):
        curr_point = fractal_points.iloc[i]
        next_point = fractal_points.iloc[i+1]
        
        # 检查是否构成有效的上涨笔
        if (curr_point['fractal_type'] == 'bottom' and 
            next_point['fractal_type'] == 'top' and
            check_stroke_condition(result_df, fractal_points, i+1, 'up')):
            
            # 添加第一个笔的起点和终点
            start_point = curr_point.name
            end_point = next_point.name
            
            stroke_points.append((start_point, 'bottom', 'up'))
            stroke_points.append((end_point, 'top', 'up'))
            
            result_df.at[start_point, 'stroke_mark'] = True
            result_df.at[start_point, 'stroke_type'] = 'up'
            result_df.at[end_point, 'stroke_mark'] = True
            result_df.at[end_point, 'stroke_type'] = 'up'
            
            break
            
        # 检查是否构成有效的下跌笔
        elif (curr_point['fractal_type'] == 'top' and 
              next_point['fractal_type'] == 'bottom' and
              check_stroke_condition(result_df, fractal_points, i+1, 'down')):
            
            # 添加第一个笔的起点和终点
            start_point = curr_point.name
            end_point = next_point.name
            
            stroke_points.append((start_point, 'top', 'down'))
            stroke_points.append((end_point, 'bottom', 'down'))
            
            result_df.at[start_point, 'stroke_mark'] = True
            result_df.at[start_point, 'stroke_type'] = 'down'
            result_df.at[end_point, 'stroke_mark'] = True
            result_df.at[end_point, 'stroke_type'] = 'down'
            
            break
    
    # 如果没有找到第一个有效的笔，返回原始数据
    if len(stroke_points) < 2:
        return result_df
    
    # 继续寻找后续的笔
    i = stroke_points[-1][0]  # 最后一个笔端点在df中的索引名
    i_idx = fractal_points.index.get_loc(i)  # 获取该点在fractal_points中的索引位置
    last_stroke_type = stroke_points[-1][2]  # 最后一个笔的类型
    
    # 从最后一个笔端点开始，继续寻找后续的笔
    while i_idx < len(fractal_points) - 1:
        next_idx = i_idx + 1
        
        # 如果已经到达最后，结束循环
        if next_idx >= len(fractal_points):
            break
        
        next_point = fractal_points.iloc[next_idx]
        
        # 根据上一笔的类型，确定下一笔的方向
        if last_stroke_type == 'up':
            # 上一笔向上，下一笔应该向下
            if (next_point['fractal_type'] == 'bottom' and 
                check_stroke_condition(result_df, fractal_points, next_idx, 'down')):
                
                end_point = next_point.name
                
                stroke_points.append((end_point, 'bottom', 'down'))
                
                result_df.at[end_point, 'stroke_mark'] = True
                result_df.at[end_point, 'stroke_type'] = 'down'
                
                i = end_point
                i_idx = next_idx
                last_stroke_type = 'down'
            else:
                i_idx += 1
        else:  # last_stroke_type == 'down'
            # 上一笔向下，下一笔应该向上
            if (next_point['fractal_type'] == 'top' and 
                check_stroke_condition(result_df, fractal_points, next_idx, 'up')):
                
                end_point = next_point.name
                
                stroke_points.append((end_point, 'top', 'up'))
                
                result_df.at[end_point, 'stroke_mark'] = True
                result_df.at[end_point, 'stroke_type'] = 'up'
                
                i = end_point
                i_idx = next_idx
                last_stroke_type = 'up'
            else:
                i_idx += 1
    
    # 处理笔之间的中间K线标记
    for i in range(len(stroke_points) - 1):
        start_point = stroke_points[i][0]
        end_point = stroke_points[i+1][0]
        stroke_type = stroke_points[i][2]
        
        start_idx = result_df.index.get_loc(start_point)
        end_idx = result_df.index.get_loc(end_point)
        
        # 标记中间K线
        for j in range(start_idx + 1, end_idx):
            result_df.at[result_df.index[j], 'stroke_type'] = stroke_type
    
    return result_df 