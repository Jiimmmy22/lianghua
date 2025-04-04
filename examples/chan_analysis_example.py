#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
缠论分析示例
展示如何使用chanlib库分析股票数据
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import akshare as ak
import yfinance as yf

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入缠论分析库
from chanlib import preprocess_kline, find_fractal_point, find_strokes, find_segments, find_hubs, add_trading_signals

def get_stock_data(stock_code, start_date, end_date):
    """获取股票数据"""
    # A股
    if stock_code.isdigit() and len(stock_code) == 6:
        try:
            if stock_code.startswith('0') or stock_code.startswith('3'):
                stock_code = 'sz' + stock_code
            else:
                stock_code = 'sh' + stock_code
                
            df = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, end_date=end_date, adjust="qfq")
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'change_pct', 'change', 'turnover']
            return df
            
        except Exception as e:
            print(f"获取A股数据出错: {e}")
            return pd.DataFrame()
    
    # 港股
    elif (stock_code.isdigit() and len(stock_code) <= 5) or (len(stock_code) <= 5 and stock_code.startswith('0')):
        try:
            if len(stock_code) < 5:
                stock_code = stock_code.zfill(5)
                
            df = ak.stock_hk_daily(symbol=stock_code, adjust="qfq")
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            df = df.reset_index()
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct']
            return df
            
        except Exception as e:
            print(f"获取港股数据出错: {e}")
            return pd.DataFrame()
    
    # 美股
    elif not stock_code.isdigit():
        try:
            stock = yf.Ticker(stock_code)
            df = stock.history(start=start_date, end=end_date)
            df = df.reset_index()
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']
            return df
            
        except Exception as e:
            print(f"获取美股数据出错: {e}")
            return pd.DataFrame()
    
    # 指数
    elif stock_code.startswith('i') and stock_code[1:].isdigit():
        try:
            index_code = stock_code[1:]
            if index_code.startswith('0') or index_code.startswith('3'):
                index_code = 'sz' + index_code
            else:
                index_code = 'sh' + index_code
                
            df = ak.stock_zh_index_daily(symbol=index_code)
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            df = df.reset_index(drop=True)
            return df
            
        except Exception as e:
            print(f"获取指数数据出错: {e}")
            return pd.DataFrame()
    
    # 行情数据（如ETF等）
    elif stock_code.startswith('e') and stock_code[1:].isdigit():
        try:
            etf_code = stock_code[1:]
            if etf_code.startswith('1') or etf_code.startswith('5'):
                etf_code = 'sh' + etf_code
            else:
                etf_code = 'sz' + etf_code
                
            df = ak.fund_etf_hist_em(symbol=etf_code, start_date=start_date, end_date=end_date, adjust="qfq")
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'change_pct', 'change', 'turnover']
            return df
            
        except Exception as e:
            print(f"获取ETF数据出错: {e}")
            return pd.DataFrame()
    
    else:
        print(f"不支持的股票代码格式: {stock_code}")
        return pd.DataFrame()

