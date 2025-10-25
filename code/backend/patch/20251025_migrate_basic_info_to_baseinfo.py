#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将 Node.basic_info_list 的数据迁移到 BaseInfo 模型

用途：
- 将现有的存储在 Node.basic_info_list JSONField 中的数据迁移到新的 BaseInfo 模型
- 保持数据的完整性，避免重复记录
- 支持重复执行，已迁移的数据不会被重复处理

使用方法：
1. 在项目根目录执行：
   cd /path/to/project/
   python scripts/migrate_basic_info_to_baseinfo_20250425.py

注意事项：
- 请在执行前备份数据库
- 确保 Django 环境已正确配置
- 脚本支持重复执行，已处理过的节点不会被重复处理
"""

import os
import sys
import django
from django.db import transaction
import json

# 设置 Django 环境
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print("工作目录:", WORKSPACE)
sys.path.append(WORKSPACE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.monitor.models import Node, BaseInfo


def migrate_basic_info_to_baseinfo():
    """
    将 Node.basic_info_list 中的数据迁移到 BaseInfo 模型
    """
    print("开始执行数据迁移：将 basic_info_list 数据迁移到 BaseInfo 模型")
    
    # 统计信息
    total_nodes = 0
    migrated_nodes = 0
    skipped_nodes = 0  # 已有 BaseInfo 记录的节点将被跳过
    total_baseinfo_created = 0
    
    # 查询所有节点
    nodes = Node.objects.all()
    total_nodes = nodes.count()
    
    print(f"总共找到 {total_nodes} 个节点")
    
    for node in nodes:
        # 检查该节点是否已经有 BaseInfo 记录
        existing_baseinfo_count = BaseInfo.objects.filter(node=node).count()
        
        if existing_baseinfo_count > 0:
            print(f"跳过节点 {node.name} (UUID: {node.uuid})，已存在 {existing_baseinfo_count} 条 BaseInfo 记录")
            skipped_nodes += 1
            continue
        
        basic_info_list = node.basic_info_list
        if not basic_info_list or not isinstance(basic_info_list, list):
            print(f"节点 {node.name} (UUID: {node.uuid}) 没有 basic_info_list 数据或数据格式不正确，跳过")
            continue
        
        print(f"处理节点 {node.name} (UUID: {node.uuid})，包含 {len(basic_info_list)} 条 basic_info")
        
        # 用于防止重复记录的集合
        created_combinations = set()
        
        for basic_info in basic_info_list:
            if not isinstance(basic_info, dict):
                print(f"  跳过非字典格式的数据: {basic_info}")
                continue
            
            host = basic_info.get('host')
            if not host:
                print(f"  跳过缺少 host 的数据: {basic_info}")
                continue
            
            port = basic_info.get('port')
            is_ping_disabled = basic_info.get('is_ping_disabled', False)
            
            # 创建唯一标识符，用于防止重复
            combination_key = (host, port)
            if combination_key in created_combinations:
                print(f"  跳过重复的 host:port 组合 {host}:{port}")
                continue
            
            # 检查数据库中是否已存在相同的记录
            existing_baseinfo = BaseInfo.objects.filter(
                node=node,
                host=host,
                port=port
            ).first()
            
            if existing_baseinfo:
                print(f"  跳过已存在的 host:port 组合 {host}:{port}")
                continue
            
            # 创建 BaseInfo 记录
            with transaction.atomic():
                baseinfo = BaseInfo.objects.create(
                    node=node,
                    host=host,
                    port=port,
                    is_ping_disabled=is_ping_disabled
                )
                print(f"    创建 BaseInfo 记录: {host}:{port} (禁ping: {is_ping_disabled})")
                total_baseinfo_created += 1
                created_combinations.add(combination_key)
        
        migrated_nodes += 1
        
        # 提交事务
        transaction.commit()
    
    print("\n数据迁移完成！")
    print(f"总节点数: {total_nodes}")
    print(f"已迁移节点数: {migrated_nodes}")
    print(f"跳过节点数: {skipped_nodes}")
    print(f"创建 BaseInfo 记录数: {total_baseinfo_created}")


def main():
    """
    主函数
    """
    try:
        migrate_basic_info_to_baseinfo()
    except KeyboardInterrupt:
        print("\n用户取消了操作")
        sys.exit(1)
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()