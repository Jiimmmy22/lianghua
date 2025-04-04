"""
缠论买卖点信号识别模块

此模块根据缠论理论识别多种买卖点信号：
- 第一类买点：在下跌趋势结束时，出现底分型且背驰（如MACD柱面积缩小）
- 第二类买点：第一类买点后，价格反弹回调但不破前低，形成次低点
- 第三类买点：价格突破中枢后回调中枢上沿不破，（确认趋势延续）
- 第一类卖点：在上涨趋势结束时，出现顶分型且背驰（如MACD柱面积缩小）
- 第二类卖点：第一类卖点后，价格下跌反弹但不破前高，形成次高点
- 第三类卖点：价格跌破中枢后反抽中枢下沿不破，（确认趋势反转）
"""

import numpy as np
import pandas as pd


def identify_buy_signals(df):
    """
    识别买入信号
    
    Args:
        df: 包含分型、笔、线段和中枢数据的DataFrame
        
    Returns:
        添加了买入信号标识的DataFrame
    """
    # 确保DataFrame包含必要的列
    required_cols = ['fractal_mark', 'stroke_mark', 'segment_mark', 'hub_mark']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    
    # 初始化买入信号列
    df['buy_signal'] = 0
    
    # 创建MACD指标列（简化模拟）
    if 'close' in df.columns and 'high' in df.columns and 'low' in df.columns:
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['diff'] = ema12 - ema26
        df['dea'] = df['diff'].ewm(span=9, adjust=False).mean()
        df['macd'] = 2 * (df['diff'] - df['dea'])
    
    # 识别第一类买点：底分型且MACD背驰
    for i in range(3, len(df)):
        # 底分型
        if df.at[i-1, 'fractal_mark'] == -1:  # -1表示底分型
            # 检查MACD背驰（当前底比前一底低，但MACD柱面积较小）
            previous_bottoms = df[(df.index < i-1) & (df['fractal_mark'] == -1)]
            if not previous_bottoms.empty:
                prev_bottom_idx = previous_bottoms.index[-1]
                
                # 价格创新低但MACD不创新低（背驰）
                if (df.at[i-1, 'low'] < df.at[prev_bottom_idx, 'low']) and \
                   (abs(df.at[i-1, 'macd']) < abs(df.at[prev_bottom_idx, 'macd'])):
                    df.at[i, 'buy_signal'] = 1  # 标记第一类买点
    
    # 识别第二类买点：第一类买点后的回调不破前低形成次低点
    first_buy_indexes = df[df['buy_signal'] == 1].index
    for buy_idx in first_buy_indexes:
        if buy_idx + 5 < len(df):  # 确保有足够的后续数据
            # 寻找第一类买点后的回调形成的次低点
            for j in range(buy_idx + 3, buy_idx + 20):
                if j >= len(df):
                    break
                    
                # 检查是否为回调后的次低点（底分型，但不破前低）
                if df.at[j-1, 'fractal_mark'] == -1 and \
                   df.at[j-1, 'low'] > df.at[buy_idx-2, 'low']:
                    df.at[j, 'buy_signal'] = 2  # 标记第二类买点
                    break
    
    # 识别第三类买点：突破中枢后回调上沿不破确认趋势
    for i in range(5, len(df)):
        # 检查中枢标记
        if df.at[i-3, 'hub_mark'] > 0:  # 中枢区域
            # 确认是否突破中枢
            hub_high = df.loc[i-5:i-1, 'high'].max()  # 简化的中枢上沿
            
            # 检查突破后回调不破上沿
            if (df.at[i-5, 'high'] > hub_high) and \
               (df.at[i-1, 'low'] >= hub_high) and \
               (df.at[i-1, 'fractal_mark'] == -1):  # 回调形成底分型
                df.at[i, 'buy_signal'] = 3  # 标记第三类买点
    
    return df


def identify_sell_signals(df):
    """
    识别卖出信号
    
    Args:
        df: 包含分型、笔、线段和中枢数据的DataFrame
        
    Returns:
        添加了卖出信号标识的DataFrame
    """
    # 确保DataFrame包含必要的列
    required_cols = ['fractal_mark', 'stroke_mark', 'segment_mark', 'hub_mark']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    
    # 初始化卖出信号列
    df['sell_signal'] = 0
    
    # 创建MACD指标列（如果尚未创建）
    if 'macd' not in df.columns and 'close' in df.columns:
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['diff'] = ema12 - ema26
        df['dea'] = df['diff'].ewm(span=9, adjust=False).mean()
        df['macd'] = 2 * (df['diff'] - df['dea'])
    
    # 识别第一类卖点：顶分型且MACD背驰
    for i in range(3, len(df)):
        # 顶分型
        if df.at[i-1, 'fractal_mark'] == 1:  # 1表示顶分型
            # 检查MACD背驰（当前顶比前一顶高，但MACD柱面积较小）
            previous_tops = df[(df.index < i-1) & (df['fractal_mark'] == 1)]
            if not previous_tops.empty:
                prev_top_idx = previous_tops.index[-1]
                
                # 价格创新高但MACD不创新高（背驰）
                if (df.at[i-1, 'high'] > df.at[prev_top_idx, 'high']) and \
                   (abs(df.at[i-1, 'macd']) < abs(df.at[prev_top_idx, 'macd'])):
                    df.at[i, 'sell_signal'] = 1  # 标记第一类卖点
    
    # 识别第二类卖点：第一类卖点后的反弹不破前高形成次高点
    first_sell_indexes = df[df['sell_signal'] == 1].index
    for sell_idx in first_sell_indexes:
        if sell_idx + 5 < len(df):  # 确保有足够的后续数据
            # 寻找第一类卖点后的反弹形成的次高点
            for j in range(sell_idx + 3, sell_idx + 20):
                if j >= len(df):
                    break
                    
                # 检查是否为反弹后的次高点（顶分型，但不破前高）
                if df.at[j-1, 'fractal_mark'] == 1 and \
                   df.at[j-1, 'high'] < df.at[sell_idx-2, 'high']:
                    df.at[j, 'sell_signal'] = 2  # 标记第二类卖点
                    break
    
    # 识别第三类卖点：跌破中枢后反抽下沿不破确认趋势
    for i in range(5, len(df)):
        # 检查中枢标记
        if df.at[i-3, 'hub_mark'] > 0:  # 中枢区域
            # 确认是否跌破中枢
            hub_low = df.loc[i-5:i-1, 'low'].min()  # 简化的中枢下沿
            
            # 检查跌破后反抽不破下沿
            if (df.at[i-5, 'low'] < hub_low) and \
               (df.at[i-1, 'high'] <= hub_low) and \
               (df.at[i-1, 'fractal_mark'] == 1):  # 反抽形成顶分型
                df.at[i, 'sell_signal'] = 3  # 标记第三类卖点
    
    return df


def add_trading_signals(df):
    """
    添加买卖信号到DataFrame
    
    Args:
        df: 包含缠论分析结果的DataFrame
        
    Returns:
        添加了买卖信号的DataFrame
    """
    df = identify_buy_signals(df)
    df = identify_sell_signals(df)
    return df 