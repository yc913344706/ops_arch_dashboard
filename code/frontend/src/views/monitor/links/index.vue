<template>
  <div class="links-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>链路管理</span>
          <el-button type="primary" @click="showCreateDialog">新建链路</el-button>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-form :model="filterForm" inline>
          <el-form-item label="链路名称">
            <el-input 
              v-model="filterForm.name" 
              placeholder="输入链路名称" 
              clearable
              @keyup.enter="fetchLinks" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterForm.isActive" placeholder="选择状态" clearable style="width: 120px;">
              <el-option label="启用" :value="true" />
              <el-option label="禁用" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchLinks">搜索</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <el-table :data="links" v-loading="loading">
        <el-table-column prop="name" label="链路名称" width="200" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by.nickname" label="创建者" width="120" />
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <!-- <el-button size="small" @click="viewTopology(scope.row)">拓扑图</el-button> -->
            <el-button size="small" @click="editLink(scope.row)">编辑</el-button>
            <el-button 
              size="small" 
              :type="scope.row.is_active ? 'warning' : 'success'" 
              @click="toggleStatus(scope.row)">
              {{ scope.row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteLink(scope.row)">
              删除
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
    
    <!-- 创建/编辑链路对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle" 
      width="500px"
      :before-close="handleCloseDialog"
    >
      <el-form 
        :model="linkForm" 
        :rules="linkFormRules" 
        ref="linkFormRef"
        label-width="100px"
      >
        <el-form-item label="链路名称" prop="name">
          <el-input v-model="linkForm.name" placeholder="请输入链路名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="linkForm.description" 
            type="textarea" 
            placeholder="请输入链路描述" 
            :rows="3" />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch
            v-model="linkForm.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCloseDialog">取消</el-button>
          <el-button type="primary" @click="submitLinkForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { linkApi } from '@/api/monitor'
import { computed } from 'vue'

// 定义响应式数据
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)

// 表格数据
const links = ref<any[]>([])

// 分页信息
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 筛选表单
const filterForm = reactive({
  name: '',
  type: '',
  isActive: null
})

// 链路表单
const linkForm = reactive({
  uuid: '',
  name: '',
  description: '',
  is_active: true
})

// 表单验证规则
const linkFormRules = {
  name: [
    { required: true, message: '请输入链路名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],

}

// 表单引用
const linkFormRef = ref()

// 计算属性
const dialogTitle = computed(() => isEdit.value ? '编辑链路' : '新建链路')



// 获取链路列表
const fetchLinks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      size: pagination.pageSize,
      search: filterForm.name,

      is_active: filterForm.isActive
    }
    const response = await linkApi.getLinks(params)
    links.value = response.data.data || []
    pagination.total = response.data.all_num || 0
  } catch (error) {
    console.error('获取链路列表失败:', error)
    ElMessage.error('获取链路列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterForm.name = ''
  filterForm.type = ''
  filterForm.isActive = null
  fetchLinks()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchLinks()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.currentPage = page
  fetchLinks()
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  resetLinkForm()
  dialogVisible.value = true
}

// 编辑链路
const editLink = (row: any) => {
  isEdit.value = true
  Object.assign(linkForm, row)
  dialogVisible.value = true
}

// 查看拓扑
const viewTopology = (row: any) => {
  // 这里应该跳转到链路详情页面
  console.log('查看链路拓扑:', row)
}

// 切换状态
const toggleStatus = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要${row.is_active ? '禁用' : '启用'}此链路吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用API更新状态
    await linkApi.updateLink({
      ...row,
      uuid: row.uuid,
      is_active: !row.is_active
    })
    
    ElMessage.success(`${row.is_active ? '禁用' : '启用'}成功`)
    fetchLinks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换状态失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

// 删除链路
const deleteLink = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      '此操作将永久删除该链路，是否继续？',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await linkApi.deleteLink({uuid: row.uuid})
    ElMessage.success('删除成功')
    fetchLinks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除链路失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 重置链路表单
const resetLinkForm = () => {
  linkForm.uuid = ''
  linkForm.name = ''
  linkForm.description = ''
  linkForm.is_active = true
}

// 提交链路表单
const submitLinkForm = async () => {
  if (!linkFormRef.value) return
  
  await linkFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await linkApi.updateLink({
            uuid: linkForm.uuid,
            name: linkForm.name,
            description: linkForm.description,
            is_active: linkForm.is_active
          })
          ElMessage.success('更新成功')
        } else {
          await linkApi.createLink({
            name: linkForm.name,
            description: linkForm.description,
            is_active: linkForm.is_active
          })
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchLinks()
      } catch (error) {
        console.error('保存链路失败:', error)
        ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
      }
    }
  })
}

// 关闭对话框
const handleCloseDialog = () => {
  dialogVisible.value = false
  if (linkFormRef.value) {
    linkFormRef.value.clearValidate()
  }
}

// 页面挂载时获取数据
onMounted(() => {
  fetchLinks()
})
</script>

<style scoped>
.links-page {
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
</style>