def plot_chan_analysis(original_df, chan_df, hubs_df=None, title=None):
    """绘制缠论分析结果"""
    if chan_df.empty:
        print("没有分析数据可供绘制")
        return
    
    # 创建图形
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(15, 10))
    
    # 设置主图和成交量图的高度比例
    gs = plt.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
    
    # 主图 - K线和分析结果
    ax1 = plt.subplot(gs[0])
    ax2 = plt.subplot(gs[1])  # 成交量
    ax3 = plt.subplot(gs[2])  # 买入信号
    ax4 = plt.subplot(gs[3])  # 卖出信号
    
    # 在主图上绘制K线
    for i in range(len(original_df)):
        # 绘制K线
        open_price = original_df['open'].iloc[i]
        close_price = original_df['close'].iloc[i]
        high_price = original_df['high'].iloc[i]
        low_price = original_df['low'].iloc[i]
        
        # 计算K线宽度
        if len(original_df) > 100:
            width = 0.6
        else:
            width = 0.8
            
        # 根据开盘收盘价格决定K线颜色
        if close_price >= open_price:
            color = 'red'
            ax1.add_patch(plt.Rectangle((i-width/2, open_price), width, close_price-open_price, 
                                    fill=True, color=color, alpha=0.6))
        else:
            color = 'green'
            ax1.add_patch(plt.Rectangle((i-width/2, close_price), width, open_price-close_price, 
                                    fill=True, color=color, alpha=0.6))
            
        # 绘制上下影线
        ax1.plot([i, i], [low_price, high_price], color='black', linewidth=1)
    
    # 绘制分型点
    if 'fractal_type' in chan_df.columns:
        top_idx = chan_df[chan_df['fractal_type'] == 'top'].index
        bottom_idx = chan_df[chan_df['fractal_type'] == 'bottom'].index
        
        for idx in top_idx:
            if idx in original_df.index:
                pos = original_df.index.get_loc(idx)
                high = original_df['high'].iloc[pos]
                ax1.scatter(pos, high, color='blue', marker='v', s=50)
                
        for idx in bottom_idx:
            if idx in original_df.index:
                pos = original_df.index.get_loc(idx)
                low = original_df['low'].iloc[pos]
                ax1.scatter(pos, low, color='blue', marker='^', s=50)
    
    # 绘制笔
    if 'stroke_mark' in chan_df.columns:
        stroke_points = chan_df[chan_df['stroke_mark'] == True]
        # 至少需要两个点才能绘制线段
        if len(stroke_points) >= 2:
            x_coords = []
            y_coords = []
            for idx in stroke_points.index:
                if idx in original_df.index:
                    pos = original_df.index.get_loc(idx)
                    x_coords.append(pos)
                    if 'stroke_type' in stroke_points.columns and stroke_points.loc[idx, 'stroke_type'] == 'top':
                        y_coords.append(original_df['high'].iloc[pos])
                    else:
                        y_coords.append(original_df['low'].iloc[pos])
            
            ax1.plot(x_coords, y_coords, 'g-', linewidth=1.5, label='笔')
            
            # 标记笔端点
            for i in range(len(x_coords)):
                ax1.scatter(x_coords[i], y_coords[i], color='g', marker='o', s=50)
    
    # 绘制线段
    if 'segment_mark' in chan_df.columns:
        segment_points = chan_df[chan_df['segment_mark'] == True]
        # 至少需要两个点才能绘制线段
        if len(segment_points) >= 2:
            x_coords = []
            y_coords = []
            for idx in segment_points.index:
                if idx in original_df.index:
                    pos = original_df.index.get_loc(idx)
                    x_coords.append(pos)
                    if 'segment_type' in segment_points.columns and segment_points.loc[idx, 'segment_type'] == 'top':
                        y_coords.append(original_df['high'].iloc[pos])
                    else:
                        y_coords.append(original_df['low'].iloc[pos])
            
            ax1.plot(x_coords, y_coords, 'b-', linewidth=2, label='线段')
            
            # 标记线段端点
            for i in range(len(x_coords)):
                ax1.scatter(x_coords[i], y_coords[i], color='b', marker='s', s=60)
    
    # 绘制中枢
    if hubs_df is not None and not hubs_df.empty:
        for i, hub in hubs_df.iterrows():
            # 获取中枢的起始和结束位置在原始数据中的索引
            start_pos = original_df.index.get_loc(hub['start_idx']) if hub['start_idx'] in original_df.index else 0
            end_pos = original_df.index.get_loc(hub['end_idx']) if hub['end_idx'] in original_df.index else len(original_df)-1
            
            # 绘制中枢范围矩形
            ax1.add_patch(plt.Rectangle((start_pos, hub['low']), end_pos-start_pos, hub['high']-hub['low'], 
                                    fill=True, alpha=0.2, color='purple'))
            
            # 标记中枢区间
            ax1.plot([start_pos, end_pos], [hub['high'], hub['high']], 'purple', linestyle='--', linewidth=1)
            ax1.plot([start_pos, end_pos], [hub['low'], hub['low']], 'purple', linestyle='--', linewidth=1)
    
    # 绘制成交量
    if 'volume' in original_df.columns:
        for i in range(len(original_df)):
            open_price = original_df['open'].iloc[i]
            close_price = original_df['close'].iloc[i]
            volume = original_df['volume'].iloc[i]
            
            # 计算宽度
            if len(original_df) > 100:
                width = 0.6
            else:
                width = 0.8
                
            # 根据开盘收盘价格决定成交量柱状图颜色
            if close_price >= open_price:
                color = 'red'
            else:
                color = 'green'
                
            ax2.bar(i, volume, width=width, color=color, alpha=0.6)
    
    # 绘制买入信号
    if 'buy_signal' in chan_df.columns:
        buy_signals = chan_df[chan_df['buy_signal'] > 0]
        for idx in buy_signals.index:
            if idx in original_df.index:
                pos = original_df.index.get_loc(idx)
                signal_type = buy_signals.loc[idx, 'buy_signal']
                
                # 绘制买入信号
                if signal_type == 1:
                    signal_name = "底分型买入"
                elif signal_type == 2:
                    signal_name = "线段底部买入"
                elif signal_type == 3:
                    signal_name = "中枢突破买入"
                else:
                    signal_name = "买入信号"
                
                ax3.bar(pos, 1, color='red', alpha=0.7)
                ax3.text(pos, 1.1, signal_name, rotation=90, fontsize=8)
    
    # 绘制卖出信号
    if 'sell_signal' in chan_df.columns:
        sell_signals = chan_df[chan_df['sell_signal'] > 0]
        for idx in sell_signals.index:
            if idx in original_df.index:
                pos = original_df.index.get_loc(idx)
                signal_type = sell_signals.loc[idx, 'sell_signal']
                
                # 绘制卖出信号
                if signal_type == 1:
                    signal_name = "顶分型卖出"
                elif signal_type == 2:
                    signal_name = "线段顶部卖出"
                elif signal_type == 3:
                    signal_name = "中枢跌破卖出"
                else:
                    signal_name = "卖出信号"
                
                ax4.bar(pos, 1, color='green', alpha=0.7)
                ax4.text(pos, 1.1, signal_name, rotation=90, fontsize=8)
    
    # 设置图表样式
    ax1.set_ylabel('价格')
    ax1.set_xlim(0, len(original_df)-1)
    ax1.legend(loc='best')
    
    ax2.set_ylabel('成交量')
    ax2.set_xlim(0, len(original_df)-1)
    
    ax3.set_ylabel('买入信号')
    ax3.set_xlim(0, len(original_df)-1)
    ax3.set_ylim(0, 2)
    ax3.set_yticks([])
    
    ax4.set_ylabel('卖出信号')
    ax4.set_xlim(0, len(original_df)-1)
    ax4.set_ylim(0, 2)
    ax4.set_yticks([])
    
    # 设置x轴刻度和标签
    x_ticks = np.linspace(0, len(original_df)-1, min(10, len(original_df)))
    x_labels = [original_df['date'].iloc[int(i)] for i in x_ticks]
    
    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, rotation=45)
    
    # 图表标题
    if title:
        plt.suptitle(title, fontsize=16)
    else:
        plt.suptitle('缠论分析', fontsize=16)
    
    plt.tight_layout()
    plt.show()

