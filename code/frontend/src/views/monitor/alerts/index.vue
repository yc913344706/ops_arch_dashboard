<template>
  <div class="alerts-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警管理</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :model="filterForm" inline>
          <el-form-item label="告警标题">
            <el-input 
              v-model="filterForm.title" 
              placeholder="输入告警标题" 
              clearable
              @keyup.enter="fetchAlerts" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 120px;">
              <el-option label="开启" value="OPEN" />
              <el-option label="已关闭" value="CLOSED" />
              <el-option label="已确认" value="ACKNOWLEDGED" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="filterForm.alert_type" placeholder="选择类型" clearable style="width: 150px;" :loading="loadingAlertTypes">
              <el-option
                v-for="item in alertTypes"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="严重程度">
            <el-select v-model="filterForm.severity" placeholder="选择严重程度" clearable style="width: 120px;">
              <el-option label="低" value="LOW" />
              <el-option label="中" value="MEDIUM" />
              <el-option label="高" value="HIGH" />
              <el-option label="严重" value="CRITICAL" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchAlerts">搜索</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table 
        :data="alerts" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="title" label="标题" width="200" show-overflow-tooltip />
        <el-table-column prop="node_id" label="节点ID" width="150" show-overflow-tooltip />
        <el-table-column prop="alert_type" label="类型" width="150">
          <template #default="scope">
            <el-tag size="small" :type="getAlertTypeTagType(scope.row.alert_type)">
              {{ getAlertTypeLabel(scope.row.alert_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="scope">
            <el-tag :type="getSeverityType(scope.row.severity)">
              {{ getSeverityLabel(scope.row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="first_occurred" label="首次发生" width="160" />
        <el-table-column prop="last_occurred" label="最后发生" width="160" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button 
              size="small" 
              @click="acknowledgeAlert(scope.row)"
              :disabled="scope.row.status !== 'OPEN'"
            >
              确认
            </el-button>
            <el-button 
              size="small" 
              type="primary" 
              @click="closeAlert(scope.row)"
              :disabled="scope.row.status !== 'OPEN'"
            >
              关闭
            </el-button>
            <el-button 
              size="small" 
              type="info" 
              @click="viewAlertDetail(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 告警详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="告警详情" 
      width="60%" 
      :before-close="closeDetailDialog"
    >
      <div v-if="selectedAlert" class="alert-detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedAlert.title }}</el-descriptions-item>
          <el-descriptions-item label="节点ID">{{ selectedAlert.node_id }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="getAlertTypeTagType(selectedAlert.alert_type)">
              {{ getAlertTypeLabel(selectedAlert.alert_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="子类型">{{ selectedAlert.alert_subtype || '-' }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(selectedAlert.severity)">
              {{ getSeverityLabel(selectedAlert.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedAlert.status)">
              {{ getStatusLabel(selectedAlert.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="首次发生">{{ selectedAlert.first_occurred }}</el-descriptions-item>
          <el-descriptions-item label="最后发生">{{ selectedAlert.last_occurred }}</el-descriptions-item>
          <el-descriptions-item label="解决时间">{{ selectedAlert.resolved_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ selectedAlert.acknowledged_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建者">
            {{ selectedAlert.created_by?.nickname || selectedAlert.created_by?.username || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="确认者">
            {{ selectedAlert.acknowledged_by?.nickname || selectedAlert.acknowledged_by?.username || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            <pre class="alert-description">{{ selectedAlert.description }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeDetailDialog">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { alertApi } from '@/api/monitor'
import { useRouter } from 'vue-router'

// 定义响应式数据
const loading = ref(false)
const detailDialogVisible = ref(false)

// 表格数据
const alerts = ref<any[]>([])

// 分页信息
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 告警类型相关
const alertTypes = ref<any[]>([])
const loadingAlertTypes = ref(false)

// 筛选表单
const filterForm = reactive({
  title: '',
  status: '',
  severity: '',
  node_id: '',
  alert_type: ''
})

// 选中的告警
const selectedAlert = ref<any>(null)

// 选中的行
const multipleSelection = ref<any[]>([])

// 获取告警类型列表
const fetchAlertTypes = async () => {
  loadingAlertTypes.value = true
  try {
    const response = await alertApi.getAlertTypes()
    alertTypes.value = response.data.alert_types || []
  } catch (error) {
    console.error('获取告警类型失败:', error)
    // 设置默认类型作为备选
    alertTypes.value = [
      { value: 'HEALTH_CHECK_FAILED', label: '健康检查失败' },
      { value: 'RESPONSE_TIME_SLOW', label: '响应时间过慢' },
      { value: 'SERVICE_UNAVAILABLE', label: '服务不可用' },
      { value: 'CONNECTION_TIMEOUT', label: '连接超时' },
      { value: 'PARTIAL_HEALTH_CHECK_FAILED', label: '部分健康检查失败' }
    ]
  } finally {
    loadingAlertTypes.value = false
  }
}

// 获取告警列表
const fetchAlerts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: filterForm.title,
      status: filterForm.status,
      severity: filterForm.severity,
      node_id: filterForm.node_id,
      alert_type: filterForm.alert_type
    }
    const response = await alertApi.getAlerts(params)
    alerts.value = response.data.data || []
    pagination.total = response.data.all_num || 0
  } catch (error) {
    console.error('获取告警列表失败:', error)
    ElMessage.error('获取告警列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterForm.title = ''
  filterForm.status = ''
  filterForm.severity = ''
  filterForm.node_id = ''
  filterForm.alert_type = ''
  fetchAlerts()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchAlerts()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.currentPage = page
  fetchAlerts()
}

// 行选择变化
const handleSelectionChange = (val: any[]) => {
  multipleSelection.value = val
}

// 获取严重程度标签类型
const getSeverityType = (severity: string) => {
  switch (severity) {
    case 'CRITICAL': return 'danger'
    case 'HIGH': return 'warning'
    case 'MEDIUM': return 'orange'
    case 'LOW': return 'info'
    default: return 'info'
  }
}

// 获取严重程度标签文本
const getSeverityLabel = (severity: string) => {
  switch (severity) {
    case 'CRITICAL': return '严重'
    case 'HIGH': return '高'
    case 'MEDIUM': return '中'
    case 'LOW': return '低'
    default: return severity
  }
}

// 获取状态标签类型
const getStatusType = (status: string) => {
  switch (status) {
    case 'OPEN': return 'danger'
    case 'CLOSED': return 'success'
    case 'ACKNOWLEDGED': return 'info'
    default: return 'info'
  }
}

// 获取状态标签文本
const getStatusLabel = (status: string) => {
  switch (status) {
    case 'OPEN': return '开启'
    case 'CLOSED': return '已关闭'
    case 'ACKNOWLEDGED': return '已确认'
    default: return status
  }
}

// 获取告警类型标签类型
const getAlertTypeTagType = (type: string) => {
  switch (type) {
    case 'HEALTH_CHECK_FAILED': return 'danger'
    case 'RESPONSE_TIME_SLOW': return 'warning'
    case 'SERVICE_UNAVAILABLE': return 'danger'
    case 'CONNECTION_TIMEOUT': return 'warning'
    default: return 'info'
  }
}

// 获取告警类型标签文本
const getAlertTypeLabel = (type: string) => {
  switch (type) {
    case 'HEALTH_CHECK_FAILED': return '健康检查失败'
    case 'RESPONSE_TIME_SLOW': return '响应时间过慢'
    case 'SERVICE_UNAVAILABLE': return '服务不可用'
    case 'CONNECTION_TIMEOUT': return '连接超时'
    default: return type
  }
}

// 确认告警
const acknowledgeAlert = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要确认告警 "${row.title}" 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await alertApi.updateAlert({
      uuid: row.uuid,
      status: 'ACKNOWLEDGED'
    })
    
    ElMessage.success('告警确认成功')
    fetchAlerts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('确认告警失败:', error)
      ElMessage.error('确认告警失败')
    }
  }
}

// 关闭告警
const closeAlert = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要关闭告警 "${row.title}" 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await alertApi.updateAlert({
      uuid: row.uuid,
      status: 'CLOSED'
    })
    
    ElMessage.success('告警关闭成功')
    fetchAlerts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('关闭告警失败:', error)
      ElMessage.error('关闭告警失败')
    }
  }
}

// 查看告警详情
const viewAlertDetail = (row: any) => {
  selectedAlert.value = row
  detailDialogVisible.value = true
}

// 关闭详情对话框
const closeDetailDialog = () => {
  detailDialogVisible.value = false
  selectedAlert.value = null
}

// 页面挂载时获取数据
onMounted(async () => {
  await fetchAlertTypes()  // 先获取告警类型
  fetchAlerts()  // 再获取告警列表
})
</script>

<style scoped>
.alerts-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  text-align: right;
}

.dialog-footer {
  text-align: right;
}

.alert-detail-content {
  max-height: 60vh;
  overflow-y: auto;
}

.alert-description {
  white-space: pre-wrap;
  font-family: inherit;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  margin: 0;
}
</style>