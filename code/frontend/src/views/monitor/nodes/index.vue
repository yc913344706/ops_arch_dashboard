<template>
  <div class="nodes-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点管理</span>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-form :model="filterForm" inline>
          <el-form-item label="搜索">
            <el-input 
              v-model="filterForm.search" 
              placeholder="输入节点名称/主机Host/主机Port" 
              clearable
              style="width: 300px;"
              @keyup.enter="fetchNodes" />
          </el-form-item>
          <el-form-item label="健康状态">
            <el-select 
              v-model="filterForm.healthy_status" 
              placeholder="选择健康状态" 
              clearable
              style="width: 150px;">
              <el-option label="未知" value="unknown" />
              <el-option label="健康" value="green" />
              <el-option label="部分异常" value="yellow" />
              <el-option label="严重异常" value="red" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchNodes">搜索</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <el-table :data="nodes" v-loading="loading">
        <el-table-column prop="name" label="节点名称" width="200" />
        <el-table-column label="主机信息" width="350">
          <template #default="scope">
            <div v-for="(info, index) in getBasicInfoList(scope.row)" :key="index" class="host-info">
              <span v-if="info.host">主机: {{ info.host }}</span>
              <span v-if="info.port" class="port-info">端口: {{ info.port }}</span>
              <el-tag 
                v-if="typeof info.is_healthy !== 'undefined'"
                :type="info.is_healthy === true ? 'success' : info.is_healthy === false ? 'danger' : 'info'"
                size="small"
                style="width: 20px; height: 20px; border-radius: 50%; margin-right: 8px; display: flex; align-items: center; justify-content: center;"
              >
                <span v-if="info.is_healthy === true" style="font-size: 12px;">✓</span>
                <span v-else-if="info.is_healthy === false" style="font-size: 12px;">✗</span>
                <span v-else style="font-size: 12px;">?</span>
              </el-tag>
              <el-tag 
                v-if="info.is_ping_disabled"
                type="warning"
                size="small"
                style="margin-left: 5px;"
              >
                禁Ping
              </el-tag>
            </div>
            <span v-if="!getBasicInfoList(scope.row) || getBasicInfoList(scope.row).length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="link.name" label="所属链路" min-width="200" />
        <el-table-column label="健康状态" width="120">
          <template #default="scope">
            <el-tag 
              :type="getHealthStatusType(scope.row.healthy_status)"
              :effect="scope.row.healthy_status === 'red' ? 'dark' : 'light'"
            >
              {{ getHealthStatusText(scope.row.healthy_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewNodeDetail(scope.row)"
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
    
    <!-- 节点详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="节点详情" 
      width="60%" 
      :before-close="closeDetailDialog"
    >
      <div v-if="selectedNode" class="node-detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="节点名称">{{ selectedNode.name }}</el-descriptions-item>
          <el-descriptions-item label="所属链路">{{ selectedNode.link.name }}</el-descriptions-item>
          <el-descriptions-item label="健康状态">
            <el-tag 
              :type="getHealthStatusType(selectedNode.healthy_status)"
              :effect="selectedNode.healthy_status === 'red' ? 'dark' : 'light'"
            >
              {{ getHealthStatusText(selectedNode.healthy_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最近一次状态收集时间">
            {{ selectedNode.last_check_time || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态收集耗时">
            <span v-if="selectedNode.check_duration_ms !== null">{{ selectedNode.check_duration_ms.toFixed(2) }} ms</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ selectedNode.create_time }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ selectedNode.update_time }}</el-descriptions-item>
          <el-descriptions-item label="主机信息" :span="2">
            <div v-for="(info, index) in getBasicInfoList(selectedNode)" :key="index" class="host-info">
              <span v-if="info.host">主机: {{ info.host }}</span>
              <span v-if="info.port" class="port-info">端口: {{ info.port }}</span>
              <el-tag 
                v-if="typeof info.is_healthy !== 'undefined'"
                :type="info.is_healthy === true ? 'success' : info.is_healthy === false ? 'danger' : 'info'"
                size="small"
                style="width: 20px; height: 20px; border-radius: 50%; margin-right: 8px; display: flex; align-items: center; justify-content: center;"
              >
                <span v-if="info.is_healthy === true" style="font-size: 12px;">✓</span>
                <span v-else-if="info.is_healthy === false" style="font-size: 12px;">✗</span>
                <span v-else style="font-size: 12px;">?</span>
              </el-tag>
              <el-tag 
                v-if="info.is_ping_disabled"
                type="warning"
                size="small"
                style="margin-left: 5px;"
              >
                禁Ping
              </el-tag>
            </div>
            <span v-if="!getBasicInfoList(selectedNode) || getBasicInfoList(selectedNode).length === 0">-</span>
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
import { nodeApi } from '@/api/monitor'
import { useRouter } from 'vue-router'

// 定义响应式数据
const loading = ref(false)
const detailDialogVisible = ref(false)
const router = useRouter()

// 表格数据
const nodes = ref<any[]>([])
// 选中的节点
const selectedNode = ref<any>(null)

// 分页信息
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 筛选表单
const filterForm = reactive({
  search: '',
  healthy_status: ''
})

// 获取节点列表
const fetchNodes = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: filterForm.search,
      healthy_status: filterForm.healthy_status
    }
    const response = await nodeApi.getNodes(params)
    console.log('Node list response:', response.data)
    nodes.value = response.data.data || []
    pagination.total = response.data.all_num || 0
  } catch (error) {
    console.error('获取节点列表失败:', error)
    ElMessage.error('获取节点列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterForm.search = ''
  filterForm.healthy_status = ''
  fetchNodes()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchNodes()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.currentPage = page
  fetchNodes()
}

// 获取健康状态文本
const getHealthStatusText = (status: string) => {
  const statusMap: { [key: string]: string } = {
    'green': '健康',
    'yellow': '部分异常',
    'red': '严重异常',
    'unknown': '未知'
  }
  return statusMap[status] || status
}

// 获取健康状态类型
const getHealthStatusType = (status: string) => {
  const typeMap: { [key: string]: string } = {
    'green': 'success',
    'yellow': 'warning',
    'red': 'danger',
    'unknown': 'info'
  }
  return typeMap[status] || 'info'
}

// 获取基础信息列表
const getBasicInfoList = (node: any) => {
  console.log('getBasicInfoList called in nodes page with node:', node)
  if (node && node.base_info_list) {
    console.log('base_info_list found in nodes page:', node.base_info_list)
    return node.base_info_list
  }
  console.log('base_info_list not found or is null/undefined in nodes page')
  return []
}

// 查看节点详情
const viewNodeDetail = (row: any) => {
  selectedNode.value = row
  detailDialogVisible.value = true
}

// 关闭详情对话框
const closeDetailDialog = () => {
  detailDialogVisible.value = false
  selectedNode.value = null
}

// 页面挂载时获取数据
onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.nodes-page {
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

.host-info {
  margin-bottom: 4px;
  display: flex;
  gap: 10px;
}

.port-info {
  margin-left: 8px;
  color: #909399;
}
</style>