"""
缠论分析入口模块
集成所有缠论功能
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

from .preprocess import preprocess_kline
from .fractal import find_fractal_point
from .stroke import find_strokes
from .segment import find_segments
from .hub import find_hubs
from .signals import add_trading_signals

def analyze_chan(df, add_signals=True):
    """
    执行缠论分析
    
    Args:
        df: DataFrame，至少包含 open, high, low, close 四列的股价数据
        add_signals: bool，是否添加买卖信号，默认为True
        
    Returns:
        processed_df: 经过缠论分析的DataFrame，添加了各种标记
    """
    # 检查必要的列
    required_columns = ['open', 'high', 'low', 'close']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"输入数据必须包含列: {col}")
    
    # 1. K线预处理
    processed_df = preprocess_kline(df)
    
    # 2. 分型
    processed_df = find_fractal_point(processed_df)
    
    # 3. 划分笔
    processed_df = find_strokes(processed_df)
    
    # 4. 划分线段
    processed_df = find_segments(processed_df)
    
    # 5. 识别中枢
    processed_df = find_hubs(processed_df)
    
    # 6. 添加买卖信号（如果需要）
    if add_signals:
        try:
            from chanlib.signals import add_trading_signals
            processed_df = add_trading_signals(processed_df)
        except Exception as e:
            print(f"添加买卖信号时出错: {str(e)}")
    
    return processed_df

def plot_chan_analysis(df, hubs_df=None):
    """
    绘制缠论分析图
    
    参数:
        df: DataFrame, 包含缠论分析结果的K线数据
        hubs_df: DataFrame, 中枢数据
        
    返回:
        图表的二进制数据
    """
    if df.empty:
        return None
    
    # 准备绘图
    plt.figure(figsize=(14, 8))
    
    # 确保我们使用预处理后的数据
    date_col = 'date' if isinstance(df.index[0], int) else df.index
    high_col = 'processed_high' if 'processed_high' in df.columns else 'high'
    low_col = 'processed_low' if 'processed_low' in df.columns else 'low'
    
    # 绘制K线
    plt.plot(date_col, df[high_col], color='black', alpha=0.3, linewidth=1)
    plt.plot(date_col, df[low_col], color='black', alpha=0.3, linewidth=1)
    
    # 绘制顶底分型
    if 'fractal_type' in df.columns:
        tops = df[df['fractal_type'] == 'top']
        bottoms = df[df['fractal_type'] == 'bottom']
        
        plt.scatter(tops.index, tops[high_col], color='red', marker='^', s=50, label='顶分型')
        plt.scatter(bottoms.index, bottoms[low_col], color='green', marker='v', s=50, label='底分型')
    
    # 绘制笔
    if 'stroke_mark' in df.columns and 'stroke_type' in df.columns:
        stroke_points = df[df['stroke_mark'] == True]
        
        for i in range(1, len(stroke_points)):
            p1 = stroke_points.iloc[i-1]
            p2 = stroke_points.iloc[i]
            
            # 根据笔的类型选择颜色
            color = 'red' if p1['stroke_type'] == 'up' else 'green'
            
            p1_x = stroke_points.index[i-1]
            p2_x = stroke_points.index[i]
            
            # 绘制笔的连线
            if p1['stroke_type'] == 'up':
                plt.plot([p1_x, p2_x], [p1[low_col], p2[high_col]], color=color, linewidth=1.5)
            else:
                plt.plot([p1_x, p2_x], [p1[high_col], p2[low_col]], color=color, linewidth=1.5)
    
    # 绘制线段
    if 'segment_mark' in df.columns and 'segment_type' in df.columns:
        segment_points = df[df['segment_mark'] == True]
        
        for i in range(1, len(segment_points)):
            p1 = segment_points.iloc[i-1]
            p2 = segment_points.iloc[i]
            
            # 根据线段的类型选择颜色
            color = 'red' if p1['segment_type'] == 'up' else 'green'
            
            p1_x = segment_points.index[i-1]
            p2_x = segment_points.index[i]
            
            # 绘制线段的连线
            if p1['segment_type'] == 'up':
                plt.plot([p1_x, p2_x], [p1[low_col], p2[high_col]], color=color, linewidth=2.5)
            else:
                plt.plot([p1_x, p2_x], [p1[high_col], p2[low_col]], color=color, linewidth=2.5)
    
    # 绘制中枢
    if hubs_df is not None and not hubs_df.empty:
        for _, hub in hubs_df.iterrows():
            # 绘制中枢范围
            start_idx = df.index.get_loc(hub['start_date']) if hub['start_date'] in df.index else 0
            end_idx = df.index.get_loc(hub['end_date']) if hub['end_date'] in df.index else len(df) - 1
            
            x_start = df.index[start_idx]
            x_end = df.index[end_idx]
            
            # 中枢区域
            plt.fill_between([x_start, x_end], hub['low'], hub['high'], color='lightblue', alpha=0.3)
            
            # 中枢中轴线
            plt.hlines(y=hub['mid'], xmin=x_start, xmax=x_end, colors='blue', linestyles='dashed')
    
    # 设置图表
    plt.title('缠论分析图')
    plt.ylabel('价格')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 优化X轴刻度
    plt.xticks(rotation=45)
    if isinstance(df.index[0], pd.Timestamp):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    
    plt.tight_layout()
    
    # 将图表保存到内存
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer 