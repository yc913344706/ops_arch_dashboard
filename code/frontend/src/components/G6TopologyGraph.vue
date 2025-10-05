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
let currentNodes: any[] = []

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
    if (evt) {
      // 从事件对象中获取节点ID
      const target = evt.item || evt.target
      if (target && target.id) {
        // 使用节点ID查找完整的节点数据
        const nodeId = target.id
        
        // 从当前设置的数据中查找节点
        const node = currentNodes.find((n: any) => n.id === nodeId)
        if (node) {
          emit('nodeClick', node)
        }
      }
    }
  })

  // 监听画布点击事件
  graphInstance.on('canvas:click', (evt: any) => {
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
    isHealthy: node.is_healthy,
    type: 'rect'
  }))

  // 准备边数据
  const edges = props.topologyData.edges.map(edge => ({
    id: edge.id || `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: edge.label || edge.direction || ''
  }))

  // 保存当前节点数据以便后续查找
  currentNodes = nodes

  // 使用setData方法设置数据
  if (graphInstance && typeof graphInstance.setData === 'function') {
    graphInstance.setData({ nodes, edges })
    graphInstance.render()
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