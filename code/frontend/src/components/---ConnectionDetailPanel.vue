<template>
  <div class="connection-detail-panel">
    <el-form :model="connection" label-width="100px" v-if="connection">
      <el-form-item label="连接ID">
        <span>{{ connection.uuid }}</span>
      </el-form-item>
      
      <el-form-item label="起始节点">
        <span>{{ getNodeIdName(connection.from_node) }}</span>
      </el-form-item>
      
      <el-form-item label="目标节点">
        <span>{{ getNodeIdName(connection.to_node) }}</span>
      </el-form-item>
      
      <el-form-item label="连接方向">
        <el-select v-model="connection.direction" placeholder="选择方向">
          <el-option label="上" value="up" />
          <el-option label="下" value="down" />
          <el-option label="左" value="left" />
          <el-option label="右" value="right" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="状态">
        <el-switch
          v-model="connection.is_active"
          active-text="启用"
          inactive-text="禁用"
        />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="updateConnection">更新</el-button>
        <el-button type="danger" @click="deleteConnection">删除</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nodeConnectionApi } from '@/api/monitor'

// 定义组件属性
const props = defineProps<{
  connection: any
}>()

// 定义事件
const emit = defineEmits(['update', 'delete'])

// 响应式数据
const connection = ref<any>(null)

// 监听连接数据变化
watch(() => props.connection, (newVal) => {
  if (newVal) {
    connection.value = { ...newVal }
  } else {
    connection.value = null
  }
}, { immediate: true })

// 获取节点名称的辅助函数
const getNodeIdName = (nodeId: string) => {
  // 这里应该从全局节点列表中获取节点名称
  // 在实际实现中，您可能需要从某个存储中获取节点名称
  return `节点: ${nodeId.substring(0, 8)}...`
}

// 更新连接
const updateConnection = async () => {
  if (!connection.value) return
  
  try {
    await nodeConnectionApi.updateConnection(connection.value.uuid, connection.value)
    emit('update', connection.value)
    ElMessage.success('连接更新成功')
  } catch (error) {
    console.error('更新连接失败:', error)
    ElMessage.error('更新连接失败')
  }
}

// 删除连接
const deleteConnection = async () => {
  if (!connection.value) return
  
  try {
    await ElMessageBox.confirm('确定要删除此连接吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await nodeConnectionApi.deleteConnection(connection.value.uuid)
    emit('delete', connection.value.uuid)
    ElMessage.success('连接删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除连接失败:', error)
      ElMessage.error('删除连接失败')
    }
  }
}
</script>

<style scoped>
.connection-detail-panel {
  padding: 20px;
}
</style>