<template>
  <div class="architecture-editor">
    <div class="top-toolbar">
      <el-select 
        v-model="selectedDiagram" 
        placeholder="选择架构图" 
        @change="onDiagramChange"
        style="width: 200px; margin-right: 10px;"
      >
        <el-option
          v-for="diagram in diagrams"
          :key="diagram.uuid"
          :label="diagram.name"
          :value="diagram.uuid"
        />
      </el-select>
      <el-button 
        type="primary" 
        @click="showCreateDiagramDialog = true"
        v-if="hasPerms('monitor:createDiagram')"
      >新建架构图</el-button>
    </div>
    
    <div class="main-content">
      <div class="canvas-container" ref="canvasRef">
        <TopologyGraph 
          :topology-data="topologyData" 
          :read-only="false"
          @node-click="handleNodeClick"
          @node-create="handleNodeCreate"
          @node-move="handleNodeMove"
        />
      </div>
      
      <el-aside class="node-panel" width="300px">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="节点信息" name="nodeInfo">
            <NodeDetailPanel 
              :node="selectedNode"
              v-if="selectedNode"
              @update="handleNodeUpdate"
              @delete="handleNodeDelete"
            />
            <div v-else class="no-selection">请选择一个节点</div>
          </el-tab-pane>
          <el-tab-pane label="连接信息" name="connectionInfo">
            <div class="connection-info">
              <h4>节点连接</h4>
              <div v-if="selectedNode">
                <div v-for="conn in nodeConnections" :key="conn.uuid" class="connection-item">
                  <span>{{ conn.direction }} -> {{ getNodeName(conn.to_node) }}</span>
                  <el-button size="small" @click="deleteConnection(conn.uuid)">删除</el-button>
                </div>
                
                <el-divider />
                
                <h4>添加连接</h4>
                <el-form :model="newConnection" label-width="80px">
                  <el-form-item label="方向">
                    <el-select v-model="newConnection.direction" placeholder="选择方向">
                      <el-option label="上" value="up" />
                      <el-option label="下" value="down" />
                      <el-option label="左" value="left" />
                      <el-option label="右" value="right" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="目标节点">
                    <el-select v-model="newConnection.to_node" placeholder="选择节点">
                      <el-option
                        v-for="node in topologyData.nodes"
                        :key="node.uuid"
                        :label="node.name"
                        :value="node.uuid"
                        :disabled="node.uuid === selectedNode.uuid"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button 
                      type="primary" 
                      @click="createConnection"
                      :disabled="!newConnection.direction || !newConnection.to_node"
                    >创建连接</el-button>
                  </el-form-item>
                </el-form>
              </div>
              <div v-else class="no-selection">请选择一个节点</div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-aside>
    </div>
    
    <!-- 创建架构图对话框 -->
    <el-dialog 
      v-model="showCreateDiagramDialog" 
      title="创建架构图" 
      width="30%"
    >
      <el-form :model="newDiagramForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newDiagramForm.name" placeholder="请输入架构图名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDiagramDialog = false">取消</el-button>
          <el-button type="primary" @click="createNewDiagram">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, defineAsyncComponent } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { linkApi, nodeApi, nodeConnectionApi } from '@/api/monitor'
import { hasPerms } from "@/utils/auth"

// 引入组件
const TopologyGraph = defineAsyncComponent(() => import('@/components/TopologyGraph.vue'))
const NodeDetailPanel = defineAsyncComponent(() => import('@/components/NodeDetailPanel.vue'))

// 响应式数据
const selectedDiagram = ref('')
const diagrams = ref<any[]>([])
const topologyData = ref({
  nodes: [],
  edges: [],
  connections: []
})
const selectedNode = ref<any>(null)
const activeTab = ref('nodeInfo')
const showCreateDiagramDialog = ref(false)
const newDiagramForm = ref({
  name: ''
})
const newConnection = ref({
  direction: '',
  to_node: ''
})

// 获取架构图列表
const fetchDiagrams = async () => {
  try {
    const response = await linkApi.getLinks({
      link_type: 'architecture'  // 只获取架构图类型的
    })
    diagrams.value = response.data.data || response.data.results || []
    
    // 如果有架构图，选择第一个
    if (diagrams.value.length > 0 && !selectedDiagram.value) {
      selectedDiagram.value = diagrams.value[0].uuid
      await loadDiagramData(selectedDiagram.value)
    }
  } catch (error) {
    console.error('获取架构图列表失败:', error)
    ElMessage.error('获取架构图列表失败')
  }
}

// 加载选中的架构图数据
const loadDiagramData = async (diagramId: string) => {
  try {
    const response = await linkApi.getLinkTopology(diagramId, {uuid: diagramId})
    const { nodes, connections } = response.data
    
    // 转换连接数据为edges格式
    const edges = connections.map(conn => ({
      id: conn.uuid,
      source: conn.from_node,
      target: conn.to_node,
      label: conn.direction,
      direction: conn.direction
    }))
    
    topologyData.value = {
      nodes: nodes.map(node => ({
        ...node,
        id: node.uuid,
        label: node.name
      })),
      edges,
      connections  // 保留原始连接数据用于操作
    }
  } catch (error) {
    console.error('加载架构图数据失败:', error)
    ElMessage.error('加载架构图数据失败')
  }
}

// 图表改变事件
const onDiagramChange = async (value: string) => {
  await loadDiagramData(value)
}

