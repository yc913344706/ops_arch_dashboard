# 运维架构可视化与监控平台

## 项目简介

这是一个用于可视化和监控运维架构的平台，支持创建和管理复杂的系统架构图，监控节点健康状态，并提供直观的图形化界面来展示系统组件之间的关系。

## 系统架构

### 后端架构
- **框架**: Django 5.2
- **数据库**: MySQL
- **缓存**: Redis
- **消息队列**: Celery
- **权限控制**: 自定义RBAC权限系统

### 前端架构
- **框架**: Vue 3 + TypeScript
- **UI库**: Element Plus
- **可视化**: G6图可视化库
- **构建工具**: Vite

### 核心功能模块

#### 1. 架构图管理 (Link)
- 创建和管理多个架构图
- 支持不同类型的架构图（如K8s集群、网络拓扑等）
- 每个架构图包含多个节点和连接关系

#### 2. 节点管理 (Node)
- 节点基础信息管理（名称、主机、端口等）
- 支持多个主机/端口配置
- 节点在架构图中的位置管理
- 节点健康状态监控

#### 3. 连接管理 (NodeConnection)
- 定义节点间的连接关系
- 支持方向性连接（上/下/左/右）
- 多对多连接支持

#### 4. 健康监控 (NodeHealth)
- 定期探测节点健康状态
- 支持Ping探测和端口探测
- 记录健康状态历史

#### 5. 系统配置 (AppSetting)
- 存储系统配置参数
- 探活配置管理

## 使用指南

### 1. 架构图操作
1. 选择或创建架构图
2. 在画布上点击节点可选中
3. 点击空白区域取消选中

### 2. 节点操作
1. 点击"新建节点"按钮创建新节点（居中显示）
2. 选中节点后可通过操作面板：
   - 在上/下/左/右方向创建新节点
   - 编辑节点信息（名称、主机、端口等）
   - 管理节点连接关系

### 3. 连接管理
1. 选中节点后可在操作面板管理连接
2. 添加新连接需要指定方向和目标节点
3. 可删除现有连接

### 4. 健康监控
1. 系统自动定期探测节点健康状态
2. 健康状态通过节点颜色显示（绿色=健康，橙色=异常）
3. 可在节点详情中查看健康状态详情

## API接口

### 架构图相关
- `GET /api/v1/monitor/links/` - 获取架构图列表
- `POST /api/v1/monitor/links/` - 创建架构图
- `GET /api/v1/monitor/links/{id}/` - 获取单个架构图
- `PUT /api/v1/monitor/links/{id}/` - 更新架构图
- `DELETE /api/v1/monitor/links/{id}/` - 删除架构图
- `GET /api/v1/monitor/links/{id}/topology/` - 获取架构图拓扑数据

### 节点相关
- `GET /api/v1/monitor/nodes/` - 获取节点列表
- `POST /api/v1/monitor/nodes/` - 创建节点
- `GET /api/v1/monitor/nodes/{id}/` - 获取单个节点
- `PUT /api/v1/monitor/nodes/{id}/` - 更新节点
- `DELETE /api/v1/monitor/nodes/{id}/` - 删除节点
- `GET /api/v1/monitor/nodes/{id}/health/` - 获取节点健康状态

### 连接相关
- `GET /api/v1/monitor/connections/` - 获取连接列表
- `POST /api/v1/monitor/connections/` - 创建连接
- `GET /api/v1/monitor/connections/{id}/` - 获取单个连接
- `PUT /api/v1/monitor/connections/{id}/` - 更新连接
- `DELETE /api/v1/monitor/connections/{id}/` - 删除连接

## 部署说明

### 环境要求
- Docker Engine 18.06.0+
- Docker Compose 3.7+

### 启动服务
```bash
docker-compose -f docker-compose.dev.yaml up -d
```

### 访问地址
http://localhost:8080/

### 默认账户
- 账号: admin
- 密码: Admin@123

## 开发说明

### 前端开发
```bash
cd code/frontend
pnpm install
pnpm dev
```

### 后端开发
```bash
cd code/backend
python manage.py runserver
```

### 数据库迁移
```bash
cd code/backend
python manage.py makemigrations
python manage.py migrate
```