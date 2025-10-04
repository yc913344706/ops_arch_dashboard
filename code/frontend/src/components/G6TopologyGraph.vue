<template>
  <div class="g6-topology-graph" ref="containerRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as G6 from '@antv/g6'

// 定义组件属性
const props = defineProps<{
  topologyData: {
    nodes: Array<any>
    edges: Array<any>
  }
  selectedNode?: any
}>()

// 定义事件
const emit = defineEmits(['nodeClick'])

// 响应式数据
const containerRef = ref<HTMLElement>()
let graphInstance: any = null

// 初始化G6图
const initGraph = async () => {
  if (!containerRef.value) return

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
        stroke: '#1890ff',
        fill: '#e6f7ff',
        lineWidth: 2
      },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: 12,
          fontWeight: 'bold'
        }
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
        autoRotate: true,
        style: {
          fontSize: 10,
          fill: '#666'
        }
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
    isHealthy: node.is_healthy
  }))

  // 准备边数据
  const edges = props.topologyData.edges.map(edge => ({
    id: edge.id || `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: edge.label || edge.direction || ''
  }))

  // 使用read方法设置数据
  try {
    console.log('Graph instance:', graphInstance)
    console.log('Graph instance type:', typeof graphInstance)
    console.log('Available methods:', Object.keys(graphInstance || {}))
    
    if (graphInstance && typeof graphInstance.read === 'function') {
      console.log('Calling graphInstance.read with data:', { nodes, edges })
      graphInstance.read({ nodes, edges })
    } else if (graphInstance && typeof graphInstance.setData === 'function') {
      console.log('Calling graphInstance.setData with data:', { nodes, edges })
      graphInstance.setData({ nodes, edges })
      graphInstance.render()
    } else {
      console.error('Graph instance does not have read or setData method')
      console.log('Graph instance methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(graphInstance)))
    }
  } catch (error) {
    console.error('Error reading graph data:', error)
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
})
</script>

<style scoped>
.g6-topology-graph {
  width: 100%;
  height: 100%;
  background-color: #fafafa;
}
</style>