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
        <el-table-column prop="basic_info_list" label="主机信息" width="300">
          <template #default="scope">
            <div v-for="(info, index) in scope.row.basic_info_list" :key="index" class="host-info">
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
            </div>
            <span v-if="!scope.row.basic_info_list || scope.row.basic_info_list.length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="link.name" label="所属链路" width="200" />
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
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nodeApi } from '@/api/monitor'
import { useRouter } from 'vue-router'

// 定义响应式数据
const loading = ref(false)
const router = useRouter()

// 表格数据
const nodes = ref<any[]>([])

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