import { http } from '@/utils/http'
import { apiMap } from '@/config/api'

// API Map 定义
const monitorApiMap = {
  // 链路相关API
  getLinks: '/monitor/links/',
  getLink: (id: string) => `/monitor/links/${id}/`,
  createLink: '/monitor/links/',
  updateLink: (id: string) => `/monitor/links/${id}/`,
  deleteLink: (id: string) => `/monitor/links/${id}/`,
  getLinkTopology: (id: string) => `/monitor/links/${id}/topology/`,
  
  // 节点相关API
  getNodes: '/monitor/nodes/',
  createNode: '/monitor/nodes/',
  updateNode: (id: string) => `/monitor/nodes/${id}/`,
  deleteNode: (id: string) => `/monitor/nodes/${id}/`,
  getNodeHealth: (id: string) => `/monitor/nodes/${id}/health/`,
  
  // 连接相关API
  getConnections: '/monitor/connections/',
  createConnection: '/monitor/connections/',
  updateConnection: (id: string) => `/monitor/connections/${id}/`,
  deleteConnection: (id: string) => `/monitor/connections/${id}/`,
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
  
  // 创建节点
  createNode: (data: any) => http.request('post', monitorApiMap.createNode, { data }),
  
  // 更新节点
  updateNode: (id: string, data: any) => http.request('put', monitorApiMap.updateNode(id), { data }),
  
  // 删除节点
  deleteNode: (id: string) => http.request('delete', monitorApiMap.deleteNode(id)),
  
  // 获取节点健康状态
  getNodeHealth: (id: string) => http.request('get', monitorApiMap.getNodeHealth(id))
}

// 连接相关API
export const nodeConnectionApi = {
  // 获取连接列表
  getConnections: (params?: any) => http.request('get', monitorApiMap.getConnections, { params }),
  
  // 创建连接
  createConnection: (data: any) => http.request('post', monitorApiMap.createConnection, { data }),
  
  // 更新连接
  updateConnection: (id: string, data: any) => http.request('put', monitorApiMap.updateConnection(id), { data }),
  
  // 删除连接
  deleteConnection: (id: string) => http.request('delete', monitorApiMap.deleteConnection(id))
}