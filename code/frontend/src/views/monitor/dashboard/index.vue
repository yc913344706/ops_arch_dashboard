<template>
  <div class="monitor-dashboard">
    <el-row :gutter="20" class="dashboard-header">
      <el-col :span="24">
        <el-card class="summary-card">
          <div class="summary-content">
            <div class="summary-item">
              <div class="summary-number">{{ summary.architectureCount }}</div>
              <div class="summary-label">架构图数量</div>
            </div>
            <div class="summary-item">
              <div class="summary-number">{{ summary.nodeCount }}</div>
              <div class="summary-label">节点总数</div>
            </div>
            <div class="summary-item">
              <!-- 
              https://www.coloraa.com/333333
              #52c41a -- 绿色
              #333 -- 黑色
              #ff4d4f -- 红色
              #faad14 -- 黄色
              #a9a9a9 -- 深灰色
              -->
              <div class="summary-number">
                <div :style="{ color: summary.healthyNodeCount > 0 ? '#52c41a' : '#333' }">{{ summary.healthyNodeCount }}</div>/
                <div :style="{ color: summary.unknownNodeCount > 0 ? '#a9a9a9' : '#333' }">{{ summary.unknownNodeCount }}</div>
              </div>
              <div class="summary-label">健康/无主机节点</div>
            </div>
            
            <div class="summary-item">
              <div class="summary-number">
                <div :style="{ color: summary.yellowNodeCount > 0 ? '#faad14' : '#333' }">{{ summary.yellowNodeCount }}</div>/
                <div :style="{ color: summary.redNodeCount > 0 ? '#ff4d4f' : '#333' }">{{ summary.redNodeCount }}</div>
              </div>
              <div class="summary-label">部分异常/严重异常节点</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="dashboard-content">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>健康状态趋势</span>
              <div class="time-filter">
                <el-radio-group v-model="timePeriod" size="small" @change="onTimePeriodChange">
                  <el-radio-button label="day">日</el-radio-button>
                  <el-radio-button label="week">周</el-radio-button>
                  <el-radio-button label="month">月</el-radio-button>
                  <el-radio-button label="quarter">季</el-radio-button>
                  <el-radio-button label="year">年</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div ref="healthChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="alert-card">
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
            </div>
          </template>
          <div class="alert-list">
            <div 
              v-for="alert in recentAlerts" 
              :key="alert.id"
              class="alert-item"
              :class="`alert-${alert.level}`"
            >
              <div class="alert-content">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-node">告警详情：{{ alert.description }}</div>
                <div class="alert-time">所属链路：{{ alert.link_name }}</div>
                <div class="alert-time">最后告警时间：{{ alert.time }}</div>
                <!-- <div class="alert-time">{{ formatTime(new Date(alert.time)) }}</div> -->
                <div class="alert-status" :class="`status-${alert.status.toLowerCase()}`">
                  <el-tag 
                    :type="getStatusType(alert.status)" 
                    size="small"
                    style="position: absolute; top: 2px; right: 2px;"
                  >
                    {{ getStatusText(alert.status) }}
                  </el-tag>
                </div>
              </div>
            </div>
            
            <div v-if="recentAlerts.length === 0" class="no-alerts">
              暂无告警
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
<!--     
    <el-row :gutter="20" class="dashboard-footer">
      <el-col :span="24">
        <el-card class="quick-access-card">
          <template #header>
            <div class="card-header">
              <span>快速访问</span>
            </div>
          </template>
          <div class="quick-access-content">
            <div class="quick-item" @click="goToArchitecture">
              <el-icon size="24"><Connection /></el-icon>
              <span>架构图管理</span>
            </div>
            <div class="quick-item" @click="goToNodes">
              <el-icon size="24"><Monitor /></el-icon>
              <span>节点管理</span>
            </div>
            <div class="quick-item" @click="goToSettings">
              <el-icon size="24"><Setting /></el-icon>
              <span>系统设置</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row> -->
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Connection, Monitor, Setting } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { dashboardApi, linkApi, nodeApi } from '@/api/monitor'

// 路由实例
const router = useRouter()

// 响应式数据
const summary = ref({
  architectureCount: 0,
  nodeCount: 0,
  healthyNodeCount: 0,
  unknownNodeCount: 0,
  unhealthyNodeCount: 0,
  yellowNodeCount: 0, // 部分异常节点
  redNodeCount: 0 // 严重异常节点
})

const recentAlerts = ref([])
const timePeriod = ref('day') // 默认时间范围

const healthChartRef = ref<HTMLElement>()
let healthChartInstance: any = null

