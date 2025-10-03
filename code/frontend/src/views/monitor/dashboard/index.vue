<template>
  <div class="monitor-dashboard">
    <el-card class="dashboard-card">
      <template #header>
        <div class="card-header">
          <span>运维架构监控总览</span>
        </div>
      </template>
      <div class="dashboard-content">
        <div class="stats-container">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-item">
                  <div class="stat-number">12</div>
                  <div class="stat-label">总链路数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-item">
                  <div class="stat-number">145</div>
                  <div class="stat-label">总节点数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card healthy">
                <div class="stat-item">
                  <div class="stat-number">140</div>
                  <div class="stat-label">健康节点</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card unhealthy">
                <div class="stat-item">
                  <div class="stat-number">5</div>
                  <div class="stat-label">异常节点</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div class="quick-access">
          <h3>快捷访问</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card class="quick-card" @click="goToLinks">
                <div class="quick-item">
                  <el-icon size="32"><Connection /></el-icon>
                  <h4>链路管理</h4>
                  <p>查看和管理所有链路</p>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="quick-card" @click="goToNodes">
                <div class="quick-item">
                  <el-icon size="32"><Monitor /></el-icon>
                  <h4>节点配置</h4>
                  <p>配置和监控节点状态</p>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="quick-card" @click="goToAlerts">
                <div class="quick-item">
                  <el-icon size="32"><Bell /></el-icon>
                  <h4>告警中心</h4>
                  <p>查看和处理告警信息</p>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div class="recent-alerts">
          <h3>最近告警</h3>
          <el-table :data="recentAlerts" style="width: 100%">
            <el-table-column prop="name" label="节点名称" width="180" />
            <el-table-column prop="linkName" label="所属链路" width="180" />
            <el-table-column prop="type" label="告警类型" width="120">
              <template #default="scope">
                <el-tag 
                  :type="scope.row.type === 'error' ? 'danger' : 'warning'" 
                  size="small">
                  {{ scope.row.type === 'error' ? '错误' : '警告' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="发生时间" width="180" />
            <el-table-column prop="message" label="告警信息" />
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Connection, 
  Monitor, 
  Bell,
  Warning
} from '@element-plus/icons-vue'

defineOptions({
  name: 'MonitorDashboard'
})

const router = useRouter()

// 模拟统计数据
const stats = ref({
  totalLinks: 12,
  totalNodes: 145,
  healthyNodes: 140,
  unhealthyNodes: 5
})

// 模拟最近告警数据
const recentAlerts = ref([
  { name: 'Web服务器01', linkName: '应用链路', type: 'error', time: '2023-06-15 10:30:25', message: 'HTTP请求超时' },
  { name: '数据库服务器', linkName: '数据库链路', type: 'warning', time: '2023-06-15 09:45:12', message: '响应时间超过阈值' },
  { name: '负载均衡器', linkName: '网络链路', type: 'error', time: '2023-06-15 08:20:05', message: '端口连接失败' },
  { name: '缓存服务器', linkName: '应用链路', type: 'warning', time: '2023-06-15 07:15:33', message: 'CPU使用率过高' }
])

// 导航方法
const goToLinks = () => {
  router.push('/monitor/links')
}

const goToNodes = () => {
  router.push('/monitor/nodes')
}

const goToAlerts = () => {
  router.push('/monitor/alerts')
}
</script>

<style scoped>
.monitor-dashboard {
  padding: 20px;
}

.dashboard-card {
  min-height: 600px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.dashboard-content {
  padding-top: 20px;
}

.stats-container {
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.stat-card.healthy {
  border-left: 4px solid #52c41a;
}

.stat-card.unhealthy {
  border-left: 4px solid #ff4d4f;
}

.stat-item {
  padding: 15px 0;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

.quick-access {
  margin-bottom: 30px;
}

.quick-access h3 {
  margin-bottom: 20px;
}

.quick-card {
  cursor: pointer;
  height: 150px;
  transition: all 0.3s;
}

.quick-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.quick-item {
  text-align: center;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.quick-item h4 {
  margin: 15px 0 5px 0;
}

.quick-item p {
  color: #999;
  font-size: 14px;
}

.recent-alerts h3 {
  margin-bottom: 20px;
}
</style>