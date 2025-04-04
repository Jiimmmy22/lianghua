import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数

# 测试时间段，可根据数据时间更改
start_time = '20220731'
end_time = '20231030'
# 读取预处理K线数据
df = pd.read_csv('数据文件1 预处理K线.csv', encoding='gbk', parse_dates=['candle_end_time'])
# 顶分型和底分型的条件
con1 = df['high'].shift(1) > df['high']
con2 = df['high'].shift(1) > df['high'].shift(2)
con3 = df['low'].shift(1) < df['low']
con4 = df['low'].shift(1) < df['low'].shift(2)

# 标记顶分型和底分型
df.loc[con1 & con2, 'type'] = '顶分型信号确认'
df.loc[con3 & con4, 'type'] = '底分型信号确认'
df.loc[con1 & con2, 'signal'] = 1
df.loc[con3 & con4, 'signal'] = 0
df.loc[df['type'].shift(-1) == '顶分型信号确认', '分型点'] = '顶分型顶点'
df.loc[df['type'].shift(-1) == '底分型信号确认', '分型点'] = '底分型底点'

df.to_csv('数据文件2 顶底分型.csv', encoding='gbk')

# 选择画图的时间范围
df = df[df['candle_end_time'] >= pd.to_datetime(start_time)]
df = df[df['candle_end_time'] <= pd.to_datetime(end_time)]

# 创建图表
fig, ax = plt.subplots(figsize=(14, 7), dpi=100)
fig.set_facecolor('grey')
ax.grid(False)  # 关闭网格
# 更改轴背景颜色为灰色
ax.set_facecolor('grey')

# 设置轴边框为白色
ax.spines['top'].set_edgecolor('white')
ax.spines['bottom'].set_edgecolor('white')
ax.spines['left'].set_edgecolor('white')
ax.spines['right'].set_edgecolor('white')

# 设置刻度标记的颜色
ax.tick_params(axis='x', colors='white')  # 设置x轴刻度标记颜色为白色
ax.tick_params(axis='y', colors='white')  # 设置y轴刻度标记颜色为白色

# 绘制K线
for index, row in df.iterrows():
    plt.plot([row['candle_end_time'], row['candle_end_time']], [row['low'], row['high']], color='white', linewidth=1)

# 标注顶分型
tops = df[df['分型点'] == '顶分型顶点']
plt.scatter(tops['candle_end_time'], tops['high'], color='red', marker='s', label='Top')

# 标注底分型
bottoms = df[df['分型点'] == '底分型底点']
plt.scatter(bottoms['candle_end_time'], bottoms['low'], color='green', marker='^', label='Bottom')



# 设置日期格式化
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))

# 设置图表标题和轴标签
plt.xlabel('Date')
plt.ylabel('Price')
plt.xticks(rotation=0, color='white', fontsize=12)  # 设置x轴刻度标签颜色和大小
plt.yticks(color='white', fontsize=12)  # 设置y轴刻度标签颜色和大小
plt.xlabel('Date', color='white', fontsize=12)  # 设置x轴标签颜色和大小
plt.ylabel('Price', color='white', fontsize=12)  # 设置y轴标签颜色和大小
plt.legend()
plt.savefig('图片2 顶底分型.png', dpi=100, bbox_inches='tight', pad_inches=0.1)
plt.show()