// 格式化时间
const formatTime = (time: Date) => {
  const now = new Date()
  const diff = now.getTime() - time.getTime()
  const minutes = Math.floor(diff / (1000 * 60))
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

// 获取状态类型用于标签显示
const getStatusType = (status: string) => {
  switch (status?.toUpperCase()) {
    case 'OPEN':
      return 'danger' // 红色，表示开放状态
    case 'SILENCED':
      return 'warning' // 黄色，表示已静默
    case 'CLOSED':
      return 'success' // 绿色，表示已关闭
    default:
      return 'info' // 蓝色，表示其他状态
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status?.toUpperCase()) {
    case 'OPEN':
      return '告警中'
    case 'SILENCED':
      return '已静默'
    case 'CLOSED':
      return '已关闭'
    default:
      return status
  }
}

// 获取概览数据
const fetchSummaryData = async () => {
  try {
    // 获取仪表板统计数据
    const dashboardResponse = await dashboardApi.getDashboardStats({period: timePeriod.value})
    const data = dashboardResponse.data
    
    // 更新概览数据
    if (data && data.summary) {
      summary.value.architectureCount = data.summary.total_links || 0
      summary.value.nodeCount = data.summary.total_nodes || 0
      summary.value.healthyNodeCount = data.summary.healthy_nodes || 0
      summary.value.unknownNodeCount = data.summary.unknown_nodes || 0
      summary.value.yellowNodeCount = data.summary.yellow_nodes || 0
      summary.value.redNodeCount = data.summary.red_nodes || 0
      summary.value.unhealthyNodeCount = data.summary.unhealthy_nodes || 0  // 不健康节点（yellow + red）
    }
    
    // 更新最近告警数据
    if (data && data.recent_alerts) {
      recentAlerts.value = data.recent_alerts.map(alert => ({
        id: alert.id,
        title: alert.title,
        nodeName: alert.node_name,
        level: alert.severity.toLowerCase(),
        time: alert.time,
        // time: new Date(alert.time),
        status: alert.status,
        link_name: alert.link_name,
        description: alert.description
      }))
    }
    
    // 更新健康趋势图表
    if (data && data.health_trend && data.health_trend.data) {
      updateHealthChart(data.health_trend.data)
    }
  } catch (error) {
    console.error('获取仪表板数据失败:', error)
    ElMessage.error('获取仪表板数据失败')
  }
}

// 时间范围选择变化事件
const onTimePeriodChange = () => {
  fetchSummaryData()
}

// 初始化健康状态图表
const initHealthChart = () => {
  if (!healthChartRef.value) return
  
  healthChartInstance = echarts.init(healthChartRef.value)
  
  // 初始时使用默认数据
  const dates = []
  const greenData = []
  const yellowData = []
  const redData = []
  const unknownData = []
  
  // 默认显示最近7天的空数据
  for (let i = 6; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    dates.push(`${date.getMonth() + 1}-${date.getDate()}`)
    greenData.push(0)
    yellowData.push(0)
    redData.push(0)
    unknownData.push(0)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['健康', '部分异常', '严重异常', '未知']
    },
    xAxis: {
      type: 'category',
      data: dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '健康',
        type: 'line',
        data: greenData,
        smooth: true,
        itemStyle: {
          color: '#52c41a' // 绿色
        }
      },
      {
        name: '部分异常',
        type: 'line',
        data: yellowData,
        smooth: true,
        itemStyle: {
          color: '#faad14' // 黄色
        }
      },
      {
        name: '严重异常',
        type: 'line',
        data: redData,
        smooth: true,
        itemStyle: {
          color: '#ff4d4f' // 红色
        }
      },
      {
        name: '未知',
        type: 'line',
        data: unknownData,
        smooth: true,
        itemStyle: {
          color: '#ccc' // 灰色
        }
      }
    ]
  }
  
  healthChartInstance.setOption(option)
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
}