def run_analysis(stock_code, start_date, end_date):
    """运行缠论分析"""
    print(f"开始分析股票: {stock_code}, 日期范围: {start_date} - {end_date}")
    
    # 获取股票数据
    df = get_stock_data(stock_code, start_date, end_date)
    
    if df.empty:
        print("未获取到股票数据")
        return
    
    print(f"获取到 {len(df)} 条数据")
    
    # 保存原始数据副本
    original_df = df.copy()
    
    # 1. K线预处理 - 处理包含关系
    processed_df = preprocess_kline(df)
    print("K线预处理完成")
    
    # 2. 分型判断
    fractal_df = find_fractal_point(processed_df)
    print(f"找到 {len(fractal_df[fractal_df['fractal_type'] == 'top'])} 个顶分型，{len(fractal_df[fractal_df['fractal_type'] == 'bottom'])} 个底分型")
    
    # 3. 笔的划分
    stroke_df = find_strokes(fractal_df)
    print(f"找到 {len(stroke_df[stroke_df['stroke_mark'] == True])} 个笔端点")
    
    # 4. 线段的划分
    segment_df = find_segments(stroke_df)
    print(f"找到 {len(segment_df[segment_df['segment_mark'] == True])} 个线段端点")
    
    # 5. 中枢识别
    hub_df = find_hubs(segment_df)
    hubs_count = len(hub_df) if 'hub_df' in locals() and hub_df is not None else 0
    print(f"找到 {hubs_count} 个中枢")
    
    # 6. 添加买卖信号
    final_df = add_trading_signals(hub_df)
    buy_signals = len(final_df[final_df['buy_signal'] > 0])
    sell_signals = len(final_df[final_df['sell_signal'] > 0])
    print(f"找到 {buy_signals} 个买入信号, {sell_signals} 个卖出信号")
    
    # 绘制分析结果
    plot_chan_analysis(original_df, final_df, hub_df, f"{stock_code} 缠论分析")
    
    return final_df, hub_df

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        stock_code = sys.argv[1]
        start_date = sys.argv[2]
        end_date = sys.argv[3]
    else:
        # 默认值
        stock_code = '601318'  # 中国平安
        start_date = '2023-01-01'
        end_date = '2023-12-31'
    
    # 运行分析
    run_analysis(stock_code, start_date, end_date)
    
    # 示例: 分析指数
    if len(sys.argv) <= 1:
        print("\n分析上证指数:")
        run_analysis('i000001', '2023-01-01', '2023-06-30')
        
        # 分析ETF
        print("\n分析上证50ETF:")
        run_analysis('e510050', '2023-01-01', '2023-06-30') 