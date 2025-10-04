<template>
  <div class="topology-graph">
    <div class="graph-container" ref="graphContainerRef"></div>
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
      <el-button @click="refreshData" title="刷新">
        <el-icon><Refresh /></el-icon>
      </el-button>
      <el-button 
        v-if="!readOnly" 
        @click="enableNodeCreation" 
        :type="isCreatingNode ? 'primary' : 'default'"
        title="创建节点">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>
    <div class="legend-panel">
      <div class="legend-title">健康状态图例</div>
      <div class="legend-item" v-for="status in healthStatuses" :key="status.code">
        <span class="legend-color" :style="{ backgroundColor: status.color }"></span>
        <span class="legend-text">{{ status.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { 
  ZoomIn, 
  ZoomOut, 
  FullScreen, 
  Refresh,
  Plus
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

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
const graphContainerRef = ref<HTMLElement>()
let graphInstance: any = null
const isCreatingNode = ref(false)

// 健康状态定义
const healthStatuses = [
  { code: 'healthy', text: '健康', color: '#52c41a' },
  { code: 'warning', text: '警告', color: '#faad14' },
  { code: 'error', text: '错误', color: '#ff4d4f' },
  { code: 'unknown', text: '未知', color: '#bfbfbf' }
]

// 初始化图表
const initGraph = async () => {
  if (!graphContainerRef.value) return
  
  // 等待DOM更新
  await nextTick()
  
  // 获取容器尺寸
  const container = graphContainerRef.value
  const width = container.clientWidth
  const height = container.clientHeight
  
  // 动态导入G6
  const G6Module = await import('@antv/g6')
  const G6 = G6Module?.default || G6Module
  
  // 创建G6图实例
  graphInstance = new G6.Graph({
    container: container,
    width,
    height,
    modes: {
      default: props.readOnly 
        ? ['zoom-canvas', 'drag-canvas', 'drag-node'] 
        : ['zoom-canvas', 'drag-canvas', 'drag-node', 'click-select']
    },
    defaultNode: {
      type: 'rect',  // 使用矩形节点更适合架构图
      size: [80, 40],
      style: {
        lineWidth: 2,
        fill: '#fff',
        radius: 4
      },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: 12,
        },
      },
    },
    defaultEdge: {
      type: 'polyline',
      style: {
        radius: 10,
        offset: 20,
        endArrow: true,
        lineWidth: 2,
        stroke: '#999',
      },
      labelCfg: {
        autoRotate: true,
        style: {
          fontSize: 10,
          fill: '#666',
          background: {
            fill: '#fff',
            stroke: '#666',
            padding: [2, 4],
            radius: 2,
          },
        },
      },
    },
    nodeStateStyles: {
      hover: {
        fillOpacity: 0.8,
      },
      selected: {
        lineWidth: 3,
      },
    },
    layout: {
      type: 'grid', // 使用网格布局更适合架构图
      preventOverlap: true,
      nodeSize: [80, 40],
    },
  })

  // 监听节点点击事件
  graphInstance.on('node:click', (evt: any) => {
    const node = evt.item.getModel()
    emit('nodeClick', node)
  })

  // 监听画布点击事件，用于创建节点
  graphInstance.on('canvas:click', (evt: any) => {
    if (isCreatingNode.value) {
      // 如果正在创建节点模式，触发创建事件
      emit('nodeCreate', { x: evt.x, y: evt.y })
      isCreatingNode.value = false  // 重置创建模式
    }
  })

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
}

// 根据健康状态获取节点颜色
const getNodeColorByHealth = (status: boolean) => {
  return status ? '#52c41a' : '#ff4d4f' // 绿色表示健康，红色表示不健康
}

// 渲染拓扑数据
const renderTopology = () => {
  if (!graphInstance || !props.topologyData) return
  
  // 准备节点数据
  const nodes = props.topologyData.nodes.map(node => ({
    id: node.uuid || node.id,
    label: node.name,
    x: node.position_x,
    y: node.position_y,
    isHealthy: node.is_healthy,
    type: 'rect',
    size: [80, 40],
    style: {
      fill: node.is_healthy ? '#e6f7ff' : '#fff2e8', // 健康为浅蓝，不健康为浅橙
      stroke: node.is_healthy ? '#1890ff' : '#ff7a45',
      lineWidth: 2,
      radius: 4,
    },
    labelCfg: {
      style: {
        fill: '#333',
        fontSize: 10,
        fontWeight: 'bold'
      }
    }
  }))
  
  // 准备边数据
  const edges = props.topologyData.edges.map(edge => ({
    id: edge.id || `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: edge.label || edge.direction || '',
    style: {
      stroke: '#999',
      lineWidth: 2
    }
  }))
  
  // 重新创建整个图表（如果data方法不可用）
  try {
    // 尝试使用标准G6 API
    if (typeof graphInstance.data === 'function') {
      graphInstance.data({ nodes, edges })
      graphInstance.render()
      graphInstance.fitView([20, 20])
    } else {
      // 如果标准方法不可用，重新初始化
      graphInstance.clear()
      graphInstance.addNodes(nodes)
      graphInstance.addEdges(edges)
      graphInstance.render()
      graphInstance.fitView([20, 20])
    }
  } catch (error) {
    console.error('Error rendering topology:', error)
    // 备用方法：完全重新创建图表
    if (graphInstance) {
      graphInstance.clear()
      nodes.forEach(node => graphInstance.addItem('node', node))
      edges.forEach(edge => graphInstance.addItem('edge', edge))
      graphInstance.render()
      graphInstance.fitView([20, 20])
    }
  }
}

// 放大
const zoomIn = () => {
  if (graphInstance) {
    graphInstance.zoom(1.2)
  }
}

// 缩小
const zoomOut = () => {
  if (graphInstance) {
    graphInstance.zoom(0.8)
  }
}

// 适应视图
const fitView = () => {
  if (graphInstance) {
    graphInstance.fitView([20, 20]);
  }
}

// 刷新数据
const refreshData = () => {
  renderTopology()
}

// 启用节点创建模式
const enableNodeCreation = () => {
  if (props.readOnly) return
  isCreatingNode.value = !isCreatingNode.value
  if (isCreatingNode.value) {
    ElMessage.info('点击画布任意位置创建新节点')
  }
}

// 处理窗口大小变化
const handleResize = () => {
  if (graphInstance && graphContainerRef.value) {
    const { clientWidth, clientHeight } = graphContainerRef.value
    if (typeof graphInstance.changeSize === 'function') {
      graphInstance.changeSize(clientWidth, clientHeight)
    } else {
      // 如果changeSize方法不可用
      graphInstance.changeSize(clientWidth, clientHeight)
    }
  }
}

// 监听数据变化
watch(() => props.topologyData, () => {
  renderTopology()
}, { deep: true })

// 监听只读模式变化
watch(() => props.readOnly, (newVal) => {
  if (graphInstance) {
    if (newVal) {
      graphInstance.setMode('default')
    } else {
      graphInstance.setMode('default')
    }
  }
})

// 组件挂载
onMounted(async () => {
  await initGraph()
  renderTopology()
})

// 组件卸载
onUnmounted(() => {
  if (graphInstance) {
    graphInstance.destroy()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.topology-graph {
  width: 100%;
  height: 100%;
  position: relative;
}

.graph-container {
  width: 100%;
  height: 100%;
  border: 1px solid #e4e7ed;
  background-color: #fafafa;
  overflow: hidden;
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
</style>