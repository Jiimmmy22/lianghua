# 股票市场缠论分析系统

## 项目简介

本项目是一个基于缠论理论的股票市场分析系统，提供了完整的缠论分析功能，包括K线预处理、分型识别、笔的划分、线段的划分、中枢的识别等。系统同时支持A股、港股和美股的数据获取和分析。

## 功能特点

- **全市场数据支持**：同时支持A股、港股、美股的数据获取
- **完整的缠论分析流程**：
  - K线预处理和包含关系处理
  - 顶底分型识别
  - 笔的划分（基于邢不行方法）
  - 线段的划分（基于邢不行方法）
  - 中枢的识别和划分
- **可视化分析**：提供K线、分型、笔、线段、中枢的可视化展示
- **Web应用界面**：通过Flask实现的Web应用，方便用户查询和分析

## 安装说明

1. 克隆项目到本地
```bash
git clone <项目地址>
cd <项目目录>
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动Web应用
```bash
python app.py
```

## 使用方法

### Web应用

访问 `http://localhost:8087`（或配置的其他端口）即可使用Web界面：

1. 输入股票代码（A股6位数字，港股4-5位数字，美股股票代码）
2. 选择开始和结束日期
3. 点击"分析"按钮获取结果

### Python API

也可以直接在Python中调用分析库：

```python
from chanlib import preprocess_kline, find_fractal_point, find_strokes, find_segments, find_hubs

# 获取股票数据（可以使用自己的数据源）
df = get_stock_data('601318', '2023-01-01', '2023-12-31')

# 设置日期为索引
df = df.set_index('date')

# 1. K线预处理
processed_df = preprocess_kline(df)

# 2. 分型识别
fractal_df = find_fractal_point(processed_df)

# 3. 笔的划分
stroke_df = find_strokes(fractal_df)

# 4. 线段的划分
segment_df = find_segments(stroke_df)

# 5. 中枢识别
hubs_df = find_hubs(segment_df)

# 可视化分析结果
plot_chan_analysis(df, segment_df, hubs_df, "缠论分析")
```

### 示例脚本

项目包含示例脚本，展示如何使用缠论分析库：

```bash
python examples/chan_analysis_example.py 601318 2023-01-01 2023-12-31
```

## 缠论理论简介

缠论（缠中说禅技术分析理论）是由"缠中说禅"博主创立的一套独特的股票市场分析方法。其核心概念包括：

1. **分型**：K线形态的顶分型和底分型识别
2. **笔**：连接相邻的顶底分型形成的线段
3. **线段**：由多个笔组成的趋势段落
4. **中枢**：三笔重叠区间形成的波动中心

本项目实现了缠论的核心算法，并提供了直观的可视化展示。

## 贡献者

[您的名字]

## 许可证

MIT 