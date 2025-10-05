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
    // 自动适配策略，'view'(适应视图) | 'center'(居中) | object
    autoFit: 'center',
    // 交互：https://g6.antv.antgroup.com/manual/behavior/overview
    behaviors: [
      'drag-canvas', // 拖动整个画布视图
      'zoom-canvas', // 缩放画布视图
      'click-select', // 点击选择图元素
    ],
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
    node: {},
    edge: {},
    // 工具栏： https://g6.antv.antgroup.com/manual/plugin/toolbar
    plugins: [
    {
      type: 'toolbar',
      position: 'top-right',
      getItems: () => [
        { id: 'zoom-in', value: 'zoom-in' },
        { id: 'zoom-out', value: 'zoom-out' },
        { id: 'auto-fit', value: 'auto-fit' },
      ],
      onClick: (value) => {
        // 处理按钮点击事件
        if (value === 'zoom-in') {
          graphInstance.zoomTo(1.1);
        } else if (value === 'zoom-out') {
          graphInstance.zoomTo(0.9);
        } else if (value === 'auto-fit') {
          graphInstance.fitView();
        }
      },
    },
  ],
  })

  // 事件： https://g6.antv.antgroup.com/api/event
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
    // node 属性： https://g6.antv.antgroup.com/manual/element/node/base-node#nodeoptions
    return {
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
      id: node.uuid || node.id,
      // x: node.position_x,
      // y: node.position_y,
      // isHealthy: node.is_healthy,
      // size: [80, 40], // 调整节点尺寸为更合适的大小
      style: {
        /* 主图形
         * - 主图形是节点的核心部分，定义了节点的基本形状和外观。
         * - 完整配置项https://g6.antv.antgroup.com/manual/element/node/base-node#%E8%99%9A%E7%BA%BF%E8%BE%B9%E6%A1%86%E6%A0%B7%E5%BC%8F
         */
        fill: node.is_healthy ? '#e6f7ff' : '#fff2e8',  // 填充
        lineWidth: 2, // 线宽
        radius: 6, // 圆角
        stroke: node.is_healthy ? '#1890ff' : '#ff7a45', // 描边
        size: [80, 40], // 调整节点尺寸为更合适的大小

        /* 标签
         * - 标签用于显示节点的文本信息，支持多种样式配置和布局方式。
         */
        // labelText: node.name, // 节点名称
        // labelWordWrap: true, // 自动换行
        // labelMaxWidth: '150%', // 节点宽度的百分比
        // labelMaxLines: 3, // 最大行数
        // labelTextOverflow: 'ellipsis', // 超出部分显示省略号
        // labelPlacement: 'bottom', // 标签位置
        // labelTextAlign: 'center', // 节点文本水平居中

        /* 图标样式
         * - 节点图标支持三种常见的使用方式：文字图标、图片图标和 IconFont 图标。
         */
        iconText: node.name,
        iconFill: '#C41D7F', // 深粉色图标

        /* 连接桩样式
         * - 连接桩是节点上的连接点，用于连接边。
         */
        // port: true,
        // ports: [
        //   { key: 'top', placement: 'top', fill: '#7E92B5' },
        //   { key: 'right', placement: 'right', fill: '#F4664A' },
        //   { key: 'bottom', placement: 'bottom', fill: '#FFBE3A' },
        //   { key: 'left', placement: 'left', fill: '#D580FF' },
        // ],
        // portR: 3,
        // portLineWidth: 1,
        // portStroke: '#fff',
      }
    }
  })
  console.log('Processed nodes:', nodes)

  // 准备边数据
  console.log('Preparing edges from topology data:', props.topologyData.edges)
  const edges = props.topologyData.edges.map(edge => {
    console.log('Processing edge:', edge)
    return {
      /**
       * edge 边： https://g6.antv.antgroup.com/manual/element/edge/overview
       * 
       * 配置边的方式有三种，按优先级从高到低如下：
       * - 使用 graph.setEdge() 动态配置
       * - 实例化图时全局配置
       * - 在数据中动态属性
       * 
       * 边配置：
       * - 通用配置： https://g6.antv.antgroup.com/manual/element/edge/base-edge
       * - 折线边配置： https://g6.antv.antgroup.com/manual/element/edge/polyline
       * 
       */
      id: edge.id || `${edge.source}-${edge.target}`,

      type: 'polyline', // 边类型，内置边类型名称或者自定义边的名称，比如 line （直线边） 或者 polyline （折线边）
      
      source: edge.source,
      target: edge.target,

      // label: edge.label || edge.direction || '',
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
    console.log('Setting data for graph instance:', { nodes: nodes, edges: edges })
    // setdata: https://g6.antv.antgroup.com/api/data#graphsetdata
    graphInstance.setData({ nodes: nodes, edges: edges })

    console.log('Rendering graph instance...')
    // render: https://g6.antv.antgroup.com/api/render#graphrender
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