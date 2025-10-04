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
        @click="createNewNode"
      >新建节点</el-button>
      
      <!-- 图控制按钮 -->
      <div class="graph-controls">
        <el-button @click="zoomIn" title="放大">
          <el-icon><ZoomIn /></el-icon>
        </el-button>
        <el-button @click="zoomOut" title="缩小">
          <el-icon><ZoomOut /></el-icon>
        </el-button>
        <el-button @click="fitView" title="适应视图">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="main-content">
      <div class="canvas-container" ref="canvasRef">
        <G6TopologyGraph 
          ref="topologyGraphRef"
          :topology-data="topologyData" 
          :selected-node="selectedNode"
          @node-click="handleNodeClick"
        />
      </div>
      
      <el-aside class="operation-panel" width="300px">
        <!-- 节点信息栏 -->
        <div v-if="selectedNode" class="node-info-panel">
          <h3>节点信息</h3>
          <el-form :model="selectedNode" label-width="80px" size="small">
            <el-form-item label="名称">
              <el-input v-model="selectedNode.name" @change="updateNodeInfo" />
            </el-form-item>
            
            <el-form-item label="基础信息">
              <div v-for="(info, index) in selectedNode.basic_info_list" :key="index" class="basic-info-item">
                <el-input 
                  v-model="info.host" 
                  placeholder="主机" 
                  size="small"
                  style="width: 40%; margin-right: 5px;"
                  @change="updateNodeInfo"
                />
                <el-input 
                  v-model="info.port" 
                  placeholder="端口" 
                  size="small"
                  type="number"
                  style="width: 30%; margin-right: 5px;"
                  @change="updateNodeInfo"
                />
                <el-button @click="removeBasicInfo(index)" size="small" type="danger">删除</el-button>
              </div>
              <el-button @click="addBasicInfo" size="small">添加信息</el-button>
            </el-form-item>
            
            <el-form-item label="健康状态">
              <el-tag :type="selectedNode.is_healthy ? 'success' : 'danger'">
                {{ selectedNode.is_healthy ? '健康' : '异常' }}
              </el-tag>
            </el-form-item>
          </el-form>
        </div>
        
        <!-- 操作栏 -->
        <div v-if="selectedNode" class="operation-section">
          <h3>操作</h3>
          
          <div class="direction-buttons">
            <div class="direction-row">
              <el-button type="default" size="small" @click="createNewNodeInDirection('up')">
                上方创建
              </el-button>
            </div>
            
            <div class="direction-row">
              <el-button type="default" size="small" @click="createNewNodeInDirection('left')">
                左侧创建
              </el-button>
              <el-button type="default" size="small" @click="createNewNodeInDirection('right')">
                右侧创建
              </el-button>
            </div>
            
            <div class="direction-row">
              <el-button type="default" size="small" @click="createNewNodeInDirection('down')">
                下方创建
              </el-button>
            </div>
          </div>
          
          <!-- 连接管理 -->
          <div class="connection-management">
            <h4>连接管理</h4>
            
            <div class="existing-connections">
              <div 
                v-for="conn in nodeConnections" 
                :key="conn.uuid" 
                class="connection-item"
              >
                <span>{{ conn.direction }} -> {{ getNodeName(conn.to_node) }}</span>
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="deleteConnection(conn.uuid)"
                >
                  删除
                </el-button>
              </div>
              
              <div v-if="nodeConnections.length === 0" class="no-connections">
                暂无连接
              </div>
            </div>
            
            <el-divider />
            
            <h5>添加连接</h5>
            <el-form :model="tempConnection" label-width="60px" size="small">
              <el-form-item label="方向">
                <el-select v-model="tempConnection.direction" placeholder="选择方向">
                  <el-option label="上" value="up" />
                  <el-option label="下" value="down" />
                  <el-option label="左" value="left" />
                  <el-option label="右" value="right" />
                </el-select>
              </el-form-item>
              <el-form-item label="节点">
                <el-select 
                  v-model="tempConnection.to_node" 
                  placeholder="选择节点"
                  filterable
                >
                  <el-option
                    v-for="node in availableNodes"
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
                  size="small"
                  @click="createConnection"
                  :disabled="!tempConnection.direction || !tempConnection.to_node"
                >
                  添加连接
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-else class="empty-state">
          <p>请选择一个节点以查看信息和进行操作</p>
        </div>
      </el-aside>
    </div>
    
    <!-- 创建节点对话框 -->
    <el-dialog 
      v-model="showCreateNodeDialog" 
      :title="createNodeDialogTitle"
      width="40%"
    >
      <el-form :model="newNodeForm" label-width="80px">
        <el-form-item label="节点名称" required>
          <el-input v-model="newNodeForm.name" placeholder="请输入节点名称" />
        </el-form-item>
        
        <el-form-item label="基础信息">
          <div v-for="(info, index) in newNodeForm.basic_info_list" :key="index" class="basic-info-item">
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
              type="number"
              style="width: 30%; margin-right: 5px;"
            />
            <el-button @click="removeNewBasicInfo(index)" size="small" type="danger">删除</el-button>
          </div>
          <el-button @click="addNewBasicInfo" size="small">添加信息</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateNodeDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmCreateNode">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, defineAsyncComponent } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { linkApi, nodeApi, nodeConnectionApi } from '@/api/monitor'
import { ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'

// 引入组件
const G6TopologyGraph = defineAsyncComponent(() => import('@/components/G6TopologyGraph.vue'))

// 响应式数据
const selectedDiagram = ref('')
const diagrams = ref<any[]>([])
const topologyData = ref({
  nodes: [],
  edges: [],
  connections: []
})
const selectedNode = ref<any>(null)
const showCreateNodeDialog = ref(false)
const createNodeDialogTitle = ref('新建节点')
const newNodeForm = ref({
  name: '',
  basic_info_list: [{}] // 默认添加一个空的信息项
})
const tempConnection = ref({
  direction: '',
  to_node: ''
})
const creatingDirection = ref<string | null>(null)
const topologyGraphRef = ref()

// 获取架构图列表
const fetchDiagrams = async () => {
  try {
    const response = await linkApi.getLinks({
      link_type: 'architecture'
    })
    diagrams.value = response.data.data || response.data.data || []
    
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
    const response = await linkApi.getLinkTopology({uuid: diagramId})
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
      connections
    }
  } catch (error) {
    console.error('加载架构图数据失败:', error)
    ElMessage.error('加载架构图数据失败')
  }
}

// 图表改变事件
const onDiagramChange = async (value: string) => {
  selectedNode.value = null // 切换图表时清除选中节点
  await loadDiagramData(value)
}

// 处理节点点击
const handleNodeClick = (node: any) => {
  selectedNode.value = node ? { ...node } : null
}

// 放大
const zoomIn = () => {
  if (topologyGraphRef.value && topologyGraphRef.value.zoomIn) {
    topologyGraphRef.value.zoomIn()
  }
}

// 缩小
const zoomOut = () => {
  if (topologyGraphRef.value && topologyGraphRef.value.zoomOut) {
    topologyGraphRef.value.zoomOut()
  }
}

// 适应视图
const fitView = () => {
  if (topologyGraphRef.value && topologyGraphRef.value.fitView) {
    topologyGraphRef.value.fitView()
  }
}

// 创建新节点 - 通用方法
const createNewNode = () => {
  createNodeDialogTitle.value = '新建节点'
  creatingDirection.value = null
  resetNewNodeForm()
  showCreateNodeDialog.value = true
}

// 在特定方向创建新节点
const createNewNodeInDirection = (direction: string) => {
  if (!selectedNode.value) {
    ElMessage.warning('请先选择一个节点')
    return
  }
  
  createNodeDialogTitle.value = `在${direction === 'up' ? '上' : direction === 'down' ? '下' : direction === 'left' ? '左' : '右'}方创建节点`
  creatingDirection.value = direction
  resetNewNodeForm()
  showCreateNodeDialog.value = true
}

// 重置新节点表单
const resetNewNodeForm = () => {
  newNodeForm.value = {
    name: '',
    basic_info_list: [{}]
  }
}

// 添加新节点的基础信息
const addNewBasicInfo = () => {
  newNodeForm.value.basic_info_list.push({})
}

// 删除新节点的基础信息
const removeNewBasicInfo = (index: number) => {
  if (newNodeForm.value.basic_info_list.length > 1) {
    newNodeForm.value.basic_info_list.splice(index, 1)
  } else {
    newNodeForm.value.basic_info_list[0] = {}
  }
}

