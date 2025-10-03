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
      <el-button type="primary" @click="createNewDiagram">新建架构图</el-button>
    </div>
    
    <div class="main-content">
      <div class="canvas-container" ref="canvasRef">
        <TopologyGraph 
          :topology-data="topologyData" 
          :read-only="false"
          @node-click="handleNodeClick"
          @node-create="handleNodeCreate"
          @connection-create="handleConnectionCreate"
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
            <ConnectionDetailPanel 
              :connection="selectedConnection"
              v-if="selectedConnection"
              @update="handleConnectionUpdate"
              @delete="handleConnectionDelete"
            />
            <div v-else class="no-selection">请选择一个连接</div>
          </el-tab-pane>
        </el-tabs>
      </el-aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { linkApi, nodeApi, nodeConnectionApi } from '@/api/monitor'

// 引入组件
const TopologyGraph = defineAsyncComponent(() => import('@/components/TopologyGraph.vue'))
const NodeDetailPanel = defineAsyncComponent(() => import('@/components/NodeDetailPanel.vue'))
const ConnectionDetailPanel = defineAsyncComponent(() => import('@/components/ConnectionDetailPanel.vue'))

// 响应式数据
const selectedDiagram = ref('')
const diagrams = ref<any[]>([])
const topologyData = ref({
  nodes: [],
  connections: []  // 注意：现在使用connections而不是edges
})
const selectedNode = ref(null)
const selectedConnection = ref(null)
const activeTab = ref('nodeInfo')
const canvasRef = ref()

// 获取架构图列表
const fetchDiagrams = async () => {
  try {
    const response = await linkApi.getLinks({
      link_type: 'architecture'  // 只获取架构图类型的
    })
    diagrams.value = response.data.results || []
    
    // 如果有架构图，选择第一个
    if (diagrams.value.length > 0 && !selectedDiagram.value) {
      selectedDiagram.value = diagrams.value[0].uuid
      await loadDiagramData(selectedDiagram.value)
    }
  } catch (error) {
    console.error('获取架构图列表失败:', error)
  }
}

// 加载选中的架构图数据
const loadDiagramData = async (diagramId: string) => {
  try {
    const response = await linkApi.getLinkTopology(diagramId)
    const { nodes, connections } = response.data
    
    // 转换连接数据为G6可用的edges格式
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
  }
}

// 图表改变事件
const onDiagramChange = async (value: string) => {
  await loadDiagramData(value)
}

// 创建新架构图
const createNewDiagram = async () => {
  try {
    // 这里应该弹出对话框获取架构图名称
    const name = prompt('请输入架构图名称:')
    if (name) {
      const response = await linkApi.createLink({
        name,
        description: '架构图',
        link_type: 'architecture'
      })
      
      // 添加到列表并选择
      diagrams.value.push(response.data)
      selectedDiagram.value = response.data.uuid
      topologyData.value = { nodes: [], edges: [], connections: [] }
    }
  } catch (error) {
    console.error('创建架构图失败:', error)
  }
}

// 处理节点点击
const handleNodeClick = (node: any) => {
  selectedNode.value = node
  selectedConnection.value = null  // 清除连接选择
  activeTab.value = 'nodeInfo'
}

// 处理节点创建
const handleNodeCreate = async (position: any, direction?: string, relatedNodeId?: string) => {
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
        link: selectedDiagram.value
      })
      
      // 更新本地数据
      topologyData.value.nodes.push({
        ...newNode,
        id: newNode.uuid,
        label: newNode.name
      })
      
      // 如果指定了方向和相关节点，创建连接
      if (direction && relatedNodeId) {
        await createConnection(relatedNodeId, newNode.uuid, direction)
      }
    }
  } catch (error) {
    console.error('创建节点失败:', error)
  }
}

// 处理连接创建
const handleConnectionCreate = async (sourceId: string, targetId: string, direction: string) => {
  if (!selectedDiagram.value) {
    ElMessage.error('请先选择架构图')
    return
  }

  try {
    await nodeConnectionApi.createConnection({
      from_node: sourceId,
      to_node: targetId,
      direction,
      link: selectedDiagram.value
    })
    
    // 更新本地数据
    topologyData.value.connections.push({
      from_node: sourceId,
      to_node: targetId,
      direction,
      link: selectedDiagram.value
    })
    
    // 添加到edges以便显示
    topologyData.value.edges.push({
      id: `${sourceId}-${targetId}`,
      source: sourceId,
      target: targetId,
      label: direction,
      direction
    })
  } catch (error) {
    console.error('创建连接失败:', error)
  }
}

// 创建连接的辅助函数
const createConnection = async (sourceId: string, targetId: string, direction: string) => {
  if (!selectedDiagram.value) return

  try {
    const response = await nodeConnectionApi.createConnection({
      from_node: sourceId,
      to_node: targetId,
      direction,
      link: selectedDiagram.value
    })
    
    // 更新本地数据
    topologyData.value.connections.push(response.data)
    topologyData.value.edges.push({
      id: response.data.uuid,
      source: sourceId,
      target: targetId,
      label: direction,
      direction
    })
  } catch (error) {
    console.error('创建连接失败:', error)
  }
}

// 处理节点更新
const handleNodeUpdate = async (nodeData: any) => {
  try {
    await nodeApi.updateNode(nodeData.uuid, nodeData)
    
    // 更新本地数据
    const index = topologyData.value.nodes.findIndex(n => n.uuid === nodeData.uuid)
    if (index !== -1) {
      topologyData.value.nodes[index] = { ...topologyData.value.nodes[index], ...nodeData }
    }
  } catch (error) {
    console.error('更新节点失败:', error)
  }
}

// 处理节点删除
const handleNodeDelete = async (nodeId: string) => {
  try {
    await nodeApi.deleteNode(nodeId)
    
    // 从本地数据中移除
    topologyData.value.nodes = topologyData.value.nodes.filter(n => n.uuid !== nodeId)
    topologyData.value.edges = topologyData.value.edges.filter(
      e => e.source !== nodeId && e.target !== nodeId
    )
    
    selectedNode.value = null
  } catch (error) {
    console.error('删除节点失败:', error)
  }
}

// 处理连接更新
const handleConnectionUpdate = async (connectionData: any) => {
  try {
    await nodeConnectionApi.updateConnection(connectionData.uuid, connectionData)
    
    // 更新本地数据
    const index = topologyData.value.connections.findIndex(c => c.uuid === connectionData.uuid)
    if (index !== -1) {
      topologyData.value.connections[index] = { ...topologyData.value.connections[index], ...connectionData }
    }
    
    // 更新edges以便显示
    const edgeIndex = topologyData.value.edges.findIndex(e => e.id === connectionData.uuid)
    if (edgeIndex !== -1) {
      topologyData.value.edges[edgeIndex].label = connectionData.direction
      topologyData.value.edges[edgeIndex].direction = connectionData.direction
    }
  } catch (error) {
    console.error('更新连接失败:', error)
  }
}

// 处理连接删除
const handleConnectionDelete = async (connectionId: string) => {
  try {
    await nodeConnectionApi.deleteConnection(connectionId)
    
    // 从本地数据中移除
    topologyData.value.connections = topologyData.value.connections.filter(c => c.uuid !== connectionId)
    topologyData.value.edges = topologyData.value.edges.filter(e => e.id !== connectionId)
    
    selectedConnection.value = null
  } catch (error) {
    console.error('删除连接失败:', error)
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
</style>