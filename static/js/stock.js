

// 初始化全局变量
let stockChart = null;
let volumeChart = null;
let technicalChart = null;
let currentPeriod = 'day';
let currentIndicator = 'MACD';

// 初始化图表
function initCharts() {
    stockChart = echarts.init(document.getElementById('kline-chart'));
    volumeChart = echarts.init(document.getElementById('volume-chart'));
    technicalChart = echarts.init(document.getElementById('technical-chart'));

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
        stockChart.resize();
        volumeChart.resize();
        technicalChart.resize();
    });
}

// 格式化数据
function formatStockData(data) {
    return {
        categoryData: data.map(item => item.date),
        values: data.map(item => [item.open, item.close, item.low, item.high]),
        volumes: data.map(item => item.volume),
        ma5: calculateMA(5, data),
        ma10: calculateMA(10, data),
        ma20: calculateMA(20, data)
    };
}

// 计算移动平均线
function calculateMA(dayCount, data) {
    let result = [];
    for (let i = 0, len = data.length; i < len; i++) {
        if (i < dayCount - 1) {
            result.push('-');
            continue;
        }
        let sum = 0;
        for (let j = 0; j < dayCount; j++) {
            sum += data[i - j].close;
        }
        result.push((sum / dayCount).toFixed(2));
    }
    return result;
}

// 渲染K线图
function renderKLineChart(data) {
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {
            data: ['K线', 'MA5', 'MA10', 'MA20']
        },
        grid: {
            left: '10%',
            right: '10%',
            bottom: '15%'
        },
        xAxis: {
            type: 'category',
            data: data.categoryData,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            splitNumber: 20
        },
        yAxis: {
            scale: true,
            splitArea: {
                show: true
            }
        },
        dataZoom: [
            {
                type: 'inside',
                start: 50,
                end: 100
            },
            {
                show: true,
                type: 'slider',
                bottom: '5%',
                start: 50,
                end: 100
            }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: data.values,
                itemStyle: {
                    color: '#ff0000',
                    color0: '#00ff00',
                    borderColor: '#ff0000',
                    borderColor0: '#00ff00'
                }
            },
            {
                name: 'MA5',
                type: 'line',
                data: data.ma5,
                smooth: true,
                lineStyle: {
                    opacity: 0.5
                }
            },
            {
                name: 'MA10',
                type: 'line',
                data: data.ma10,
                smooth: true,
                lineStyle: {
                    opacity: 0.5
                }
            },
            {
                name: 'MA20',
                type: 'line',
                data: data.ma20,
                smooth: true,
                lineStyle: {
                    opacity: 0.5
                }
            }
        ]
    };

    stockChart.setOption(option);
}

// 渲染成交量图
function renderVolumeChart(data) {
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        grid: {
            left: '10%',
            right: '10%',
            bottom: '15%'
        },
        xAxis: {
            type: 'category',
            data: data.categoryData,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false }
        },
        yAxis: {
            type: 'value',
            scale: true
        },
        dataZoom: [
            {
                type: 'inside',
                start: 50,
                end: 100
            },
            {
                show: true,
                type: 'slider',
                bottom: '5%',
                start: 50,
                end: 100
            }
        ],
        series: [
            {
                name: '成交量',
                type: 'bar',
                data: data.volumes,
                itemStyle: {
                    color: function(params) {
                        return data.values[params.dataIndex][1] > data.values[params.dataIndex][0] ? '#ff0000' : '#00ff00';
                    }
                }
            }
        ]
    };

    volumeChart.setOption(option);
}

// 更新股票信息
function updateStockInfo(data) {
    const lastData = data[data.length - 1];
    const prevData = data[data.length - 2];
    
    document.getElementById('current-price').textContent = lastData.close.toFixed(2);
    
    const change = lastData.close - prevData.close;
    const changePercent = (change / prevData.close * 100).toFixed(2);
    const changeElement = document.getElementById('price-change');
    changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent}%)`;
    changeElement.className = `price-change ${change >= 0 ? 'positive' : 'negative'}`;
    
    document.getElementById('volume').textContent = (lastData.volume / 10000).toFixed(2) + '万';
    document.getElementById('turnover').textContent = (lastData.volume * lastData.close / 100000000).toFixed(2) + '亿';
}

// 获取股票数据
async function fetchStockData(stockCode, startDate, endDate) {
    try {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('error-message').style.display = 'none';
        document.getElementById('stock-data').style.display = 'none';

        const response = await fetch(`/api/stock_data?code=${stockCode}&start_date=${startDate}&end_date=${endDate}&period=${currentPeriod}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        document.getElementById('stock-name').textContent = data.stock_name;
        document.getElementById('stock-data').style.display = 'block';

        const formattedData = formatStockData(data.data);
        renderKLineChart(formattedData);
        renderVolumeChart(formattedData);
        updateStockInfo(data.data);

    } catch (error) {
        document.getElementById('error-message').textContent = error.message;
        document.getElementById('error-message').style.display = 'block';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

// 事件监听器
document.addEventListener('DOMContentLoaded', () => {
    initCharts();

    // 表单提交
    document.getElementById('stock-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const stockCode = document.getElementById('stock-code').value;
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        fetchStockData(stockCode, startDate, endDate);
    });

    // 周期切换
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPeriod = btn.dataset.period;
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const stockCode = document.getElementById('stock-code').value;
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            if (stockCode && startDate && endDate) {
                fetchStockData(stockCode, startDate, endDate);
            }
        });
    });

    // 技术指标切换
    document.querySelectorAll('.indicator-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentIndicator = btn.dataset.indicator;
            document.querySelectorAll('.indicator-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // TODO: 实现技术指标图表更新
        });
    });

    // 设置默认日期
    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    
    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    document.getElementById('start-date').value = oneYearAgo.toISOString().split('T')[0];
});