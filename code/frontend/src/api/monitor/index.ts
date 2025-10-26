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
  
  // 告警相关API
  getAlerts: '/monitor/alerts/',
  getAlert: '/monitor/alert/',
  createAlert: '/monitor/alerts/',
  updateAlert: '/monitor/alert/',
  deleteAlert: '/monitor/alert/',
  getAlertTypes: '/monitor/alert-types/',
  
  // 监控仪表板相关API
  getDashboardStats: '/monitor/dashboard/',
  
  // 基础信息相关API
  getBaseInfoList: '/monitor/baseinfo/',
  
  // 系统健康统计相关API
  getSystemHealthStats: '/monitor/system_health_stats/',
  
  // PushPlus配置相关API
  getPushPlusConfigs: '/monitor/pushplus-configs/',
  getPushPlusConfig: '/monitor/pushplus-config/',
  createPushPlusConfig: '/monitor/pushplus-configs/',
  updatePushPlusConfig: '/monitor/pushplus-config/',
  deletePushPlusConfig: '/monitor/pushplus-config/',
  testPushPlusConfig: '/monitor/pushplus-test/',
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

// 告警相关API
export const alertApi = {
  // 获取告警列表
  getAlerts: (params?: any) => http.request('get', monitorApiMap.getAlerts, { params }),
  
  // 获取单个告警详情
  getAlert: (params: any) => http.request('get', monitorApiMap.getAlert, { params }),
  
  // 创建告警
  createAlert: (data: any) => http.request('post', monitorApiMap.createAlert, { data }),
  
  // 更新告警
  updateAlert: (data: any) => http.request('put', monitorApiMap.updateAlert, { data }),
  
  // 删除告警
  deleteAlert: (params: any) => http.request('delete', monitorApiMap.deleteAlert, { params }),
  
  // 获取告警类型
  getAlertTypes: (params?: any) => http.request('get', monitorApiMap.getAlertTypes, { params })
}

// 监控仪表板相关API
export const dashboardApi = {
  // 获取仪表板统计信息
  getDashboardStats: (params?: any) => http.request('get', monitorApiMap.getDashboardStats, { params })
}

// 基础信息相关API
export const baseInfoApi = {
  // 获取基础信息列表
  getBaseInfoList: (params?: any) => http.request('get', monitorApiMap.getBaseInfoList, { params })
}

// 系统健康统计相关API
export const systemHealthStatsApi = {
  // 获取系统健康统计信息
  getSystemHealthStats: (params?: any) => http.request('get', monitorApiMap.getSystemHealthStats, { params })
}

// PushPlus配置相关API
export const pushPlusConfigApi = {
  // 获取PushPlus配置列表
  getPushPlusConfigs: (params?: any) => http.request('get', monitorApiMap.getPushPlusConfigs, { params }),
  
  // 获取单个PushPlus配置详情
  getPushPlusConfig: (params: any) => http.request('get', monitorApiMap.getPushPlusConfig, { params }),
  
  // 创建PushPlus配置
  createPushPlusConfig: (data: any) => http.request('post', monitorApiMap.createPushPlusConfig, { data }),
  
  // 更新PushPlus配置
  updatePushPlusConfig: (data: any) => http.request('put', monitorApiMap.updatePushPlusConfig, { data }),
  
  // 删除PushPlus配置
  deletePushPlusConfig: (params: any) => http.request('delete', monitorApiMap.deletePushPlusConfig, { params }),
  
  // 测试PushPlus配置
  testPushPlusConfig: (data: any) => http.request('post', monitorApiMap.testPushPlusConfig, { data })
}