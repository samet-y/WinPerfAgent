def get_recommendations(metrics, top_procs):
    recs = []

    if metrics['cpu'] > 85:
        top_cpu = top_procs[0] if top_procs else {"name": "unknown", "cpu": 0}
        recs.append(f"High CPU usage detected ({metrics['cpu']}%). Consider closing '{top_cpu['name']}' if not needed.")

    if metrics['ram'] > 85:
        recs.append(f"Memory usage is high ({metrics['ram']}%). Try restarting heavy applications.")

    if metrics['disk'] > 90:
        recs.append(f"Disk usage is very high ({metrics['disk']}%). Consider cleaning temporary files or uninstalling unused apps.")

    return recs
