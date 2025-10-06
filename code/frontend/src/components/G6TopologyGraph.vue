<template>
  <div class="g6-topology-graph" ref="containerRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as G6 from '@antv/g6'
import { G6_NODE_SIZE } from '@/constants/g6Constants'

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
      'drag-element', // 拖动元素
      // 'create-edge', // 创建边
      // {
      //   type: 'create-edge',
      //   trigger: 'click',
      // }
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
      // nodeSize: G6_NODE_SIZE,
    },
    node: {},
    edge: {
      type: 'polyline', // 边类型，内置边类型名称或者自定义边的名称，比如 line （直线边） 或者 polyline （折线边）
      style: {
        lineWidth: 2
      }
    },
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
          // https://g6.antv.antgroup.com/api/viewport#graphzoombyratio-animation-origin
          graphInstance.zoomBy(1.2);
        } else if (value === 'zoom-out') {
          graphInstance.zoomBy(0.8);
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

// 根据健康状态获取颜色
const getHealthColorByStatus = (healthy_status: string, type: 'fill' | 'stroke') => {
  switch(healthy_status) {  
    case 'green': // 健康  
      return type === 'fill' ? '#f6ffed' : '#52c41a';  // 背景淡绿，主色标准绿
    case 'yellow': // 部分异常  
      return type === 'fill' ? '#fffbe6' : '#faad14';  // 背景淡黄，主色标准黄
    case 'red': // 异常  
      return type === 'fill' ? '#fff1f0' : '#ff4d4f';  // 背景淡红，主色标准红
    case 'unknown': // 未知  
    default:  
      return type === 'fill' ? '#f5f5f5' : '#bfbfbf';  // 灰色，未定义
  }
}

function svgToBase64(svg: any) {
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

const getHealthIconByStatus = (healthy_status: string) => {
  switch(healthy_status) {  
    case 'green': // 健康  
      return svgToBase64('<svg t="1759740438938" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="5805" width="200" height="200"><path d="M610.727508 952.784687c-52.300312 0-103.11349-10.209422-150.96911-30.477881-46.184684-19.566666-87.657327-47.504724-123.281693-83.12909s-63.562424-77.097009-83.112381-123.281693c-20.268459-47.855621-30.477881-98.668799-30.477881-150.96911 0-52.300312 10.209422-103.11349 30.477881-150.969111 19.549957-46.184684 47.504724-87.657327 83.112381-123.281693 35.624366-35.624366 77.097009-63.562424 123.281693-83.11238 47.855621-20.268459 98.668799-30.477881 150.96911-30.477881 52.300312 0 103.11349 10.209422 150.969111 30.477881 46.184684 19.549957 87.657327 47.504724 123.281693 83.11238 35.624366 35.624366 63.562424 77.097009 83.12909 123.281693 20.25175 47.855621 30.477881 98.668799 30.477881 150.969111 0 52.300312-10.209422 103.11349-30.477881 150.96911-19.566666 46.184684-47.504724 87.657327-83.12909 123.281693s-77.097009 63.562424-123.281693 83.12909c-47.855621 20.168203-98.668799 30.477881-150.969111 30.477881z m0-719.822724" fill="#B3F995" p-id="5806"></path><path d="M440.75985 720.641483c-9.440791 0-18.864873-3.575804-25.999772-10.810959L210.705316 505.792471c-14.386763-14.386763-14.386763-37.746455 0-52.133218s37.746455-14.386763 52.133218 0l178.038282 178.038281 318.764551-318.78126c14.386763-14.386763 37.746455-14.386763 52.133218 0s14.386763 37.746455 0 52.133218l-344.897998 344.881288a37.119854 37.119854 0 0 1-26.116737 10.710703z m0 0" fill="#00B48A" p-id="5807"></path><path d="M511.189822 1022.613123c-68.92613 0-135.913973-13.467748-198.975115-40.152604-60.872216-25.78255-115.545257-62.60999-162.498572-109.563304-46.953315-46.953315-83.780755-101.626356-109.546596-162.498573C13.451265 647.3375 0.000227 580.349657 0.000227 511.423527s13.467748-135.913973 40.169312-198.975116c25.78255-60.872216 62.60999-115.545257 109.546596-162.498572 46.953315-46.953315 101.626356-83.780755 162.498572-109.546595C375.27585 13.68497 442.246983 0.233931 511.189822 0.233931c68.942839 0 135.913973 13.467748 198.975116 40.169313 60.872216 25.78255 115.545257 62.60999 162.498572 109.546595 46.953315 46.953315 83.780755 101.626356 109.563305 162.498572 26.701565 63.061143 40.152603 130.048986 40.152603 198.975116 0 68.942839-13.467748 135.913973-40.152603 198.975115-25.78255 60.872216-62.60999 115.545257-109.563305 162.498573-46.953315 46.953315-101.626356 83.780755-162.498572 109.563304-63.061143 26.56789-130.048986 40.152603-198.975116 40.152604z m0-948.724312c-116.79846 0-226.712661 45.466181-309.340469 128.077281-82.627809 82.627809-128.194246 192.642266-128.194247 309.457435 0 116.815169 45.466181 226.712661 128.077281 309.34047 82.627809 82.627809 192.642266 128.210956 309.457435 128.210955 116.815169 0 226.712661-45.449472 309.34047-128.077281 82.627809-82.627809 128.210956-192.642266 128.210956-309.457435 0-116.79846-45.449472-226.712661-128.09399-309.340469-82.644518-82.644518-192.658976-128.210956-309.457436-128.210956z m0 0" fill="#00B48A" p-id="5808"></path></svg>');
    case 'yellow': // 部分异常  
      return svgToBase64('<svg t="1759740408267" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4647" width="200" height="200"><path d="M1001.661867 796.544c48.896 84.906667 7.68 157.013333-87.552 157.013333H110.781867c-97.834667 0-139.050667-69.504-90.112-157.013333l401.664-666.88c48.896-87.552 128.725333-87.552 177.664 0l401.664 666.88zM479.165867 296.533333v341.333334a32 32 0 1 0 64 0v-341.333334a32 32 0 1 0-64 0z m0 469.333334v42.666666a32 32 0 1 0 64 0v-42.666666a32 32 0 1 0-64 0z" fill="#FAAD14" p-id="4648"></path></svg>');  // 背景淡黄，主色标准黄
    case 'red': // 异常  
      return svgToBase64('<svg t="1759740285703" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="3651" width="200" height="200"><path d="M435.205 255.99c-6.003 2.861-11.799 6.004-17.375 9.525-7.532 4.659-9.794 14.466-5.16 21.949a15.921 15.921 0 0 0 13.524 7.52c2.897 0 5.796-0.758 8.413-2.36a144.277 144.277 0 0 1 14.355-7.85c7.948-3.79 11.286-13.303 7.483-21.252-3.791-7.948-13.28-11.409-21.24-7.532z" fill="#FF3333" p-id="3652"></path><path d="M876.832 765.444c-14.99-5.918-78.966-36.462-78.966-127.729V395.972c0-117.557-95.865-226.016-215.183-258.371v-1.993c0-39.557-32.195-71.74-71.728-71.74-0.123 0-0.269 0.012-0.392 0.012-0.147 0-0.256-0.012-0.416-0.012-39.532 0-71.728 32.183-71.728 71.74v1.993c-119.3 32.354-215.189 140.813-215.189 258.371v241.743c0 91.268-63.981 121.812-78.985 127.729-10.913 5.551-18.415 16.825-18.415 29.934 0 18.561 15.028 33.675 33.632 33.675h702.182c18.623 0 33.639-15.114 33.639-33.675-0.011-13.108-7.518-24.383-18.451-29.934z m-346.508-0.172H245.511c23.526-30.422 41.47-72.203 41.47-127.57V432.595c0.263 0.073 0.525 0.122 0.789 0.207v-36.817c0-105.048 108.221-204.361 222.795-204.606 114.536 0.245 222.764 99.558 222.764 204.606v36.817c0.269-0.085 0.538-0.134 0.795-0.207v205.12c0 55.367 17.938 97.136 41.464 127.558H530.324v-0.001z" fill="#FF3333" p-id="3653"></path><path d="M392.249 306.172c-7.104-5.283-17.07-3.815-22.364 3.167-22.97 30.582-35.075 66.922-35.075 105.22v159.425c0 8.791 7.11 15.944 15.939 15.944 8.816 0 15.92-7.153 15.92-15.944V414.559c0-31.352 9.953-61.09 28.686-86.059 5.332-7.08 3.901-17.058-3.106-22.328zM615.221 844.949H569.6c-2.006 0.183-3.79 0.904-5.308 2.03-0.194-0.368-0.439-0.661-0.647-1.003-3.045 1.124-5.588 3.252-6.407 6.529-3.583 22.181-22.39 39.397-45.413 40.18-23.025-0.782-41.832-17.999-45.402-40.18-0.807-3.277-3.351-5.405-6.432-6.529-0.196 0.342-0.416 0.635-0.612 1.003a10.465 10.465 0 0 0-5.331-2.03h-45.609c-4.769 0.293-8.241 3.875-8.975 8.462 4.414 57.506 52.09 103.079 110.685 103.079 0.563 0 1.125-0.049 1.688-0.049 0.562 0 1.113 0.049 1.675 0.049 58.607 0 106.296-45.586 110.697-103.079-0.734-4.598-4.231-8.169-8.988-8.462z" fill="#FF3333" p-id="3654"></path></svg>');  // 背景淡红，主色标准红
    case 'unknown': // 未知  
    default:  
      return svgToBase64('<svg t="1759740810131" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="9780" width="200" height="200"><path d="M928.214 336.161c-22.752-53.794-55.319-102.1-96.799-143.579-41.476-41.476-89.786-74.048-143.578-96.799-55.705-23.562-114.866-35.506-175.839-35.506S391.866 72.224 336.16 95.783c-53.794 22.753-102.1 55.321-143.579 96.799-41.477 41.477-74.048 89.786-96.799 143.579-23.562 55.705-35.506 114.866-35.506 175.838 0 60.973 11.947 120.132 35.506 175.838 22.753 53.794 55.319 102.102 96.799 143.579 41.477 41.477 89.786 74.048 143.579 96.799 55.705 23.563 114.866 35.509 175.838 35.509s120.132-11.946 175.839-35.509c53.792-22.752 102.1-55.319 143.578-96.799 41.477-41.476 74.048-89.786 96.799-143.579 23.563-55.705 35.509-114.865 35.509-175.838 0-60.972-11.946-120.132-35.509-175.838zM511.999 919.017c-224.429 0-407.015-182.589-407.015-407.017S287.57 104.985 511.999 104.985c224.429 0 407.015 182.586 407.015 407.015S736.428 919.017 511.999 919.017z" p-id="9781" fill="#8a8a8a"></path><path d="M708.637 511.483c0 18.691-14.658 33.842-32.735 33.842H348.931c-18.08 0-32.736-15.151-32.736-33.842s14.657-33.842 32.736-33.842h326.971c18.077 0 32.735 15.151 32.735 33.842z" p-id="9782" fill="#8a8a8a"></path></svg>');  // 灰色，未定义
  }
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
      id: node.uuid || node.id,
      basic_info_list: node.basic_info_list || [],
      healthy_status: node.healthy_status,

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
      // x: node.position_x,
      // y: node.position_y,
      // isHealthy: node.is_healthy,
      // size: [80, 40], // 调整节点尺寸为更合适的大小
      style: {
        /* 主图形
         * - 主图形是节点的核心部分，定义了节点的基本形状和外观。
         * - 完整配置项https://g6.antv.antgroup.com/manual/element/node/base-node#%E8%99%9A%E7%BA%BF%E8%BE%B9%E6%A1%86%E6%A0%B7%E5%BC%8F
         */
        fill: getHealthColorByStatus(node.healthy_status, 'fill'),  // 填充
        lineWidth: 2, // 线宽
        radius: 6, // 圆角
        stroke: getHealthColorByStatus(node.healthy_status, 'stroke'), // 描边
        size: G6_NODE_SIZE, // 调整节点尺寸为更合适的大小

        /* 标签
         * - 标签用于显示节点的文本信息，支持多种样式配置和布局方式。
         */
        labelText: node.name, // 节点名称
        labelWordWrap: true, // 自动换行
        labelMaxWidth: '150%', // 节点宽度的百分比
        labelMaxLines: 3, // 最大行数
        labelTextOverflow: 'ellipsis', // 超出部分显示省略号
        labelPlacement: 'bottom', // 标签位置
        labelTextAlign: 'center', // 节点文本水平居中
        labelFill: '#002060', // 节点标签颜色
        labelFontWeight: 'bold', // 加粗
        // labelFill: '#0070c0', // 节点标签颜色
        // labelFill: '#C41D7F', // 节点标签颜色
        labelFontSize: 12, // 字体大小

        /* 图标样式
         * - 节点图标支持三种常见的使用方式：文字图标、图片图标和 IconFont 图标。
         */
        // iconText: node.name,
        // iconFill: '#C41D7F', // 深粉色图标
        iconSrc: getHealthIconByStatus(node.healthy_status)

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
      source: edge.source,
      target: edge.target,
      style: {
        stroke: getHealthColorByStatus(edge.healthy_status, 'stroke'), // 边颜色
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