import psutil
import socket
import platform
from datetime import datetime


def get_system_metrics():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except Exception:
        hostname = platform.node()
        ip = "127.0.0.1"

    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    net_io = psutil.net_io_counters()
    disks = get_disk_info()
    process_count = len(psutil.pids())

    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": hostname,
        "ip": ip,
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.architecture()[0],
        "cpu": {
            "percent": cpu_percent,
            "count": cpu_count,
            "frequency": cpu_freq._asdict() if cpu_freq else None
        },
        "memory": {
            "percent": memory.percent,
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free
        },
        "swap": {
            "percent": swap.percent,
            "total": swap.total,
            "used": swap.used,
            "free": swap.free
        },
        "network": {
            "total_sent": net_io.bytes_sent,
            "total_recv": net_io.bytes_recv,
            "interfaces": get_network_interfaces()
        },
        "disk": disks,
        "process_count": process_count,
        "top_processes": get_top_processes()
    }


def get_network_interfaces():
    interfaces = {}
    try:
        for interface, stats in psutil.net_io_counters(pernic=True).items():
            interfaces[interface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
    except Exception as e:
        pass
    return interfaces


def get_disk_info():
    disks = {}
    try:
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": (usage.used / usage.total) * 100
                }
            except (PermissionError, OSError):
                continue
    except Exception as e:
        pass
    return disks


def get_top_processes(limit=5):
    processes = []
    for p in psutil.process_iter(['name', 'cpu_percent']):
        try:
            name = p.info['name'] or "Unknown"
            cpu = p.info['cpu_percent']
            if name.lower() != "system idle process":
                processes.append({'name': name, 'cpu': cpu})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    sorted_procs = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:limit]
    return sorted_procs


if __name__ == '__main__':
    import json
    import time

    while True:
        metrics = get_system_metrics()
        print(json.dumps(metrics, indent=2))
        time.sleep(10)
