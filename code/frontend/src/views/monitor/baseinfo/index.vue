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
        <el-table-column prop="remarks" label="备注" show-overflow-tooltip width="200" />
        <el-table-column label="关联节点" width="200">
          <template #default="scope">
            <div v-for="node in scope.row.nodes" :key="node.uuid" class="node-item">
              <el-tag type="info" size="small" style="margin-right: 4px; margin-bottom: 2px;">
                {{ node.name }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="所属链路" width="150">
          <template #default="scope">
            <div v-for="node in scope.row.nodes" :key="node.uuid" class="link-item">
              <el-tag type="success" size="small" style="margin-right: 4px; margin-bottom: 2px;">
                {{ node.link.name }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <!-- <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="editRemark(scope.row)"
            >
              修改备注
            </el-button>
          </template>
        </el-table-column> -->
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
    
    <!-- 修改备注对话框 -->
    <el-dialog 
      v-model="showRemarkDialog" 
      title="修改备注" 
      width="500px"
      :before-close="() => { showRemarkDialog = false }"
    >
      <el-form>
        <el-form-item label="备注">
          <el-input
            v-model="remarkForm.remarks"
            :rows="4"
            type="textarea"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showRemarkDialog = false">取消</el-button>
          <el-button type="primary" @click="saveRemark">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { baseInfoApi } from '@/api/monitor'
import { useRouter } from 'vue-router'

// 定义响应式数据
const loading = ref(false)
const router = useRouter()

// 弹窗相关数据
const showRemarkDialog = ref(false)
const currentBaseInfo = ref<any>(null)
const remarkForm = reactive({
  remarks: ''
})

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
  nodeName: '',  // 实际不会用于新API，但保留以兼容前端界面
  linkName: ''   // 实际不会用于新API，但保留以兼容前端界面
})

// 获取基础信息列表
const fetchBaseInfoList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: filterForm.host || filterForm.port ? '' : '', // 如果有host或port过滤，不使用通用搜索
      host: filterForm.host,
      port: filterForm.port ? Number(filterForm.port) : null,
    }
    
    const response = await baseInfoApi.getBaseInfoList(params)
    baseInfoList.value = response.data.data || []
    pagination.total = response.data.all_num || 0
    
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

// 编辑备注
const editRemark = (row: any) => {
  currentBaseInfo.value = { ...row }
  remarkForm.remarks = row.remarks || ''
  showRemarkDialog.value = true
}

// 保存备注
const saveRemark = async () => {
  if (!currentBaseInfo.value) return
  
  try {
    await baseInfoApi.updateBaseInfo({
      uuid: currentBaseInfo.value.uuid,
      remarks: remarkForm.remarks
    })
    
    // 更新本地数据
    const index = baseInfoList.value.findIndex(item => item.uuid === currentBaseInfo.value.uuid)
    if (index !== -1) {
      baseInfoList.value[index].remarks = remarkForm.remarks
    }
    
    showRemarkDialog.value = false
    ElMessage.success('备注更新成功')
  } catch (error) {
    console.error('更新备注失败:', error)
    ElMessage.error('更新备注失败')
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