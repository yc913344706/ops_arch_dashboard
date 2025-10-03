import { http } from '@/utils/http'
import { apiMap } from '@/config/api'

// API Map 定义
const monitorApiMap = {
  // 链路相关API
  getLinks: '/api/v1/monitor/links/',
  getLink: (id: string) => `/api/v1/monitor/links/${id}/`,
  createLink: '/api/v1/monitor/links/',
  updateLink: (id: string) => `/api/v1/monitor/links/${id}/`,
  deleteLink: (id: string) => `/api/v1/monitor/links/${id}/`,
  getLinkTopology: (id: string) => `/api/v1/monitor/links/${id}/topology/`,
  
  // 节点相关API
  getNodes: '/api/v1/monitor/nodes/',
  getNode: (id: string) => `/api/v1/monitor/nodes/${id}/`,
  createNode: '/api/v1/monitor/nodes/',
  updateNode: (id: string) => `/api/v1/monitor/nodes/${id}/`,
  deleteNode: (id: string) => `/api/v1/monitor/nodes/${id}/`,
  getNodeHealth: (id: string) => `/api/v1/monitor/nodes/${id}/health/`,
  getNodeHealthHistory: (id: string) => `/api/v1/monitor/nodes/${id}/health_history/`,
  getBatchNodeHealth: '/api/v1/monitor/nodes/batch_health/',
  
  // 连接相关API
  getConnections: '/api/v1/monitor/connections/',
  getConnection: (id: string) => `/api/v1/monitor/connections/${id}/`,
  createConnection: '/api/v1/monitor/connections/',
  updateConnection: (id: string) => `/api/v1/monitor/connections/${id}/`,
  deleteConnection: (id: string) => `/api/v1/monitor/connections/${id}/`,
  
  // 探活配置API
  getProbeConfig: '/api/v1/monitor/probe_config/',
  updateProbeConfig: '/api/v1/monitor/probe_config/',
  
  // 搜索API
  globalSearch: '/api/v1/monitor/search/',
}

// 链路相关API
export const linkApi = {
  // 获取链路列表
  getLinks: (params?: any) => http.request('get', monitorApiMap.getLinks, { params }),
  
  // 获取单个链路
  getLink: (id: string) => http.request('get', monitorApiMap.getLink(id)),
  
  // 创建链路
  createLink: (data: any) => http.request('post', monitorApiMap.createLink, { data }),
  
  // 更新链路
  updateLink: (id: string, data: any) => http.request('put', monitorApiMap.updateLink(id), { data }),
  
  // 删除链路
  deleteLink: (id: string) => http.request('delete', monitorApiMap.deleteLink(id)),
  
  // 获取链路拓扑
  getLinkTopology: (id: string) => http.request('get', monitorApiMap.getLinkTopology(id))
}

// 节点相关API
export const nodeApi = {
  // 获取节点列表
  getNodes: (params?: any) => http.request('get', monitorApiMap.getNodes, { params }),
  
  // 获取单个节点
  getNode: (id: string) => http.request('get', monitorApiMap.getNode(id)),
  
  // 创建节点
  createNode: (data: any) => http.request('post', monitorApiMap.createNode, { data }),
  
  // 更新节点
  updateNode: (id: string, data: any) => http.request('put', monitorApiMap.updateNode(id), { data }),
  
  // 删除节点
  deleteNode: (id: string) => http.request('delete', monitorApiMap.deleteNode(id)),
  
  // 获取节点健康状态
  getNodeHealth: (id: string) => http.request('get', monitorApiMap.getNodeHealth(id)),
  
  // 获取节点健康历史
  getNodeHealthHistory: (id: string, params?: any) => http.request('get', monitorApiMap.getNodeHealthHistory(id), { params }),
  
  // 批量获取节点健康状态
  batchGetNodeHealth: (data: any) => http.request('post', monitorApiMap.getBatchNodeHealth, { data })
}

// 连接相关API
export const nodeConnectionApi = {
  // 获取连接列表
  getConnections: (params?: any) => http.request('get', monitorApiMap.getConnections, { params }),
  
  // 获取单个连接
  getConnection: (id: string) => http.request('get', monitorApiMap.getConnection(id)),
  
  // 创建连接
  createConnection: (data: any) => http.request('post', monitorApiMap.createConnection, { data }),
  
  // 更新连接
  updateConnection: (id: string, data: any) => http.request('put', monitorApiMap.updateConnection(id), { data }),
  
  // 删除连接
  deleteConnection: (id: string) => http.request('delete', monitorApiMap.deleteConnection(id))
}

// 探活配置API
export const probeConfigApi = {
  // 获取探活配置
  getProbeConfig: () => http.request('get', monitorApiMap.getProbeConfig),
  
  // 更新探活配置
  updateProbeConfig: (data: any) => http.request('put', monitorApiMap.updateProbeConfig, { data })
}

// 搜索API
export const searchApi = {
  // 全局搜索
  globalSearch: (params?: any) => http.request('get', monitorApiMap.globalSearch, { params })
}