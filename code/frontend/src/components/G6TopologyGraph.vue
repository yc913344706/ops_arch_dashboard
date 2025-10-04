<template>
  <div class="g6-topology-graph" ref="containerRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import G6 from '@antv/g6'

// 定义组件属性
const props = defineProps<{
  topologyData: {
    nodes: Array<any>
    edges: Array<any>
  }
  selectedNode?: any
  readOnly?: boolean
}>()

// 定义事件
const emit = defineEmits(['nodeClick'])

// 响应式数据
const containerRef = ref<HTMLElement>()
let graphInstance: any = null

// 初始化G6图
const initGraph = async () => {
  if (!containerRef.value) return

  // 等待DOM更新
  await nextTick()

  // 获取容器尺寸
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight

  // 创建G6图实例
  graphInstance = new G6.Graph({
    container: containerRef.value,
    width,
    height,
    modes: {
      default: ['drag-canvas', 'zoom-canvas']
    },
    layout: {
      type: 'dagre',
      rankdir: 'TB',
      nodesep: 30,
      ranksep: 50
    },
    defaultNode: {
      type: 'rect',
      size: [120, 60],
      style: {
        radius: 6,
        stroke: '#5B8FF9',
        fill: '#C6E5FF',
        lineWidth: 2
      },
      labelCfg: {
        style: {
          fill: '#000',
          fontSize: 12
        },
        offset: 10
      }
    },
    defaultEdge: {
      type: 'polyline',
      style: {
        stroke: '#999',
        lineWidth: 2,
        endArrow: true
      },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: 10
        }
      }
    },
    nodeStateStyles: {
      selected: {
        stroke: '#1890ff',
        lineWidth: 3
      },
      hover: {
        fillOpacity: 0.8
      }
    },
    edgeStateStyles: {
      selected: {
        stroke: '#1890ff',
        lineWidth: 3
      }
    }
  })

  // 监听节点点击事件
  graphInstance.on('node:click', (evt: any) => {
    const node = evt.item.getModel()
    emit('nodeClick', node)
  })

  // 监听画布点击事件
  graphInstance.on('canvas:click', () => {
    emit('nodeClick', null)
  })

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
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
    size: [120, 60],
    style: {
      fill: node.is_healthy ? '#e6f7ff' : '#fff2e8',
      stroke: node.is_healthy ? '#1890ff' : '#ff7a45',
      lineWidth: 2,
      radius: 6
    },
    labelCfg: {
      style: {
        fill: '#333',
        fontSize: 12,
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

  // 设置数据并渲染
  graphInstance.data({ nodes, edges })
  graphInstance.render()

  // 适应视图
  graphInstance.fitView([20, 20])

  // 高亮选中的节点
  if (props.selectedNode) {
    const nodeId = props.selectedNode.uuid || props.selectedNode.id
    const nodeItem = graphInstance.findById(nodeId)
    if (nodeItem) {
      graphInstance.setItemState(nodeItem, 'selected', true)
    }
  }
}

// 处理窗口大小变化
const handleResize = () => {
  if (graphInstance && containerRef.value) {
    const { clientWidth, clientHeight } = containerRef.value
    graphInstance.changeSize(clientWidth, clientHeight)
    graphInstance.fitView([20, 20])
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
    graphInstance.fitView([20, 20])
  }
}

// 监听数据变化
watch(
  () => props.topologyData,
  () => {
    renderTopology()
  },
  { deep: true }
)

// 监听选中节点变化
watch(
  () => props.selectedNode,
  (newVal, oldVal) => {
    if (graphInstance) {
      // 取消旧节点的选中状态
      if (oldVal) {
        const oldNodeId = oldVal.uuid || oldVal.id
        const oldNodeItem = graphInstance.findById(oldNodeId)
        if (oldNodeItem) {
          graphInstance.setItemState(oldNodeItem, 'selected', false)
        }
      }

      // 高亮新节点
      if (newVal) {
        const newNodeId = newVal.uuid || newVal.id
        const newNodeItem = graphInstance.findById(newNodeId)
        if (newNodeItem) {
          graphInstance.setItemState(newNodeItem, 'selected', true)
        }
      }
    }
  },
  { deep: true }
)

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
.g6-topology-graph {
  width: 100%;
  height: 100%;
  background-color: #fafafa;
}
</style>