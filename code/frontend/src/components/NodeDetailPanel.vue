<template>
  <div class="node-detail-panel">
    <el-form :model="node" label-width="100px" v-if="node">
      <el-form-item label="节点ID">
        <span>{{ node.uuid }}</span>
      </el-form-item>
      
      <el-form-item label="节点名称">
        <el-input v-model="node.name" />
      </el-form-item>
      
      <el-form-item label="基础信息">
        <el-button @click="addBasicInfo" size="small">添加</el-button>
        <div 
          v-for="(info, index) in node.basic_info_list" 
          :key="index"
          class="basic-info-item"
        >
          <el-input 
            v-model="info.host" 
            placeholder="主机" 
            size="small"
            style="width: 40%; margin-right: 5px;"
          />
          <el-input 
            v-model="info.port" 
            placeholder="端口" 
            size="small"
            style="width: 30%; margin-right: 5px;"
          />
          <el-button @click="removeBasicInfo(index)" size="small" type="danger">删除</el-button>
        </div>
      </el-form-item>
      
      <el-form-item label="健康状态">
        <el-tag :type="node.is_healthy ? 'success' : 'danger'">
          {{ node.is_healthy ? '健康' : '不健康' }}
        </el-tag>
      </el-form-item>
      
      <el-form-item label="状态">
        <el-switch
          v-model="node.is_active"
          active-text="启用"
          inactive-text="禁用"
        />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="updateNode">更新</el-button>
        <el-button type="danger" @click="deleteNode">删除</el-button>
      </el-form-item>
    </el-form>
    <div v-else class="no-data">请选择一个节点</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nodeApi } from '@/api/monitor'

// 定义组件属性
const props = defineProps<{
  node: any
}>()

// 定义事件
const emit = defineEmits(['update', 'delete'])

// 响应式数据
const node = ref<any>(null)

// 监听节点数据变化
watch(() => props.node, (newVal) => {
  if (newVal) {
    // 创建副本以避免直接修改父组件数据
    node.value = JSON.parse(JSON.stringify(newVal))
  } else {
    node.value = null
  }
}, { immediate: true })

// 添加基础信息
const addBasicInfo = () => {
  if (node.value) {
    if (!node.value.basic_info_list) {
      node.value.basic_info_list = []
    }
    node.value.basic_info_list.push({ host: '', port: null })
  }
}

// 删除基础信息
const removeBasicInfo = (index: number) => {
  if (node.value && node.value.basic_info_list) {
    node.value.basic_info_list.splice(index, 1)
  }
}

// 更新节点
const updateNode = async () => {
  if (!node.value || !node.value.uuid) return
  
  try {
    const response = await nodeApi.updateNode({
      uuid: node.value.uuid,
      name: node.value.name,
      basic_info_list: node.value.basic_info_list || [],
      is_active: node.value.is_active
    })
    
    emit('update', response)
    ElMessage.success('节点更新成功')
  } catch (error) {
    console.error('更新节点失败:', error)
    ElMessage.error('更新节点失败')
  }
}

// 删除节点
const deleteNode = async () => {
  if (!node.value || !node.value.uuid) return
  
  try {
    await ElMessageBox.confirm('确定要删除此节点吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await nodeApi.deleteNode({ uuid: node.value.uuid })
    emit('delete', node.value.uuid)
    ElMessage.success('节点删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除节点失败:', error)
      ElMessage.error('删除节点失败')
    }
  }
}
</script>

<style scoped>
.node-detail-panel {
  padding: 20px;
}

.basic-info-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.no-data {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>