// 更新健康状态图表
const updateHealthChart = (trendData) => {
  if (!healthChartInstance) return
  
  console.log('Updating chart with trend data:', trendData) // 调试日志
  
  // 提取日期和各种健康状态数据
  const dates = trendData.map(item => {
    // 根据数据格式调整日期显示格式
    let dateStr = item.date
    if (timePeriod.value === 'day') {
      // 如果是按小时显示，保留时间部分
      return dateStr.slice(11, 16) // 取 HH:MM 部分
    } else if (timePeriod.value === 'year') {
      // 如果是按年显示，显示年月
      return dateStr.slice(0, 7) // 取 YYYY-MM 部分
    } else {
      // 其他情况显示月日
      return dateStr.slice(5, 10) // 取 MM-DD 部分
    }
  })
  
  const greenData = trendData.map(item => item.green_count)
  const yellowData = trendData.map(item => item.yellow_count)
  const redData = trendData.map(item => item.red_count)
  const unknownData = trendData.map(item => item.unknown_count)
  
  console.log('Chart data:', { dates, greenData, yellowData, redData, unknownData }) // 调试日志
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const date = params[0].axisValue;
        let tooltip = date + '<br/>';
        params.forEach(param => {
          tooltip += param.marker + ' ' + param.seriesName + ': ' + param.value + '<br/>';
        });
        // 添加总计
        const total = greenData[params[0].dataIndex] + 
                     yellowData[params[0].dataIndex] + 
                     redData[params[0].dataIndex] + 
                     unknownData[params[0].dataIndex];
        tooltip += `<strong>总计: ${total}</strong>`;
        return tooltip;
      }
    },
    legend: {
      data: ['健康', '部分异常', '严重异常', '未知']
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        interval: 0, // 显示所有标签
        rotate: 45, // 旋转标签避免重叠
        fontSize: 10 // 设置较小的字体以适应更多标签
      }
    },
    yAxis: {
      type: 'value',
      name: '节点数量',
      nameLocation: 'middle',
      nameGap: 40
    },
    series: [
      {
        name: '健康',
        type: 'line',
        data: greenData,
        smooth: true,
        itemStyle: {
          color: '#52c41a' // 绿色
        },
        lineStyle: {
          width: 2
        }
      },
      {
        name: '部分异常',
        type: 'line',
        data: yellowData,
        smooth: true,
        itemStyle: {
          color: '#faad14' // 黄色
        },
        lineStyle: {
          width: 2
        }
      },
      {
        name: '严重异常',
        type: 'line',
        data: redData,
        smooth: true,
        itemStyle: {
          color: '#ff4d4f' // 红色
        },
        lineStyle: {
          width: 2
        }
      },
      {
        name: '未知',
        type: 'line',
        data: unknownData,
        smooth: true,
        itemStyle: {
          color: '#ccc' // 灰色
        },
        lineStyle: {
          width: 2
        }
      }
    ]
  }
  
  healthChartInstance.setOption(option)
}

// 处理窗口大小变化
const handleResize = () => {
  if (healthChartInstance) {
    healthChartInstance.resize()
  }
}

// 快捷导航
const goToArchitecture = () => {
  router.push('/monitor/architecture')
}

const goToNodes = () => {
  router.push('/monitor/nodes')
}

const goToSettings = () => {
  router.push('/monitor/settings')
}

// 组件挂载
onMounted(() => {
  fetchSummaryData()
  initHealthChart()
})

// 组件卸载
onUnmounted(() => {
  if (healthChartInstance) {
    healthChartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.monitor-dashboard {
  padding: 20px;
  height: 100%;
  overflow: auto;
}

.dashboard-header {
  margin-bottom: 20px;
}

.summary-card {
  height: 120px;
}

.summary-content {
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 100%;
  flex-wrap: wrap;
}

.summary-item {
  text-align: center;
  flex: 1;
  min-width: 120px;
}

.summary-number {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.summary-number > div {
  display: inline-block;
}

.summary-label {
  font-size: 14px;
  font-weight: bold;
  color: #666;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.dashboard-content {
  margin-bottom: 20px;
}

.chart-card, .alert-card {
  min-height: 400px;
}

.chart-container {
  width: 100%;
  min-height: 350px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.time-filter {
  display: inline-block;
}

.alert-list {
  height: 350px;
  overflow-y: auto;
}

.alert-item {
  padding: 15px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background-color 0.3s;
  position: relative;
}

.alert-item:hover {
  background-color: #f5f5f5;
}

.alert-success {
  border-left: 4px solid #52c41a;
}

.alert-warning {
  border-left: 4px solid #faad14;
}

.alert-error {
  border-left: 4px solid #ff4d4f;
}

.alert-content {
  display: flex;
  flex-direction: column;
  position: relative; /* 为绝对定位提供容器 */
}

.alert-content .alert-title {
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
}

.alert-content .alert-node {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.alert-content .alert-time {
  font-size: 12px;
  color: #999;
  margin-bottom: 5px;
}

.no-alerts {
  text-align: center;
  padding: 50px;
  color: #999;
}

.dashboard-footer {
  height: 150px;
}

.quick-access-card {
  height: 100%;
}

.quick-access-content {
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 100%;
}

.quick-item {
  text-align: center;
  cursor: pointer;
  padding: 20px;
  border-radius: 8px;
  transition: all 0.3s;
}

.quick-item:hover {
  background-color: #f0f2f5;
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.quick-item span {
  display: block;
  margin-top: 10px;
  font-size: 14px;
  color: #333;
}

/* 告警等级颜色 */
.alert-item.alert-high {
  border-left: 4px solid #ff4d4f; /* 红色 - 严重 */
}

.alert-item.alert-medium {
  border-left: 4px solid #faad14; /* 黄色 - 中等 */
}

.alert-item.alert-low {
  border-left: 4px solid #1890ff; /* 蓝色 - 低 */
}

.alert-item.alert-info {
  border-left: 4px solid #909399; /* 灰色 - 信息 */
}
</style>