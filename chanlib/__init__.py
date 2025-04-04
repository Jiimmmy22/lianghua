"""
缠论分析库
包含预处理、分型、笔段、线段等功能
"""

from .preprocess import preprocess_kline
from .fractal import find_fractal_point
from .stroke import find_strokes
from .segment import find_segments
from .hub import find_hubs
from .analyzer import analyze_chan, plot_chan_analysis
from .signals import add_trading_signals, identify_buy_signals, identify_sell_signals 