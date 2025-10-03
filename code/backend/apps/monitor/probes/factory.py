from .base import BaseProbe
from .ping import PingProbe
from .port import PortProbe


def get_probe_instance(probe_method, params):
    """
    根据探活方式获取对应的探活实例
    """
    probe_mapping = {
        'ping': PingProbe,
        'port': PortProbe,
    }
    
    probe_class = probe_mapping.get(probe_method)
    if not probe_class:
        raise ValueError(f"Unsupported probe method: {probe_method}")
    
    return probe_class(params)