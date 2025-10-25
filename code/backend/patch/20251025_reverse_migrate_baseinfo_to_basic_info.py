#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
反向数据迁移脚本：将 BaseInfo 模型的数据迁回到 Node.basic_info_list

用途：
- 将存储在 BaseInfo 模型中的数据迁回 Node.basic_info_list JSONField
- 用于回滚或备份目的
- 支持重复执行，已迁移的数据可能会被覆盖

使用方法：
1. 在项目根目录执行：
   cd /path/to/project/
   python scripts/reverse_migrate_baseinfo_to_basic_info_20250425.py

注意事项：
- 请在执行前备份数据库
- 确保 Django 环境已正确配置
- 此脚本会更新 Node.basic_info_list 字段，已存在的数据将被替换
"""

import os
import sys
import django
from django.db import transaction

# 设置 Django 环境
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print("工作目录:", WORKSPACE)
sys.path.append(WORKSPACE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.monitor.models import Node, BaseInfo


def reverse_migrate_baseinfo_to_basic_info():
    """
    将 BaseInfo 模型中的数据迁回到 Node.basic_info_list
    """
    print("开始执行反向数据迁移：将 BaseInfo 数据迁回到 basic_info_list")
    
    # 统计信息
    total_nodes = 0
    processed_nodes = 0
    total_baseinfo_processed = 0
    
    # 查询所有节点
    nodes = Node.objects.all()
    total_nodes = nodes.count()
    
    print(f"总共找到 {total_nodes} 个节点")
    
    for node in nodes:
        # 获取该节点的 BaseInfo 记录
        base_info_items = BaseInfo.objects.filter(node=node).order_by('create_time')
        
        if not base_info_items.exists():
            print(f"节点 {node.name} (UUID: {node.uuid}) 没有 BaseInfo 记录，跳过")
            continue
        
        print(f"处理节点 {node.name} (UUID: {node.uuid})，找到 {base_info_items.count()} 条 BaseInfo 记录")
        
        # 构建 basic_info_list
        basic_info_list = []
        for base_info in base_info_items:
            item = {
                'host': base_info.host,
            }
            if base_info.port is not None:
                item['port'] = base_info.port
            item['is_ping_disabled'] = base_info.is_ping_disabled
            basic_info_list.append(item)
            total_baseinfo_processed += 1
        
        # 更新节点的 basic_info_list
        with transaction.atomic():
            node.basic_info_list = basic_info_list
            node.save(update_fields=['basic_info_list'])
            print(f"  更新节点 {node.name} 的 basic_info_list，包含 {len(basic_info_list)} 条记录")
        
        processed_nodes += 1
    
    print("\n反向数据迁移完成！")
    print(f"总节点数: {total_nodes}")
    print(f"处理节点数: {processed_nodes}")
    print(f"处理 BaseInfo 记录数: {total_baseinfo_processed}")


def main():
    """
    主函数
    """
    try:
        reverse_migrate_baseinfo_to_basic_info()
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