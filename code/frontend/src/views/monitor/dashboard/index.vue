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
              <div class="summary-number" :style="{ color: summary.healthyNodeCount > 0 ? '#52c41a' : '#333' }">
                {{ summary.healthyNodeCount }}
              </div>
              <div class="summary-label">健康节点</div>
            </div>
            <div class="summary-item">
              <div class="summary-number" :style="{ color: summary.unhealthyNodeCount > 0 ? '#ff4d4f' : '#333' }">
                {{ summary.unhealthyNodeCount }}
              </div>
              <div class="summary-label">异常节点</div>
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
                <div class="alert-node">{{ alert.nodeName }}</div>
                <div class="alert-time">{{ formatTime(alert.time) }}</div>
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
import { linkApi, nodeApi } from '@/api/monitor'

// 路由实例
const router = useRouter()

// 响应式数据
const summary = ref({
  architectureCount: 0,
  nodeCount: 0,
  healthyNodeCount: 0,
  unhealthyNodeCount: 0
})

const recentAlerts = ref([
  {
    id: '1',
    title: '节点连接失败',
    nodeName: 'Web Server 01',
    level: 'error',
    time: new Date(Date.now() - 1000 * 60 * 5) // 5分钟前
  },
  {
    id: '2',
    title: '响应时间超阈值',
    nodeName: 'Database Master',
    level: 'warning',
    time: new Date(Date.now() - 1000 * 60 * 15) // 15分钟前
  },
  {
    id: '3',
    title: '节点恢复正常',
    nodeName: 'Cache Server 02',
    level: 'success',
    time: new Date(Date.now() - 1000 * 60 * 30) // 30分钟前
  }
])

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

// 获取概览数据
const fetchSummaryData = async () => {
  try {
    // 获取架构图数量
    const linkResponse = await linkApi.getLinks({ link_type: 'architecture' })
    summary.value.architectureCount = linkResponse.data.count || linkResponse.data.length || 0
    
    // 获取节点统计数据
    // 这里需要后端提供统计API，暂且模拟
    summary.value.nodeCount = 45
    summary.value.healthyNodeCount = 42
    summary.value.unhealthyNodeCount = 3
  } catch (error) {
    console.error('获取概览数据失败:', error)
    ElMessage.error('获取概览数据失败')
  }
}

// 初始化健康状态图表
const initHealthChart = () => {
  if (!healthChartRef.value) return
  
  healthChartInstance = echarts.init(healthChartRef.value)
  
  // 模拟健康状态数据
  const dates = []
  const healthyData = []
  const unhealthyData = []
  
  for (let i = 6; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    dates.push(`${date.getMonth() + 1}-${date.getDate()}`)
    
    // 模拟数据
    const healthy = Math.floor(Math.random() * 20) + 30
    const unhealthy = Math.floor(Math.random() * 5)
    
    healthyData.push(healthy)
    unhealthyData.push(unhealthy)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['健康节点', '异常节点']
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
        name: '健康节点',
        type: 'line',
        stack: '总量',
        data: healthyData,
        smooth: true,
        itemStyle: {
          color: '#52c41a'
        }
      },
      {
        name: '异常节点',
        type: 'line',
        stack: '总量',
        data: unhealthyData,
        smooth: true,
        itemStyle: {
          color: '#ff4d4f'
        }
      }
    ]
  }
  
  healthChartInstance.setOption(option)
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
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
}

.summary-item {
  text-align: center;
}

.summary-number {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.summary-label {
  font-size: 14px;
  color: #666;
}

.dashboard-content {
  margin-bottom: 20px;
}

.chart-card, .alert-card {
  height: 400px;
}

.chart-container {
  width: 100%;
  height: 350px;
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

.alert-content .alert-title {
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
}

.alert-content .alert-node {
  font-size: 12px;
  color: #666;
  margin-bottom: 3px;
}

.alert-content .alert-time {
  font-size: 12px;
  color: #999;
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

.card-header {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}
</style>