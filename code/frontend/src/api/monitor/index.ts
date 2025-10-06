import { http } from '@/utils/http'
import { apiMap } from '@/config/api'

// API Map 定义
const monitorApiMap = {
  // 链路相关API
  getLinks: '/monitor/links/',
  getLink: '/monitor/links/detail/',
  createLink: '/monitor/links/',
  updateLink: '/monitor/links/',
  deleteLink: '/monitor/links/',
  getLinkTopology: `/monitor/link/topology/`,
  
  // 节点相关API
  getNodes: '/monitor/nodes/',
  createNode: '/monitor/nodes/',
  updateNode: '/monitor/nodes/',
  deleteNode: '/monitor/nodes/',
  getNodeHealth: '/monitor/nodes/health/',
  
  // 连接相关API
  getConnections: '/monitor/connections/',
  createConnection: '/monitor/connections/',
  updateConnection: '/monitor/connections/',
  deleteConnection: '/monitor/connections/',
}

// 链路相关API
export const linkApi = {
  // 获取链路列表
  getLinks: (params?: any) => http.request('get', monitorApiMap.getLinks, { params }),
  
  // 获取单个链路
  getLink: (params: any) => http.request('get', monitorApiMap.getLink, { params }),
  
  // 创建链路
  createLink: (data: any) => http.request('post', monitorApiMap.createLink, { data }),
  
  // 更新链路
  updateLink: (data: any) => http.request('put', monitorApiMap.updateLink, { data }),
  
  // 删除链路
  deleteLink: (params: any) => http.request('delete', monitorApiMap.deleteLink, { params }),
  
  // 获取链路拓扑
  getLinkTopology: (params: any) => http.request('get', monitorApiMap.getLinkTopology, { params })
}

// 节点相关API
export const nodeApi = {
  // 获取节点列表
  getNodes: (params?: any) => http.request('get', monitorApiMap.getNodes, { params }),
  
  // 创建节点
  createNode: (data: any) => http.request('post', monitorApiMap.createNode, { data }),
  
  // 更新节点
  updateNode: (data: any) => http.request('put', monitorApiMap.updateNode, { data }),
  
  // 删除节点
  deleteNode: (params: any) => http.request('delete', monitorApiMap.deleteNode, { params }),
  
  // 获取节点健康状态
  getNodeHealth: (params: any) => http.request('get', monitorApiMap.getNodeHealth, { params })
}

// 连接相关API
export const nodeConnectionApi = {
  // 获取连接列表
  getConnections: (params?: any) => http.request('get', monitorApiMap.getConnections, { params }),
  
  // 创建连接
  createConnection: (data: any) => http.request('post', monitorApiMap.createConnection, { data }),
  
  // 更新连接
  updateConnection: (data: any) => http.request('put', monitorApiMap.updateConnection, { data }),
  
  // 删除连接
  deleteConnection: (params: any) => http.request('delete', monitorApiMap.deleteConnection, { params })
}