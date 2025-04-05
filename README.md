# 股票缠论分析系统

这是一个基于缠论理论的股票技术分析系统，提供了股票数据的分析和可视化功能。

## 功能特点

- 股票数据获取与处理
- 基于缠论理论的技术分析
- 识别顶底分型、笔、线段等结构
- 生成买卖信号
- 交互式图表展示
- 支持数据下载和原始图像查看

## 安装与使用

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python app.py
```

运行后，在浏览器中访问 `http://localhost:8087` 即可使用。

### 使用方法

1. 在界面上输入股票代码（如：000001、600519等）
2. 选择开始和结束日期
3. 点击"分析"按钮查看结果
4. 可以使用缩放功能或切换视图查看不同形式的图表

## 技术栈

- 后端：Flask、pandas、numpy
- 前端：JavaScript、ECharts
- 数据分析：mplfinance、ta-lib

## 许可证

MIT 