from apps.monitor.models import Link, Node

def format_link_data(link: Link):
    """格式化链路数据"""
    res = {
        'uuid': str(link.uuid),
        'name': link.name
    }

    if link.is_del:
        res['name'] = link.name + '[已删除]'

    return res

def format_node_data(node: Node):
    """格式化节点数据"""
    res = {
        'uuid': str(node.uuid),
        'name': node.name,
        'link': format_link_data(node.link)
    }

    if node.is_del:
        res['name'] = node.name + '[已删除]'

    return res