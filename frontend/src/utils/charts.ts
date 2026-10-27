export const palette = [
  '#2f5597',
  '#5b8cd6',
  '#6fa8a0',
  '#d9a45b',
  '#9a7fb5',
  '#7f95b5',
  '#cf6f6f',
  '#59a8bf',
  '#b0b88a',
  '#8c8fa8',
]

export const baseText = {
  fontFamily: '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif',
  color: '#4a5b72',
}

export const tooltipStyle = {
  backgroundColor: 'rgba(19, 41, 75, 0.92)',
  borderWidth: 0,
  textStyle: { color: '#fff', fontSize: 12 },
}

export const gridStyle = {
  left: 12,
  right: 22,
  top: 38,
  bottom: 8,
  containLabel: true,
}

export const axisStyle = {
  axisLine: { lineStyle: { color: '#dfe6f0' } },
  axisTick: { show: false },
  axisLabel: { color: '#7a8797', fontSize: 11 },
  splitLine: { lineStyle: { color: '#eef2f7' } },
}

export function pieOption(data: Array<{ name: string; value: number }>, seriesName = '数量') {
  return {
    color: palette,
    tooltip: { trigger: 'item', ...tooltipStyle },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#5f6f85', fontSize: 11 },
    },
    series: [
      {
        name: seriesName,
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { show: false },
        emphasis: { label: { show: true, fontWeight: 600, fontSize: 12 } },
        data,
      },
    ],
  }
}

export function barOption(
  categories: string[],
  values: number[],
  options: { name?: string; horizontal?: boolean; color?: string; unit?: string } = {},
) {
  const name = options.name || '数量'
  const color = options.color || '#2f5597'
  const valueAxis = {
    type: 'value',
    name: options.unit || '',
    nameTextStyle: { color: '#9aa7b8', fontSize: 10 },
    ...axisStyle,
  }
  const categoryAxis = {
    type: 'category',
    data: categories,
    ...axisStyle,
    splitLine: { show: false },
    axisLabel: { color: '#7a8797', fontSize: 11, interval: 0, rotate: categories.length > 8 ? 30 : 0 },
  }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle },
    grid: gridStyle,
    xAxis: options.horizontal ? valueAxis : categoryAxis,
    yAxis: options.horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: [
      {
        name,
        type: 'bar',
        data: values,
        barMaxWidth: 26,
        itemStyle: {
          color,
          borderRadius: options.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
        },
      },
    ],
  }
}

export function lineOption(
  categories: string[],
  series: Array<{ name: string; data: number[]; color?: string; unit?: string }>,
) {
  return {
    color: palette,
    tooltip: { trigger: 'axis', ...tooltipStyle },
    legend: {
      top: 0,
      right: 0,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 4,
      textStyle: { color: '#5f6f85', fontSize: 11 },
    },
    grid: gridStyle,
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: false,
      ...axisStyle,
      splitLine: { show: false },
    },
    yAxis: { type: 'value', ...axisStyle },
    series: series.map((item, index) => ({
      name: item.name,
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: item.data,
      lineStyle: { width: 2.2, color: item.color || palette[index % palette.length] },
      itemStyle: { color: item.color || palette[index % palette.length] },
      areaStyle: {
        opacity: 0.1,
        color: item.color || palette[index % palette.length],
      },
    })),
  }
}
