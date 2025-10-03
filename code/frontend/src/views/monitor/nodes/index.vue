<template>
  <div class="monitor-page" v-if="hasPerms('monitor:read')">
    <!-- 搜索区域 -->
    <el-card class="search-card">
      <div class="search-form">
        <div class="form-item">
          <span class="label">关键词</span>
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索节点名称"
            clearable
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </div>

        <div class="form-item button-group">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button 
            type="primary" 
            @click="handleAdd"
            v-if="hasPerms('monitor:create')"
          >新增节点</el-button>
        </div>
      </div>
    </el-card>

    <!-- 表格区域 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="nodeList"
        style="width: 100%"
      >
        <el-table-column prop="name" label="节点名称" />
        <el-table-column prop="link.name" label="所属架构图" />
        <el-table-column label="基础信息" width="300">
          <template #default="scope">
            <div v-for="(info, index) in scope.row.basic_info_list" :key="index" class="basic-info">
              <span v-if="info.host">{{ info.host }}</span>
              <span v-if="info.port" class="port">:{{ info.port }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="健康状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_healthy ? 'success' : 'danger'">
              {{ scope.row.is_healthy ? '健康' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleTest(scope.row)">测试连通性</el-button>
            <el-button type="info" size="small" @click="handleViewDetail(scope.row)">查看详情</el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleDelete(scope.row)" 
              v-if="hasPerms('monitor:delete')"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增节点' : '编辑节点'"
      width="50%"
    >
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="节点名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入节点名称" />
        </el-form-item>
        <el-form-item label="所属架构图" prop="link">
          <el-select v-model="form.link" placeholder="请选择架构图" style="width: 100%">
            <el-option
              v-for="item in diagrams"
              :key="item.uuid"
              :label="item.name"
              :value="item.uuid"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="基础信息">
          <el-button @click="addBasicInfo" size="small">添加信息</el-button>
          <div v-for="(info, index) in form.basic_info_list" :key="index" class="basic-info-form">
            <el-input 
              v-model="info.host" 
              placeholder="主机" 
              size="small"
              style="width: 40%; margin-right: 10px;"
            />
            <el-input 
              v-model="info.port" 
              placeholder="端口" 
              size="small"
              type="number"
              style="width: 30%; margin-right: 10px;"
            />
            <el-button @click="removeBasicInfo(index)" size="small" type="danger">删除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 节点详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="节点详情"
      width="60%"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="节点名称">
          {{ currentDetail.name }}
        </el-descriptions-item>
        <el-descriptions-item label="所属架构图">
          {{ currentDetail.link_name }}
        </el-descriptions-item>
        <el-descriptions-item label="健康状态">
          <el-tag :type="currentDetail.is_healthy ? 'success' : 'danger'">
            {{ currentDetail.is_healthy ? '健康' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentDetail.is_active ? 'success' : 'info'">
            {{ currentDetail.is_active ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="基础信息">
          <div v-for="(info, index) in currentDetail.basic_info_list" :key="index">
            <span v-if="info.host">{{ info.host }}</span>
            <span v-if="info.port" class="port">:{{ info.port }}</span>
            <br v-if="index < currentDetail.basic_info_list.length - 1" />
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ currentDetail.create_time }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ currentDetail.update_time }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="handleEditFromDetail">编辑</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { http } from '@/utils/http'
import { apiMap } from '@/config/api'
import { hasPerms } from "@/utils/auth";
import { Search } from '@element-plus/icons-vue'
import '@/style/system.scss'
import { nodeApi, linkApi } from '@/api/monitor'

interface NodeForm {
  uuid?: string
  name: string
  link: string
  basic_info_list: Array<{
    host?: string
    port?: number
  }>
  is_active: boolean
}

const nodeList = ref([])
const diagrams = ref([])
const dialogVisible = ref(false)
const detailDialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const formRef = ref<FormInstance>()
const form = ref<NodeForm>({
  name: '',
  link: '',
  basic_info_list: [],
  is_active: true
})
const currentDetail = ref<any>(null)

const rules = {
  name: [
    { required: true, message: '请输入节点名称', trigger: 'blur' }
  ],
  link: [
    { required: true, message: '请选择架构图', trigger: 'change' }
  ]
}

const loading = ref(false)

// 分页相关
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 搜索相关
const searchForm = ref({
  keyword: ''
})

// 获取节点列表
const getNodeList = async () => {
  try {
    loading.value = true
    const params = {
      page: page.value,
      page_size: pageSize.value,
      search: searchForm.value.keyword
    }
    const res = await nodeApi.getNodes(params)
    if (res.success) {
      nodeList.value = res.data.results || []
      total.value = res.data.count || 0
    } else {
      ElMessage.error(res.msg || '获取节点列表失败')
    }
  } catch (error) {
    ElMessage.error('获取节点列表失败')
  } finally {
    loading.value = false
  }
}

// 获取架构图列表
const getDiagramList = async () => {
  try {
    const res = await linkApi.getLinks({ link_type: 'architecture' })
    if (res.success) {
      diagrams.value = res.data.results || []
    } else {
      ElMessage.error(res.msg || '获取架构图列表失败')
    }
  } catch (error) {
    ElMessage.error('获取架构图列表失败')
  }
}

// 新增节点
const handleAdd = () => {
  dialogType.value = 'add'
  form.value = {
    name: '',
    link: '',
    basic_info_list: [],
    is_active: true
  }
  dialogVisible.value = true
}

// 查看详情
const handleViewDetail = async (row: any) => {
  try {
    // 为了显示架构图名称，我们需要获取完整节点信息
    const res = await nodeApi.getNode(row.uuid)
    if (res.success) {
      currentDetail.value = res.data
      detailDialogVisible.value = true
    } else {
      ElMessage.error(res.msg || '获取节点详情失败')
    }
  } catch (error) {
    ElMessage.error('获取节点详情失败')
  }
}

// 编辑详情对话框中的节点
const handleEditFromDetail = () => {
  // 将详情数据复制到表单
  form.value = {
    uuid: currentDetail.value.uuid,
    name: currentDetail.value.name,
    link: currentDetail.value.link,
    basic_info_list: currentDetail.value.basic_info_list,
    is_active: currentDetail.value.is_active
  }
  dialogType.value = 'edit'
  detailDialogVisible.value = false
  dialogVisible.value = true
}

// 删除节点
const handleDelete = (row: any) => {
  ElMessageBox.confirm('确定删除该节点吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      const res = await nodeApi.deleteNode(row.uuid)
      if (res.success) {
        ElMessage.success('删除成功')
        getNodeList()
      } else {
        ElMessage.error(res.msg || '删除失败')
      }
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 测试节点连通性
const handleTest = (row: any) => {
  ElMessage.info(`正在测试节点 ${row.name} 的连通性...`)
  // 这里可以调用API来测试节点健康状态
  nodeApi.getNodeHealth(row.uuid).then(res => {
    if (res.success) {
      ElMessage.success(`节点 ${row.name} 测试结果: ${res.data.is_healthy ? '健康' : '异常'}`)
    } else {
      ElMessage.error('测试失败')
    }
  }).catch(() => {
    ElMessage.error('测试失败')
  })
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        let res: any
        if (dialogType.value === 'add') {
          res = await nodeApi.createNode(form.value)
        } else {
          if (!form.value.uuid) {
            ElMessage.error('节点信息不完整')
            return
          }
          res = await nodeApi.updateNode(form.value.uuid, form.value)
        }
        
        if (res.success) {
          ElMessage.success(dialogType.value === 'add' ? '新增成功' : '编辑成功')
          dialogVisible.value = false
          getNodeList()
        } else {
          ElMessage.error(res.msg || (dialogType.value === 'add' ? '新增失败' : '编辑失败'))
        }
      } catch (error) {
        ElMessage.error(dialogType.value === 'add' ? '新增失败' : '编辑失败')
      }
    }
  })
}

// 添加基础信息
const addBasicInfo = () => {
  form.value.basic_info_list.push({ host: '', port: undefined })
}

// 删除基础信息
const removeBasicInfo = (index: number) => {
  if (form.value.basic_info_list.length > 1) {
    form.value.basic_info_list.splice(index, 1)
  } else {
    // 如果只剩一个，清空而不是删除，确保至少有一个空项
    form.value.basic_info_list[0] = { host: '', port: undefined }
  }
}

// 处理搜索
const handleSearch = () => {
  page.value = 1
  getNodeList()
}

// 处理页码改变
const handleCurrentChange = (val: number) => {
  page.value = val
  getNodeList()
}

// 处理每页条数改变
const handleSizeChange = (val: number) => {
  pageSize.value = val
  page.value = 1
  getNodeList()
}

// 重置搜索
const resetSearch = () => {
  searchForm.value.keyword = ''
  page.value = 1
  getNodeList()
}

onMounted(() => {
  if (!hasPerms('monitor:read')) {
    ElMessage.error('您没有权限查看节点列表')
    return
  }
  getNodeList()
  getDiagramList()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-box {
  margin-left: 20px;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

.basic-info {
  margin: 2px 0;
}

.basic-info .port {
  color: #909399;
}

.basic-info-form {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
</style>