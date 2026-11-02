function renderChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption(option);
  window.addEventListener('resize', () => chart.resize());
}

async function load() {
  try {
    const [count, usage, status, heat] = await Promise.all([
      fetch('/api/statistics/reservation-count').then(r => r.json()),
      fetch('/api/statistics/room-usage').then(r => r.json()),
      fetch('/api/statistics/status').then(r => r.json()),
      fetch('/api/statistics/time-heat').then(r => r.json()),
    ]);

    renderChart('chart-count', {
      title: { text: '各房间预约次数' },
      tooltip: {},
      xAxis: { type: 'category', data: count.map(d => d.name) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{ type: 'bar', data: count.map(d => d.value), itemStyle: { color: '#5470c6' } }]
    });

    renderChart('chart-usage', {
      title: { text: '房间使用率（%，近 7 天）' },
      tooltip: { valueFormatter: v => v + '%' },
      xAxis: { type: 'value', max: 100 },
      yAxis: { type: 'category', data: usage.map(d => d.name) },
      series: [{ type: 'bar', data: usage.map(d => d.value), itemStyle: { color: '#91cc75' } }]
    });

    renderChart('chart-status', {
      title: { text: '预约状态分布' },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '60%',
        data: status,
        color: ['#5470c6', '#91cc75', '#fac858']
      }]
    });

    renderChart('chart-heat', {
      title: { text: '时间段热度（预约次数）' },
      tooltip: {},
      xAxis: { type: 'category', data: heat.map(d => d.hour + ':00') },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{ type: 'bar', data: heat.map(d => d.value), itemStyle: { color: '#fac858' } }]
    });
  } catch (e) {
    console.error('加载统计数据失败', e);
  }
}

document.addEventListener('DOMContentLoaded', load);
