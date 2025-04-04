"""
买卖信号模块
基于缠论理论的买卖信号识别
"""

import pandas as pd
import numpy as np

def identify_buy_signals(df):
    """
    识别买入信号
    
    参数:
        df: DataFrame, 包含缠论分析结果的DataFrame
        
    返回:
        添加买入信号的DataFrame
    """
    if df.empty:
        return df
    
    # 复制数据
    result_df = df.copy()
    
    # 初始化信号列
    result_df['buy_signal'] = 0
    
    # 1. 底分型买入信号: 三根K线形成底分型
    for i in range(2, len(result_df)):
        if 'fractal_type' in result_df.columns and result_df.iloc[i-1]['fractal_type'] == 'bottom':
            result_df.at[result_df.index[i], 'buy_signal'] = 1
    
    # 2. 线段底部买入信号
    if 'segment_mark' in result_df.columns:
        segment_bottoms = result_df[(result_df['segment_mark'] == True) & 
                                   (result_df['segment_type'] == 'bottom')].index
        for idx in segment_bottoms:
            if idx in result_df.index:
                pos = result_df.index.get_loc(idx)
                if pos+1 < len(result_df):
                    result_df.at[result_df.index[pos+1], 'buy_signal'] = 2
    
    # 3. 中枢突破买入信号
    if 'in_hub' in result_df.columns and 'hub_breakthrough' not in result_df.columns:
        result_df['hub_breakthrough'] = 0
        # 找出所有中枢
        hubs = []
        current_hub = None
        for i in range(len(result_df)):
            if result_df.iloc[i]['in_hub'] > 0 and current_hub is None:
                current_hub = {
                    'start': i,
                    'hub_id': result_df.iloc[i]['in_hub'],
                    'high': result_df.iloc[i]['processed_high'],
                    'low': result_df.iloc[i]['processed_low']
                }
            elif result_df.iloc[i]['in_hub'] > 0 and current_hub is not None:
                if result_df.iloc[i]['in_hub'] == current_hub['hub_id']:
                    current_hub['high'] = max(current_hub['high'], result_df.iloc[i]['processed_high'])
                    current_hub['low'] = min(current_hub['low'], result_df.iloc[i]['processed_low'])
                else:
                    current_hub['end'] = i-1
                    hubs.append(current_hub)
                    current_hub = {
                        'start': i,
                        'hub_id': result_df.iloc[i]['in_hub'],
                        'high': result_df.iloc[i]['processed_high'],
                        'low': result_df.iloc[i]['processed_low']
                    }
            elif result_df.iloc[i]['in_hub'] == 0 and current_hub is not None:
                current_hub['end'] = i-1
                hubs.append(current_hub)
                current_hub = None
        
        # 如果最后还有一个中枢没处理完
        if current_hub is not None:
            current_hub['end'] = len(result_df)-1
            hubs.append(current_hub)
        
        # 检测中枢突破买入信号
        for hub in hubs:
            # 检查中枢后的一段时间
            check_range = min(20, len(result_df) - hub['end'] - 1)
            for i in range(1, check_range+1):
                pos = hub['end'] + i
                if pos < len(result_df):
                    # 价格突破中枢上轨
                    if (result_df.iloc[pos]['processed_high'] > hub['high'] and 
                        result_df.iloc[pos-1]['processed_high'] <= hub['high']):
                        result_df.at[result_df.index[pos], 'buy_signal'] = 3
                        result_df.at[result_df.index[pos], 'hub_breakthrough'] = 1
                        break
    
    return result_df

def identify_sell_signals(df):
    """
    识别卖出信号
    
    参数:
        df: DataFrame, 包含缠论分析结果的DataFrame
        
    返回:
        添加卖出信号的DataFrame
    """
    if df.empty:
        return df
    
    # 复制数据
    result_df = df.copy()
    
    # 初始化信号列
    result_df['sell_signal'] = 0
    
    # 1. 顶分型卖出信号: 三根K线形成顶分型
    for i in range(2, len(result_df)):
        if 'fractal_type' in result_df.columns and result_df.iloc[i-1]['fractal_type'] == 'top':
            result_df.at[result_df.index[i], 'sell_signal'] = 1
    
    # 2. 线段顶部卖出信号
    if 'segment_mark' in result_df.columns:
        segment_tops = result_df[(result_df['segment_mark'] == True) & 
                                (result_df['segment_type'] == 'top')].index
        for idx in segment_tops:
            if idx in result_df.index:
                pos = result_df.index.get_loc(idx)
                if pos+1 < len(result_df):
                    result_df.at[result_df.index[pos+1], 'sell_signal'] = 2
    
    # 3. 中枢跌破卖出信号
    if 'in_hub' in result_df.columns and 'hub_breakdown' not in result_df.columns:
        result_df['hub_breakdown'] = 0
        # 找出所有中枢
        hubs = []
        current_hub = None
        for i in range(len(result_df)):
            if result_df.iloc[i]['in_hub'] > 0 and current_hub is None:
                current_hub = {
                    'start': i,
                    'hub_id': result_df.iloc[i]['in_hub'],
                    'high': result_df.iloc[i]['processed_high'],
                    'low': result_df.iloc[i]['processed_low']
                }
            elif result_df.iloc[i]['in_hub'] > 0 and current_hub is not None:
                if result_df.iloc[i]['in_hub'] == current_hub['hub_id']:
                    current_hub['high'] = max(current_hub['high'], result_df.iloc[i]['processed_high'])
                    current_hub['low'] = min(current_hub['low'], result_df.iloc[i]['processed_low'])
                else:
                    current_hub['end'] = i-1
                    hubs.append(current_hub)
                    current_hub = {
                        'start': i,
                        'hub_id': result_df.iloc[i]['in_hub'],
                        'high': result_df.iloc[i]['processed_high'],
                        'low': result_df.iloc[i]['processed_low']
                    }
            elif result_df.iloc[i]['in_hub'] == 0 and current_hub is not None:
                current_hub['end'] = i-1
                hubs.append(current_hub)
                current_hub = None
        
        # 如果最后还有一个中枢没处理完
        if current_hub is not None:
            current_hub['end'] = len(result_df)-1
            hubs.append(current_hub)
        
        # 检测中枢跌破卖出信号
        for hub in hubs:
            # 检查中枢后的一段时间
            check_range = min(20, len(result_df) - hub['end'] - 1)
            for i in range(1, check_range+1):
                pos = hub['end'] + i
                if pos < len(result_df):
                    # 价格跌破中枢下轨
                    if (result_df.iloc[pos]['processed_low'] < hub['low'] and 
                        result_df.iloc[pos-1]['processed_low'] >= hub['low']):
                        result_df.at[result_df.index[pos], 'sell_signal'] = 3
                        result_df.at[result_df.index[pos], 'hub_breakdown'] = 1
                        break
    
    return result_df

def add_trading_signals(df):
    """
    添加买卖信号
    
    参数:
        df: DataFrame, 包含缠论分析结果的DataFrame
        
    返回:
        添加买卖信号的DataFrame
    """
    if df.empty:
        return df
    
    # 添加买入信号
    df = identify_buy_signals(df)
    
    # 添加卖出信号
    df = identify_sell_signals(df)
    
    return df 