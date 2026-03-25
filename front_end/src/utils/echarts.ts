import * as echarts from 'echarts/core'
import { BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import type { EChartsOption, EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, PieChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const init = echarts.init
const getInstanceByDom = echarts.getInstanceByDom

export { echarts, getInstanceByDom, init }
export type { EChartsOption, EChartsType }
