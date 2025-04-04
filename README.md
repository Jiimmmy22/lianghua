# 全球股票数据查询系统

基于Python Flask的全球股票数据查询和缠论分析系统。

## 功能特点

- 支持A股、港股、美股的数据查询
- 支持ETF基金数据查询
- 集成缠论分析功能
- K线图展示
- 买卖点分析
- 本地数据缓存

## 安装说明

1. 克隆仓库
```bash
git clone https://github.com/[your-username]/global-stock-analysis.git
cd global-stock-analysis
```

2. 创建虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动应用
```bash
python app.py
```

2. 打开浏览器访问
```
http://localhost:8087
```

3. 输入股票代码和日期范围进行分析

## 支持的股票代码格式

- A股代码（6位数）：如 601318
- 港股代码（5位数或更少）
- 美股代码（如AAPL）
- ETF基金：在数字前添加"e"，如e510050（上证50ETF）

## 技术栈

- Python 3.9+
- Flask
- Pandas
- yfinance
- matplotlib
- mplfinance

## 许可证

MIT License 