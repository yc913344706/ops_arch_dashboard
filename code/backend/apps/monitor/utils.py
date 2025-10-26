from apps.monitor.models import Node


def format_node_data(node: Node):
    """格式化节点数据"""
    res = {
        'uuid': str(node.uuid),
        'name': node.name,
        'link': {
            'uuid': str(node.link.uuid),
            'name': node.link.name
        }
    }

    if node.is_del:
        res['name'] = node.name + '[已删除]'

    return res