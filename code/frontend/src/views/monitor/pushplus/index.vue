<template>
  <div class="pushplus-config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>PushPlus 配置管理</span>
          <el-button type="primary" @click="showCreateDialog">新建配置</el-button>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-form :model="filterForm" inline>
          <el-form-item label="配置名称">
            <el-input 
              v-model="filterForm.name" 
              placeholder="输入配置名称" 
              clearable
              @keyup.enter="fetchConfigs" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterForm.enabled" placeholder="选择状态" clearable style="width: 120px;">
              <el-option label="启用" :value="true" />
              <el-option label="禁用" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchConfigs">搜索</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <el-table :data="configs" v-loading="loading">
        <el-table-column prop="name" label="配置名称" width="200" />
        <el-table-column prop="title_prefix" label="标题前缀" width="150" show-overflow-tooltip />
        <el-table-column prop="msg_type" label="消息类型" width="120">
          <template #default="scope">
            <el-tag :type="getMsgTypeTagType(scope.row.msg_type)">
              {{ getMsgTypeLabel(scope.row.msg_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="template_type" label="模板类型" width="120">
          <template #default="scope">
            <el-tag :type="getTemplateTypeTagType(scope.row.template_type)">
              {{ getTemplateTypeLabel(scope.row.template_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">
              {{ scope.row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="220">
          <template #default="scope">
            <el-button size="small" @click="editConfig(scope.row)">编辑</el-button>
            <el-button 
              size="small" 
              :type="scope.row.enabled ? 'warning' : 'success'" 
              @click="toggleStatus(scope.row)">
              {{ scope.row.enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              size="small" 
              type="info" 
              @click="testConfig(scope.row)">
              测试
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteConfig(scope.row)">
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
    
    <!-- 创建/编辑配置对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle" 
      width="800px"
      :before-close="handleCloseDialog"
      :destroy-on-close="true"
    >
      <el-form 
        :model="configForm" 
        :rules="configFormRules" 
        ref="configFormRef"
        label-width="120px"
        style="max-height: 600px; overflow-y: auto;"
      >
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="configForm.name" placeholder="请输入配置名称" />
        </el-form-item>
        
        <el-form-item label="Token" prop="token">
          <el-input 
            v-model="configForm.token" 
            type="password"
            show-password
            placeholder="请输入PushPlus Token" />
        </el-form-item>
        
        <el-form-item label="标题前缀">
          <el-input v-model="configForm.title_prefix" placeholder="推送消息标题前缀" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch
            v-model="configForm.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
        
        <el-form-item label="消息类型" prop="msg_type">
          <el-select v-model="configForm.msg_type" placeholder="选择消息类型">
            <el-option label="文本消息(txt)" value="txt" />
            <el-option label="HTML消息(html)" value="html" />
            <el-option label="Markdown消息(markdown)" value="markdown" />
            <el-option label="JSON消息(json)" value="json" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="模板类型" prop="template_type">
          <el-select v-model="configForm.template_type" placeholder="选择模板类型">
            <el-option label="告警消息模板" value="alert" />
            <el-option label="通知消息模板" value="notification" />
            <el-option label="自定义消息模板" value="custom" />
          </el-select>
        </el-form-item>
        
        <el-form-item 
          v-if="configForm.template_type === 'custom'"
          label="内容模板" prop="content_template">
          <el-input 
            v-model="configForm.content_template" 
            type="textarea" 
            :rows="5"
            placeholder="消息内容模板，支持变量替换：{title}, {description}, {node_name}, {severity} 等" />
          <div class="template-help">
            <p>可用变量：</p>
            <ul>
              <li><code>{title}</code> - 告警标题</li>
              <li><code>{description}</code> - 告警描述</li>
              <li><code>{node_name}</code> - 节点名称</li>
              <li><code>{severity}</code> - 严重程度</li>
              <li><code>{alert_type}</code> - 告警类型</li>
              <li><code>{first_occurred}</code> - 首次发生时间</li>
              <li><code>{last_occurred}</code> - 最后发生时间</li>
            </ul>
          </div>
        </el-form-item>
        
        <el-form-item label="应用到所有告警">
          <el-switch
            v-model="configForm.apply_to_all_alerts"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
        
        <el-form-item 
          v-if="!configForm.apply_to_all_alerts"
          label="告警级别过滤">
          <el-checkbox-group v-model="configForm.alert_severity_filter">
            <el-checkbox label="LOW">低</el-checkbox>
            <el-checkbox label="MEDIUM">中</el-checkbox>
            <el-checkbox label="HIGH">高</el-checkbox>
            <el-checkbox label="CRITICAL">严重</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="订阅组列表">
          <el-input 
            v-model="configForm.topic_list_str" 
            type="textarea" 
            :rows="2"
            placeholder="请输入订阅组ID，多个用逗号分隔" />
        </el-form-item>
        
        <el-form-item label="Webhook列表">
          <el-input 
            v-model="configForm.webhook_list_str" 
            type="textarea" 
            :rows="2"
            placeholder="请输入Webhook URL，多个用逗号分隔" />
          </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCloseDialog">取消</el-button>
          <el-button type="primary" @click="submitConfigForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 测试配置对话框 -->
    <el-dialog 
      v-model="testDialogVisible" 
      title="测试配置" 
      width="600px"
      :before-close="closeTestDialog"
    >
      <el-form :model="testForm" label-width="100px">
        <el-form-item label="测试标题">
          <el-input v-model="testForm.title" placeholder="测试消息标题" />
        </el-form-item>
        <el-form-item label="测试内容">
          <el-input 
            v-model="testForm.content" 
            type="textarea" 
            :rows="4"
            placeholder="测试消息内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeTestDialog">取消</el-button>
          <el-button type="primary" @click="sendTestMessage" :loading="testLoading">发送测试</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { pushPlusConfigApi } from '@/api/monitor'

// 响应式数据
const loading = ref(false)
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const testLoading = ref(false)
const isEdit = ref(false)

// 表格数据
const configs = ref<any[]>([])

// 分页信息
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 筛选表单
const filterForm = reactive({
  name: '',
  enabled: null
})

// 配置表单
const configForm = reactive({
  uuid: '',
  name: '',
  token: '',
  title_prefix: '',
  enabled: true,
  msg_type: 'txt',
  template_type: 'alert',
  content_template: '',
  apply_to_all_alerts: true,
  alert_severity_filter: [] as string[],
  topic_list_str: '', // 以逗号分隔的字符串形式存储
  webhook_list_str: '' // 以逗号分隔的字符串形式存储
})

// 测试表单
const testForm = reactive({
  title: 'PushPlus测试消息',
  content: '这是一条测试消息',
  token: ''
})

// 表单引用
const configFormRef = ref()

// 表单验证规则
const configFormRules = {
  name: [
    { required: true, message: '请输入配置名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  token: [
    { required: true, message: '请输入PushPlus Token', trigger: 'blur' }
  ],
  msg_type: [
    { required: true, message: '请选择消息类型', trigger: 'change' }
  ],
  template_type: [
    { required: true, message: '请选择模板类型', trigger: 'change' }
  ]
}

// 计算属性
const dialogTitle = computed(() => isEdit.value ? '编辑配置' : '新建配置')

// 获取消息类型标签类型
const getMsgTypeTagType = (msgType: string) => {
  const typeMap: Record<string, string> = {
    'txt': 'info',
    'html': 'warning',
    'markdown': 'success',
    'json': 'primary'
  }
  return typeMap[msgType] || 'info'
}

// 获取消息类型标签文本
const getMsgTypeLabel = (msgType: string) => {
  const labelMap: Record<string, string> = {
    'txt': '文本',
    'html': 'HTML',
    'markdown': 'Markdown',
    'json': 'JSON'
  }
  return labelMap[msgType] || msgType
}

// 获取模板类型标签类型
const getTemplateTypeTagType = (templateType: string) => {
  const typeMap: Record<string, string> = {
    'alert': 'danger',
    'notification': 'warning',
    'custom': 'info'
  }
  return typeMap[templateType] || 'info'
}

// 获取模板类型标签文本
const getTemplateTypeLabel = (templateType: string) => {
  const labelMap: Record<string, string> = {
    'alert': '告警',
    'notification': '通知',
    'custom': '自定义'
  }
  return labelMap[templateType] || templateType
}

// 获取配置列表
const fetchConfigs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: filterForm.name,
      enabled: filterForm.enabled
    }
    const response = await pushPlusConfigApi.getPushPlusConfigs(params)
    configs.value = response.data.data || []
    pagination.total = response.data.all_num || 0
  } catch (error) {
    console.error('获取配置列表失败:', error)
    ElMessage.error('获取配置列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterForm.name = ''
  filterForm.enabled = null
  fetchConfigs()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchConfigs()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.currentPage = page
  fetchConfigs()
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  resetConfigForm()
  dialogVisible.value = true
}

// 编辑配置
const editConfig = (row: any) => {
  isEdit.value = true
  
  // 将数组转换为逗号分隔的字符串
  const topicListStr = row.topic_list && Array.isArray(row.topic_list) 
    ? row.topic_list.join(',') 
    : row.topic_list || ''
    
  const webhookListStr = row.webhook_list && Array.isArray(row.webhook_list) 
    ? row.webhook_list.join(',') 
    : row.webhook_list || ''
  
  Object.assign(configForm, {
    ...row,
    topic_list_str: topicListStr,
    webhook_list_str: webhookListStr
  })
  dialogVisible.value = true
}

// 切换状态
const toggleStatus = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要${row.enabled ? '禁用' : '启用'}此配置吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用API更新状态
    const updateData = {
      ...row,
      uuid: row.uuid,
      enabled: !row.enabled
    }
    
    await pushPlusConfigApi.updatePushPlusConfig(updateData)
    ElMessage.success(`${row.enabled ? '禁用' : '启用'}成功`)
    fetchConfigs()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换状态失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

// 删除配置
const deleteConfig = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      '此操作将永久删除该配置，是否继续？',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await pushPlusConfigApi.deletePushPlusConfig({uuid: row.uuid})
    ElMessage.success('删除成功')
    fetchConfigs()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除配置失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 重置配置表单
const resetConfigForm = () => {
  configForm.uuid = ''
  configForm.name = ''
  configForm.token = ''
  configForm.title_prefix = ''
  configForm.enabled = true
  configForm.msg_type = 'txt'
  configForm.template_type = 'alert'
  configForm.content_template = ''
  configForm.apply_to_all_alerts = true
  configForm.alert_severity_filter = []
  configForm.topic_list_str = ''
  configForm.webhook_list_str = ''
}

// 提交配置表单
const submitConfigForm = async () => {
  if (!configFormRef.value) return
  
  await configFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      try {
        // 将逗号分隔的字符串转换为数组
        const topicList = configForm.topic_list_str 
          ? configForm.topic_list_str.split(',').map(item => item.trim()).filter(item => item)
          : []
          
        const webhookList = configForm.webhook_list_str 
          ? configForm.webhook_list_str.split(',').map(item => item.trim()).filter(item => item)
          : []
        
        const submitData = {
          ...configForm,
          topic_list: topicList,
          webhook_list: webhookList,
          alert_severity_filter: configForm.apply_to_all_alerts ? [] : configForm.alert_severity_filter
        }
        
        // 移除临时字段
        delete (submitData as any).topic_list_str
        delete (submitData as any).webhook_list_str
        
        if (isEdit.value) {
          await pushPlusConfigApi.updatePushPlusConfig(submitData)
          ElMessage.success('更新成功')
        } else {
          await pushPlusConfigApi.createPushPlusConfig(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchConfigs()
      } catch (error) {
        console.error('保存配置失败:', error)
        ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
      }
    }
  })
}

// 关闭对话框
const handleCloseDialog = () => {
  dialogVisible.value = false
  if (configFormRef.value) {
    configFormRef.value.clearValidate()
  }
}

// 测试配置
const testConfig = (row: any) => {
  testForm.token = row.token
  testDialogVisible.value = true
}

// 发送测试消息
const sendTestMessage = async () => {
  testLoading.value = true
  try {
    await pushPlusConfigApi.testPushPlusConfig({
      token: testForm.token,
      title: testForm.title,
      content: testForm.content,
      msg_type: 'txt'
    })
    ElMessage.success('测试消息发送成功')
    closeTestDialog()
  } catch (error) {
    console.error('发送测试消息失败:', error)
    ElMessage.error('发送测试消息失败')
  } finally {
    testLoading.value = false
  }
}

// 关闭测试对话框
const closeTestDialog = () => {
  testDialogVisible.value = false
  testForm.title = 'PushPlus测试消息'
  testForm.content = '这是一条测试消息'
}

// 页面挂载时获取数据
onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped>
.pushplus-config-page {
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

.template-help {
  margin-top: 10px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
}

.template-help ul {
  margin: 5px 0;
  padding-left: 20px;
}

.template-help li {
  margin: 3px 0;
}

.template-help code {
  background-color: #e6f3ff;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
}
</style>