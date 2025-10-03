import { get, post, put, del } from '@/utils/request'

// 链路相关API
export const linkApi = {
  // 获取链路列表
  getLinks: (params?: any) => get('/api/v1/monitor/links/', params),
  
  // 获取单个链路
  getLink: (id: string) => get(`/api/v1/monitor/links/${id}/`),
  
  // 创建链路
  createLink: (data: any) => post('/api/v1/monitor/links/', data),
  
  // 更新链路
  updateLink: (id: string, data: any) => put(`/api/v1/monitor/links/${id}/`, data),
  
  // 删除链路
  deleteLink: (id: string) => del(`/api/v1/monitor/links/${id}/`),
  
  // 获取链路拓扑
  getLinkTopology: (id: string) => get(`/api/v1/monitor/links/${id}/topology/`)
}

// 节点相关API
export const nodeApi = {
  // 获取节点列表
  getNodes: (params?: any) => get('/api/v1/monitor/nodes/', params),
  
  // 获取单个节点
  getNode: (id: string) => get(`/api/v1/monitor/nodes/${id}/`),
  
  // 创建节点
  createNode: (data: any) => post('/api/v1/monitor/nodes/', data),
  
  // 更新节点
  updateNode: (id: string, data: any) => put(`/api/v1/monitor/nodes/${id}/`, data),
  
  // 删除节点
  deleteNode: (id: string) => del(`/api/v1/monitor/nodes/${id}/`),
  
  // 获取节点健康状态
  getNodeHealth: (id: string) => get(`/api/v1/monitor/nodes/${id}/health/`),
  
  // 获取节点健康历史
  getNodeHealthHistory: (id: string, params?: any) => get(`/api/v1/monitor/nodes/${id}/health_history/`, params),
  
  // 批量获取节点健康状态
  batchGetNodeHealth: (data: any) => post('/api/v1/monitor/nodes/batch_health/', data)
}

// 探活配置API
export const probeConfigApi = {
  // 获取探活配置
  getProbeConfig: () => get('/api/v1/monitor/probe_config/'),
  
  // 更新探活配置
  updateProbeConfig: (data: any) => put('/api/v1/monitor/probe_config/', data)
}

// 连接相关API
export const nodeConnectionApi = {
  // 获取连接列表
  getConnections: (params?: any) => get('/api/v1/monitor/connections/', params),
  
  // 获取单个连接
  getConnection: (id: string) => get(`/api/v1/monitor/connections/${id}/`),
  
  // 创建连接
  createConnection: (data: any) => post('/api/v1/monitor/connections/', data),
  
  // 更新连接
  updateConnection: (id: string, data: any) => put(`/api/v1/monitor/connections/${id}/`, data),
  
  // 删除连接
  deleteConnection: (id: string) => del(`/api/v1/monitor/connections/${id}/`)
}

// 搜索API
export const searchApi = {
  // 全局搜索
  globalSearch: (params?: any) => get('/api/v1/monitor/search/', params)
}