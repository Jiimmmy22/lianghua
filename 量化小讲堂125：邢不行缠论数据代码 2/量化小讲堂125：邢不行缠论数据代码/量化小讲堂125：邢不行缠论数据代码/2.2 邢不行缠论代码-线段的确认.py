import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数


# 测试时间段，可根据数据时间更改
start_time = '20220731'
end_time = '20231030'

df = pd.read_csv('数据文件3 笔.csv', encoding='gbk')
df1 = df.copy()
df.sort_values(by='candle_end_time', inplace=True)
df.reset_index(inplace=True, drop=True)

df['price'] = df['画图信号点'].shift(1)
columns_to_keep = ['candle_end_time', '笔的信号', 'price']
df = df[columns_to_keep]
df = df[df['笔的信号'] >= 0]

def cal_signal_pic(df):
    df['candle_end_time'] = pd.to_datetime(df['candle_end_time'])
    df.sort_values(by='candle_end_time', inplace=True)
    df.reset_index(inplace=True, drop=True)
    temp_df = df.copy()
    temp_df['是否保留'] = None
    index_begin = 0
    index_list = []  # 最后保留的list
    while index_begin < len(df) - 3:  # 确保有足够的行来比较
        signal_begin = df.loc[index_begin, '笔的信号']
        price_begin = df.loc[index_begin, 'price']
        price_next = df.loc[min(index_begin + 3, len(df) - 1), 'price']  # 防止索引超出范围
        price_next_next = df.loc[min(index_begin + 5, len(df) - 1), 'price']  # 再向后判断一个价格
        # print(index_begin, signal_begin, price_begin, price_next, price_next_next)
        print(index_begin)
        if (signal_begin == 0) and (price_next > price_begin) :
            if price_next_next < price_next:
                index_begin += 3
                index_list.append(index_begin)
                print('开始0保留', index_begin)
            else:
                index_begin += 2

        elif (signal_begin == 1) and (price_next < price_begin):
            if price_next_next > price_next:
                index_begin += 3
                index_list.append(index_begin)
                print('开始1保留', index_begin)
            else:
                index_begin += 2
        else:
            index_begin += 1  # 如果当前点不满足条件，移动到下一个点
        print(index_begin, signal_begin, price_begin, price_next, price_next_next)

    print(index_list)
    df.loc[index_list, '是否保留'] = df['笔的信号']
    return df


if __name__ == '__main__':
    df = cal_signal_pic(df)
    print(df)

df2 = df.copy()
df1['candle_end_time'] = pd.to_datetime(df1['candle_end_time'])
df2['candle_end_time'] = pd.to_datetime(df2['candle_end_time'])
df2 = df2[['candle_end_time', '是否保留', 'price']]
df3 = pd.merge(df1, df2, on='candle_end_time', how='left')
df3.loc[df3['是否保留'] >= 0, '线段图'] = df3['price']
df3['线段画图'] = df3['线段图'].shift(-1)
df3.to_csv('数据文件4 线段.csv', encoding='gbk')

df3['candle_end_time'] = pd.to_datetime(df3['candle_end_time'])
# 选择画图的时间范围
df3 = df3[df3['candle_end_time'] >= pd.to_datetime(start_time)]
df3 = df3[df3['candle_end_time'] <= pd.to_datetime(end_time)]

# 创建图和轴
fig, ax = plt.subplots(figsize=(14, 7), dpi=100)
fig.set_facecolor('grey')

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

# 绘制K线图
for idx, row in df3.iterrows():
    if pd.notna(row['candle_end_time']) and pd.notna(row['high']) and pd.notna(row['low']):
        # 绘制价格线，更改颜色为白色，并加粗
        ax.plot([mdates.date2num(row['candle_end_time']), mdates.date2num(row['candle_end_time'])],
                [row['low'], row['high']], color='white', linewidth=1)

# 添加箭头
previous_point = None
for i in range(len(df3)):
    if pd.notna(df3['candle_end_time'].iloc[i]) and pd.notna(df3['画图信号点'].iloc[i]):
        current_point = (mdates.date2num(df3['candle_end_time'].iloc[i]), df3['画图信号点'].iloc[i])

        if previous_point is not None:
            dx = current_point[0] - previous_point[0]
            dy = current_point[1] - previous_point[1]

            # 绘制箭头，更改颜色为橙色，并加粗
            ax.arrow(previous_point[0], previous_point[1], dx, dy,
                     head_width=0, head_length=0, fc='orange', ec='orange', linewidth=1.5)

        previous_point = current_point

previous = None
for i in range(len(df3)):
    if pd.notna(df3['candle_end_time'].iloc[i]) and pd.notna(df3['线段画图'].iloc[i]):
        current = (mdates.date2num(df3['candle_end_time'].iloc[i]), df3['线段画图'].iloc[i])

        if previous is not None:
            dx = current[0] - previous[0]
            dy = current[1] - previous[1]

            # 绘制箭头，更改颜色为绿色，并加粗
            ax.arrow(previous[0], previous[1], dx, dy,
                     head_width=0, head_length=0, fc='green', ec='green', linewidth=2)

        previous = current

# 设置日期格式
ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=20))  # 调整maxticks参数
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))

# 设置网格和标签
ax.grid(False)  # 关闭网格
plt.xticks(rotation=0, color='white', fontsize=12)  # 设置x轴刻度标签颜色和大小
plt.yticks(color='white', fontsize=12)  # 设置y轴刻度标签颜色和大小
plt.xlabel('Date', color='white', fontsize=12)  # 设置x轴标签颜色和大小
plt.ylabel('Price', color='white', fontsize=12)  # 设置y轴标签颜色和大小

# 保存图形，指定分辨率和大小
plt.savefig('图片4 线段.png', dpi=100, bbox_inches='tight', pad_inches=0.1)

plt.show()