<template>
  <div class="baseinfo-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础信息管理</span>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-form :model="filterForm" inline>
          <el-form-item label="主机地址">
            <el-input 
              v-model="filterForm.host" 
              placeholder="输入主机地址" 
              clearable
              @keyup.enter="fetchBaseInfoList" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input 
              v-model="filterForm.port" 
              placeholder="输入端口" 
              type="number"
              clearable
              @keyup.enter="fetchBaseInfoList" />
          </el-form-item>
          <el-form-item label="节点名称">
            <el-input 
              v-model="filterForm.nodeName" 
              placeholder="输入节点名称" 
              clearable
              @keyup.enter="fetchBaseInfoList" />
          </el-form-item>
          <el-form-item label="链路名称">
            <el-input 
              v-model="filterForm.linkName" 
              placeholder="输入链路名称" 
              clearable
              @keyup.enter="fetchBaseInfoList" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchBaseInfoList">搜索</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <el-table :data="baseInfoList" v-loading="loading">
        <el-table-column prop="host" label="主机地址" width="200" />
        <el-table-column prop="port" label="端口" width="100" />
        <el-table-column prop="is_ping_disabled" label="禁Ping" width="100">
          <template #default="scope">
            <el-tag 
              :type="scope.row.is_ping_disabled ? 'warning' : 'success'"
              size="small"
            >
              {{ scope.row.is_ping_disabled ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_healthy" label="健康状态" width="120">
          <template #default="scope">
            <el-tag 
              :type="getHealthStatusType(scope.row.is_healthy)"
              size="small"
            >
              {{ getHealthStatusText(scope.row.is_healthy) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remarks" label="备注" show-overflow-tooltip />
        <el-table-column prop="node.name" label="所属节点" width="150" />
        <el-table-column prop="node.link.name" label="所属链路" width="150" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="goToNodeInEditor(scope.row.node.uuid)"
            >
              在架构图中查看
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { nodeApi } from '@/api/monitor'
import { useRouter } from 'vue-router'

// 定义响应式数据
const loading = ref(false)
const router = useRouter()

// 表格数据
const baseInfoList = ref<any[]>([])

// 分页信息
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 筛选表单
const filterForm = reactive({
  host: '',
  port: '',
  nodeName: '',
  linkName: ''
})

// 获取基础信息列表
const fetchBaseInfoList = async () => {
  loading.value = true
  try {
    // 由于后端API可能需要通过节点接口获取数据，我们获取所有节点然后过滤
    const response = await nodeApi.getNodes({
      page: 1,
      page_size: 10000 // 获取所有节点
    })
    
    const allNodes = response.data.data || []
    
    // 过滤并展开 base_info_list 数据
    let filteredData: any[] = []
    let seenHostPorts = new Set() // 用于跟踪已处理的 host:port 组合
    
    console.log('All nodes for baseinfo:', allNodes)
    allNodes.forEach(node => {
      const nodeMatches = !filterForm.nodeName || node.name.toLowerCase().includes(filterForm.nodeName.toLowerCase())
      const linkMatches = !filterForm.linkName || node.link.name.toLowerCase().includes(filterForm.linkName.toLowerCase())
      
      if (nodeMatches && linkMatches) {
        console.log('Processing node:', node.name, 'base_info_list:', node.base_info_list)
        const nodeBaseInfoList = node.base_info_list || []
        nodeBaseInfoList.forEach((baseInfo: any) => {
          const hostPortKey = `${baseInfo.host}:${baseInfo.port || 'null'}`
          const hostMatches = !filterForm.host || (baseInfo.host && baseInfo.host.toLowerCase().includes(filterForm.host.toLowerCase()))
          const portMatches = !filterForm.port || (baseInfo.port !== null && baseInfo.port !== undefined && String(baseInfo.port).includes(filterForm.port))
          
          console.log('Base info item:', baseInfo, 'hostMatches:', hostMatches, 'portMatches:', portMatches)
          
          if (hostMatches && portMatches) {
            // 添加到结果前检查是否已存在相同的 host:port
            if (!seenHostPorts.has(hostPortKey)) {
              seenHostPorts.add(hostPortKey)
              filteredData.push({
                ...baseInfo,
                node: node
              })
            } else {
              // 如果已存在相同的 host:port，可以选择合并或跳过
              // 这里我们只保留首次出现的，以避免重复显示
              console.log(`Duplicate host:port ${hostPortKey} found, skipping`)
            }
          }
        })
      }
    })
    
    // 分页处理
    const start = (pagination.currentPage - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    baseInfoList.value = filteredData.slice(start, end)
    pagination.total = filteredData.length
    
  } catch (error) {
    console.error('获取基础信息列表失败:', error)
    ElMessage.error('获取基础信息列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterForm.host = ''
  filterForm.port = ''
  filterForm.nodeName = ''
  filterForm.linkName = ''
  fetchBaseInfoList()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchBaseInfoList()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.currentPage = page
  fetchBaseInfoList()
}

// 跳转到指定节点的架构图编辑页面
const goToNodeInEditor = (nodeId: string) => {
  // 简单地跳转到架构图页面，实际实现需要根据具体路由设计
  router.push({ path: '/monitor/links' })
  ElMessage.info('请在架构图页面中搜索该节点')
}

// 获取健康状态类型
const getHealthStatusType = (is_healthy: boolean | null) => {
  if (is_healthy === true) {
    return 'success' // 健康
  } else if (is_healthy === false) {
    return 'danger' // 不健康
  } else {
    return 'info' // 未知状态
  }
}

// 获取健康状态文本
const getHealthStatusText = (is_healthy: boolean | null) => {
  if (is_healthy === true) {
    return '健康'
  } else if (is_healthy === false) {
    return '异常'
  } else {
    return '未知'
  }
}

// 页面挂载时获取数据
onMounted(() => {
  fetchBaseInfoList()
})
</script>

<style scoped>
.baseinfo-page {
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
</style>