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
  console.log('Graph size:', width, height)

  // 创建G6图实例
  graphInstance = new G6.Graph({
    /*
     * graph 配置： https://g6.antv.antgroup.com/manual/graph/graph
     */
    // 图容器，可以是 DOM 元素 ID、DOM 元素实例或 Canvas 实例
    container: containerRef.value,
    // 容器宽度	画布宽度(像素)
    width,
    // 容器高度	画布高度(像素)
    height,
    modes: {
      default: ['drag-canvas', 'zoom-canvas']
    },
    layout: {
      /**
       * 布局： dagre： 
       * - 基础： https://g6.antv.antgroup.com/manual/layout/dagre-layout
       * - 更多： https://github.com/dagrejs/dagre/wiki#configuring-the-layout
       * - 例子： https://g6.antv.antgroup.com/examples/layout/dagre/#antv-dagre
       */
      type: 'dagre',
      /* 布局方向，可选值	TB | BT | LR | RL， 默认值：TB
       *  where T = top, B = bottom, L = left, and R = right.
       */
      rankdir: 'TB',
      // 节点间距（px）。在rankdir 为 TB 或 BT 时是节点的水平间距；在rankdir 为 LR 或 RL 时代表节点的竖直方向间距
      nodesep: 30,
      // 层间距（px）。在rankdir 为 TB 或 BT 时是竖直方向相邻层间距；在rankdir 为 LR 或 RL 时代表水平方向相邻层间距
      ranksep: 50,
      nodeSize: [80, 40],
    },
    defaultNode: {
      /**
       * 节点通用配置项： https://g6.antv.antgroup.com/manual/element/node/base-node
       *     type: 'circle', // 节点类型
       *     style: {}, // 节点样式
       *     state: {}, // 状态样式
       *     palette: {}, // 色板配置
       *     animation: {}, // 动画配置
       * 
       * rect 节点： https://g6.antv.antgroup.com/manual/element/node/rect
       */
      type: 'rect',
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
        },
        offset: 0 // 确保标签在节点中心显示
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
  console.log('Preparing nodes from topology data:', props.topologyData.nodes)
  const nodes = props.topologyData.nodes.map(node => {
    console.log('Processing node:', node)
    return {
      id: node.uuid || node.id,
      label: node.name,
      x: node.position_x,
      y: node.position_y,
      isHealthy: node.is_healthy,
      type: 'rect',
      size: [80, 40], // 调整节点尺寸为更合适的大小
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
        },
        offset: 0 // 确保标签在节点中心显示
      }
    }
  })
  console.log('Processed nodes:', nodes)

  // 准备边数据
  console.log('Preparing edges from topology data:', props.topologyData.edges)
  const edges = props.topologyData.edges.map(edge => {
    console.log('Processing edge:', edge)
    return {
      id: edge.id || `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: edge.label || edge.direction || '',
      style: {
        stroke: '#999',
        lineWidth: 2
      }
    }
  })
  console.log('Processed edges:', edges)

  // 保存当前节点数据以便后续查找
  currentNodes = nodes

  // 使用setData方法设置数据
  if (graphInstance && typeof graphInstance.setData === 'function') {
    graphInstance.setData({ nodes, edges })
    graphInstance.render()
    
    // 确保标签正确显示
    setTimeout(() => {
      if (graphInstance) {
        graphInstance.fitView([20, 20])
      }
    }, 100)
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