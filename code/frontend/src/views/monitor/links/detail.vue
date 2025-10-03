<template>
  <div class="link-detail-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>链路拓扑图</span>
          <div>
            <el-button @click="goBack">返回</el-button>
            <el-button type="primary" @click="refreshTopology">刷新</el-button>
          </div>
        </div>
      </template>
      
      <div class="topology-container">
        <TopologyGraph 
          :topology-data="topologyData" 
          :read-only="false"
          @node-click="handleNodeClick"
        />
      </div>
    </el-card>
    
    <!-- 节点详情面板 -->
    <el-drawer
      v-model="nodeDetailVisible"
      title="节点详情"
      size="400px"
    >
      <NodeDetailPanel 
        :node="selectedNode" 
        @edit="handleEditNode"
        @delete="handleDeleteNode"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { linkApi } from '@/api/monitor'

// 引入拓扑图组件（将在后续步骤中创建）
const TopologyGraph = defineAsyncComponent(() => import('@/components/TopologyGraph.vue'))
const NodeDetailPanel = defineAsyncComponent(() => import('@/components/NodeDetailPanel.vue'))

const router = useRouter()
const route = useRoute()

const topologyData = ref({
  nodes: [],
  edges: []
})
const nodeDetailVisible = ref(false)
const selectedNode = ref(null)

// 获取链路ID
const linkId = computed(() => route.params.id as string)

// 获取拓扑数据
const fetchTopologyData = async () => {
  if (!linkId.value) return
  
  try {
    // 这里应该调用获取链路拓扑的API
    // const response = await linkApi.getLinkTopology(linkId.value)
    // 模拟数据
    topologyData.value = {
      nodes: [
        { uuid: '1', name: '负载均衡器', ip_address: '192.168.1.10', is_healthy: true, position_x: 100, position_y: 200 },
        { uuid: '2', name: 'Web服务器1', ip_address: '192.168.1.11', is_healthy: true, position_x: 250, position_y: 100 },
        { uuid: '3', name: 'Web服务器2', ip_address: '192.168.1.12', is_healthy: true, position_x: 250, position_y: 300 },
        { uuid: '4', name: '数据库', ip_address: '192.168.1.20', is_healthy: false, position_x: 400, position_y: 200 }
      ],
      edges: [
        { source: '1', target: '2' },
        { source: '1', target: '3' },
        { source: '2', target: '4' },
        { source: '3', target: '4' }
      ]
    }
  } catch (error) {
    console.error('获取拓扑数据失败:', error)
  }
}

// 处理节点点击事件
const handleNodeClick = (node: any) => {
  selectedNode.value = node
  nodeDetailVisible.value = true
}

// 刷新拓扑图
const refreshTopology = () => {
  fetchTopologyData()
}

// 返回链路列表
const goBack = () => {
  router.push('/monitor/links')
}

// 处理编辑节点
const handleEditNode = () => {
  console.log('编辑节点:', selectedNode.value)
  // 在实际实现中，这里会打开编辑节点的对话框
}

// 处理删除节点
const handleDeleteNode = () => {
  console.log('删除节点:', selectedNode.value)
  // 在实际实现中，这里会调用删除节点的API
  nodeDetailVisible.value = false
}

// 页面挂载时获取数据
onMounted(() => {
  fetchTopologyData()
})
</script>

<style scoped>
.link-detail-page {
  padding: 20px;
  height: calc(100vh - 120px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.topology-container {
  height: calc(100vh - 200px);  /* 调整高度以适应页面布局 */
}
</style>