// 创建新架构图
const createNewDiagram = async () => {
  if (!newDiagramForm.value.name.trim()) {
    ElMessage.error('请输入架构图名称')
    return
  }
  
  try {
    const response = await linkApi.createLink({
      name: newDiagramForm.value.name,
      description: '架构图',
      link_type: 'architecture'
    })
    
    // 添加到列表并选择
    diagrams.value.push(response.data)
    selectedDiagram.value = response.data.uuid
    topologyData.value = { nodes: [], edges: [], connections: [] }
    newDiagramForm.value.name = ''
    showCreateDiagramDialog.value = false
    ElMessage.success('架构图创建成功')
  } catch (error) {
    console.error('创建架构图失败:', error)
    ElMessage.error('创建架构图失败')
  }
}

// 处理节点点击
const handleNodeClick = (node: any) => {
  selectedNode.value = { ...node }  // 创建副本以避免直接修改原数据
  activeTab.value = 'nodeInfo'
}

// 处理节点创建
const handleNodeCreate = async (position: any) => {
  if (!selectedDiagram.value) {
    ElMessage.error('请先选择架构图')
    return
  }

  try {
    // 弹出对话框获取节点信息
    const name = prompt('请输入节点名称:')
    if (name) {
      const newNode = await nodeApi.createNode({
        name,
        basic_info_list: [],
        link: selectedDiagram.value,
        position_x: Math.round(position.x),
        position_y: Math.round(position.y)
      })
      
      // 更新本地数据
      topologyData.value.nodes.push({
        ...newNode,
        id: newNode.uuid,
        label: newNode.name
      })
      
      ElMessage.success('节点创建成功')
    }
  } catch (error) {
    console.error('创建节点失败:', error)
    ElMessage.error('创建节点失败')
  }
}

// 处理节点移动
const handleNodeMove = async ({ node, x, y }: { node: any, x: number, y: number }) => {
  try {
    // 更新后端数据
    await nodeApi.updateNode(node.uuid, {
      ...node,
      position_x: Math.round(x),
      position_y: Math.round(y)
    })
    
    // 更新本地数据
    const index = topologyData.value.nodes.findIndex(n => n.uuid === node.uuid)
    if (index !== -1) {
      topologyData.value.nodes[index].position_x = Math.round(x)
      topologyData.value.nodes[index].position_y = Math.round(y)
    }
    
    ElMessage.success('节点位置已更新')
  } catch (error) {
    console.error('更新节点位置失败:', error)
    ElMessage.error('更新节点位置失败')
  }
}

// 处理节点更新
const handleNodeUpdate = async (updatedNode: any) => {
  // 更新本地数据
  const index = topologyData.value.nodes.findIndex(n => n.uuid === updatedNode.uuid)
  if (index !== -1) {
    topologyData.value.nodes[index] = { ...updatedNode }
    topologyData.value.nodes[index].id = updatedNode.uuid
    topologyData.value.nodes[index].label = updatedNode.name
  }
  
  ElMessage.success('节点更新成功')
}

// 处理节点删除
const handleNodeDelete = async (nodeId: string) => {
  // 从本地数据中移除
  topologyData.value.nodes = topologyData.value.nodes.filter(n => n.uuid !== nodeId)
  topologyData.value.edges = topologyData.value.edges.filter(
    e => e.source !== nodeId && e.target !== nodeId
  )
  topologyData.value.connections = topologyData.value.connections.filter(
    c => c.from_node !== nodeId && c.to_node !== nodeId
  )
  
  selectedNode.value = null
  ElMessage.success('节点删除成功')
}

// 获取与当前选中节点相关的连接
const nodeConnections = computed(() => {
  if (!selectedNode.value || !topologyData.value.connections) return []
  return topologyData.value.connections.filter(conn => conn.from_node === selectedNode.value.uuid)
})

// 获取节点名称的辅助函数
const getNodeName = (nodeId: string) => {
  const node = topologyData.value.nodes.find(n => n.uuid === nodeId)
  return node ? node.name : nodeId.substring(0, 8) + '...'
}

// 创建连接
const createConnection = async () => {
  if (!selectedNode.value || !newConnection.value.direction || !newConnection.value.to_node) {
    ElMessage.error('请填写完整的连接信息')
    return
  }

  try {
    const response = await nodeConnectionApi.createConnection({
      from_node: selectedNode.value.uuid,
      to_node: newConnection.value.to_node,
      direction: newConnection.value.direction,
      link: selectedDiagram.value
    })
    
    // 更新本地数据
    topologyData.value.connections.push(response.data)
    topologyData.value.edges.push({
      id: response.data.uuid,
      source: response.data.from_node,
      target: response.data.to_node,
      label: response.data.direction,
      direction: response.data.direction
    })
    
    // 重置表单
    newConnection.value = { direction: '', to_node: '' }
    ElMessage.success('连接创建成功')
  } catch (error) {
    console.error('创建连接失败:', error)
    ElMessage.error('创建连接失败')
  }
}

// 删除连接
const deleteConnection = async (connectionId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除此连接吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await nodeConnectionApi.deleteConnection(connectionId)
    
    // 从本地数据中移除
    topologyData.value.connections = topologyData.value.connections.filter(c => c.uuid !== connectionId)
    topologyData.value.edges = topologyData.value.edges.filter(e => e.id !== connectionId)
    
    ElMessage.success('连接删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除连接失败:', error)
      ElMessage.error('删除连接失败')
    }
  }
}

// 组件挂载时获取架构图列表
onMounted(() => {
  fetchDiagrams()
})
</script>

<style scoped>
.architecture-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.top-toolbar {
  padding: 10px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  height: calc(100vh - 120px);
}

.node-panel {
  width: 300px;
  background-color: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
}

.no-selection {
  padding: 20px;
  text-align: center;
  color: #999;
}

.connection-info {
  padding: 10px;
}

.connection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.dialog-footer {
  text-align: right;
}
</style>