// 确认创建节点
const confirmCreateNode = async () => {
  if (!newNodeForm.value.name.trim()) {
    ElMessage.error('请输入节点名称')
    return
  }

  try {
    // 计算新节点的位置 - 居中或相对于选中节点
    let position_x = 0
    let position_y = 0
    
    if (creatingDirection.value && selectedNode.value) {
      // 在特定方向创建节点
      const offset = 120 // 节点间距
      switch (creatingDirection.value) {
        case 'up':
          position_x = selectedNode.value.position_x || 0
          position_y = (selectedNode.value.position_y || 0) - offset
          break
        case 'down':
          position_x = selectedNode.value.position_x || 0
          position_y = (selectedNode.value.position_y || 0) + offset
          break
        case 'left':
          position_x = (selectedNode.value.position_x || 0) - offset
          position_y = selectedNode.value.position_y || 0
          break
        case 'right':
          position_x = (selectedNode.value.position_x || 0) + offset
          position_y = selectedNode.value.position_y || 0
          break
      }
    } else {
      // 居中创建
      const container = document.querySelector('.canvas-container')
      if (container) {
        position_x = container.clientWidth / 2 - 40 // 40是节点宽度的一半
        position_y = container.clientHeight / 2 - 20 // 20是节点高度的一半
      }
    }

    const newNode = await nodeApi.createNode({
      name: newNodeForm.value.name,
      basic_info_list: newNodeForm.value.basic_info_list.filter(info => info.host || info.port),
      link: selectedDiagram.value,
      position_x: Math.round(position_x),
      position_y: Math.round(position_y)
    })
    
    // 如果是在特定方向创建的，还需要创建连接
    if (creatingDirection.value && selectedNode.value) {
      await nodeConnectionApi.createConnection({
        from_node: selectedNode.value.uuid,
        to_node: newNode.uuid,
        direction: creatingDirection.value,
        link: selectedDiagram.value
      })
    }

    // 刷新数据
    await loadDiagramData(selectedDiagram.value)
    showCreateNodeDialog.value = false
    
    ElMessage.success('节点创建成功')
  } catch (error) {
    console.error('创建节点失败:', error)
    ElMessage.error('创建节点失败')
  }
}

// 添加基础信息到选中节点
const addBasicInfo = () => {
  if (selectedNode.value) {
    if (!selectedNode.value.basic_info_list) {
      selectedNode.value.basic_info_list = []
    }
    selectedNode.value.basic_info_list.push({ host: '', port: null })
  }
}

// 删除基础信息
const removeBasicInfo = (index: number) => {
  if (selectedNode.value && selectedNode.value.basic_info_list) {
    if (selectedNode.value.basic_info_list.length > 1) {
      selectedNode.value.basic_info_list.splice(index, 1)
    } else {
      selectedNode.value.basic_info_list[0] = { host: '', port: null }
    }
  }
}

// 更新节点信息
const updateNodeInfo = async () => {
  if (!selectedNode.value || !selectedNode.value.uuid) return

  try {
    await nodeApi.updateNode(selectedNode.value.uuid, {
      name: selectedNode.value.name,
      basic_info_list: selectedNode.value.basic_info_list.filter((info: any) => info.host || info.port)
    })
    
    // 更新本地数据
    const index = topologyData.value.nodes.findIndex(n => n.uuid === selectedNode.value.uuid)
    if (index !== -1) {
      topologyData.value.nodes[index] = { ...selectedNode.value }
    }
    
    ElMessage.success('节点信息更新成功')
  } catch (error) {
    console.error('更新节点信息失败:', error)
    ElMessage.error('更新节点信息失败')
  }
}

// 获取与当前选中节点相关的连接
const nodeConnections = computed(() => {
  if (!selectedNode.value || !topologyData.value.connections) return []
  return topologyData.value.connections.filter(conn => conn.from_node === selectedNode.value.uuid)
})

// 获取可连接的节点（排除当前选中的节点）
const availableNodes = computed(() => {
  if (!selectedNode.value || !topologyData.value.nodes) return []
  return topologyData.value.nodes.filter(node => node.uuid !== selectedNode.value.uuid)
})

// 获取节点名称的辅助函数
const getNodeName = (nodeId: string) => {
  const node = topologyData.value.nodes.find(n => n.uuid === nodeId)
  return node ? node.name : nodeId.substring(0, 8) + '...'
}

// 创建连接
const createConnection = async () => {
  if (!selectedNode.value || !tempConnection.value.direction || !tempConnection.value.to_node) {
    ElMessage.error('请填写完整的连接信息')
    return
  }

  try {
    const response = await nodeConnectionApi.createConnection({
      from_node: selectedNode.value.uuid,
      to_node: tempConnection.value.to_node,
      direction: tempConnection.value.direction,
      link: selectedDiagram.value
    })
    
    // 刷新数据
    await loadDiagramData(selectedDiagram.value)
    
    // 重置表单
    tempConnection.value = { direction: '', to_node: '' }
    
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
    
    // 刷新数据
    await loadDiagramData(selectedDiagram.value)
    
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

.graph-controls {
  display: flex;
  margin-left: auto;
  gap: 5px;
}

.graph-controls .el-button {
  padding: 8px;
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

.operation-panel {
  width: 300px;
  background-color: #fff;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  padding: 15px;
}

.node-info-panel, .operation-section {
  margin-bottom: 20px;
}

.node-info-panel h3, .operation-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
}

.basic-info-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.direction-buttons {
  margin-bottom: 20px;
}

.direction-row {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

.direction-row .el-button {
  margin: 0 5px;
}

.connection-management {
  border-top: 1px solid #e4e7ed;
  padding-top: 15px;
}

.connection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.connection-item:last-child {
  border-bottom: none;
}

.no-connections {
  padding: 10px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  text-align: center;
}

.dialog-footer {
  text-align: right;
}
</style>