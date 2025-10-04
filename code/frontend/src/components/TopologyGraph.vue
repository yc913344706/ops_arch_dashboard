<template>
  <div class="topology-graph">
    <div class="graph-controls">
      <el-button @click="zoomIn" title="放大">
        <el-icon><ZoomIn /></el-icon>
      </el-button>
      <el-button @click="zoomOut" title="缩小">
        <el-icon><ZoomOut /></el-icon>
      </el-button>
      <el-button @click="refreshData" title="刷新">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>
    <div class="legend-panel">
      <div class="legend-title">健康状态图例</div>
      <div class="legend-item" v-for="status in healthStatuses" :key="status.code">
        <span class="legend-color" :style="{ backgroundColor: status.color }"></span>
        <span class="legend-text">{{ status.text }}</span>
      </div>
    </div>
    
    <div class="topology-canvas" ref="canvasRef" @click="handleCanvasClick">
      <!-- 渲染节点 -->
      <div 
        v-for="node in topologyData.nodes"
        :key="node.uuid || node.id"
        class="node-item"
        :style="{ 
          left: (node.position_x || 0) + 'px', 
          top: (node.position_y || 0) + 'px',
          border: `2px solid ${getNodeBorderColor(node.is_healthy)}`
        }"
        :class="{ 'healthy': node.is_healthy, 'unhealthy': !node.is_healthy, 'selected': isSelected(node) }"
        @click.stop="handleNodeClick(node)"
        @dblclick="handleNodeDoubleClick(node)"
      >
        <div class="node-header">{{ node.name }}</div>
        <div class="node-info">
          <div v-for="(info, index) in node.basic_info_list" :key="index" class="node-basic-info">
            <span v-if="info.host">{{ info.host }}</span>
            <span v-if="info.port" class="port">:{{ info.port }}</span>
          </div>
        </div>
      </div>
      
      <!-- 渲染连接线 -->
      <svg class="connections-svg" :style="{ width: '100%', height: '100%' }">
        <line 
          v-for="edge in topologyData.edges" 
          :key="edge.id" 
          :x1="getNodePosition(edge.source).x" 
          :y1="getNodePosition(edge.source).y" 
          :x2="getNodePosition(edge.target).x" 
          :y2="getNodePosition(edge.target).y" 
          stroke="#999" 
          stroke-width="2"
        />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { 
  ZoomIn, 
  ZoomOut, 
  Refresh
} from '@element-plus/icons-vue'

// 定义组件属性
const props = defineProps<{
  topologyData: {
    nodes: Array<any>,
    edges: Array<any>
  },
  readOnly?: boolean
}>()

// 定义事件
const emit = defineEmits(['nodeClick', 'nodeCreate'])

// 响应式数据
const canvasRef = ref<HTMLElement>()
const selectedNode = ref<any>(null)
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)

// 健康状态定义
const healthStatuses = [
  { code: 'healthy', text: '健康', color: '#52c41a' },
  { code: 'warning', text: '警告', color: '#faad14' },
  { code: 'error', text: '错误', color: '#ff4d4f' },
  { code: 'unknown', text: '未知', color: '#bfbfbf' }
]

// 获取节点位置
const getNodePosition = (nodeId: string) => {
  const node = props.topologyData.nodes.find(n => n.id === nodeId || n.uuid === nodeId)
  if (node) {
    return { x: node.position_x || 0, y: node.position_y || 0 }
  }
  return { x: 0, y: 0 }
}

// 根据健康状态获取节点边框颜色
const getNodeBorderColor = (isHealthy: boolean) => {
  return isHealthy ? '#52c41a' : '#ff4d4f'
}

// 检查节点是否被选中
const isSelected = (node: any) => {
  return selectedNode.value && (selectedNode.value.uuid === node.uuid || selectedNode.value.id === node.id)
}

// 处理节点点击
const handleNodeClick = (node: any) => {
  selectedNode.value = node
  emit('nodeClick', node)
}

// 处理节点双击
const handleNodeDoubleClick = (node: any) => {
  // 可能用于编辑节点
}

// 处理画布点击
const handleCanvasClick = (event: MouseEvent) => {
  // 如果点击的是空白区域，取消选择
  if (event.target === canvasRef.value) {
    selectedNode.value = null
  }
}

// 放大
const zoomIn = () => {
  scale.value = Math.min(scale.value + 0.1, 2)
  applyTransform()
}

// 缩小
const zoomOut = () => {
  scale.value = Math.max(scale.value - 0.1, 0.5)
  applyTransform()
}

// 应用缩放和转换
const applyTransform = () => {
  if (canvasRef.value) {
    canvasRef.value.style.transform = `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`
  }
}

// 刷新数据
const refreshData = () => {
  // 触发重新渲染
}

// 监听数据变化
watch(() => props.topologyData, () => {
  // 数据更新时重新渲染
}, { deep: true })

// 组件挂载
onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.topology-graph {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: auto;
  background-color: #f5f5f5;
}

.graph-controls {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.graph-controls .el-button {
  padding: 8px;
}

.legend-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  background: white;
  padding: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.legend-title {
  font-weight: bold;
  margin-bottom: 8px;
  text-align: center;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.legend-text {
  font-size: 12px;
}

.topology-canvas {
  width: 100%;
  height: 100%;
  position: relative;
  background-image: 
    radial-gradient(circle, #d3d3d3 1px, transparent 1px);
  background-size: 20px 20px;
}

.node-item {
  position: absolute;
  width: 120px;
  min-height: 60px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 8px;
  display: flex;
  flex-direction: column;
  user-select: none;
}

.node-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.node-item.selected {
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.5);
}

.node-item.healthy {
  background-color: #f6ffed;
}

.node-item.unhealthy {
  background-color: #fff2e8;
}

.node-header {
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 4px;
  color: #333;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-info {
  flex: 1;
  font-size: 12px;
  color: #666;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.node-basic-info {
  text-align: center;
  margin: 1px 0;
}

.node-basic-info .port {
  color: #909399;
  font-weight: normal;
}

.connections-svg {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
</style>