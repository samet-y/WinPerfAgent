from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for
import time
import logging
from datetime import datetime
import os
from db import insert_report, get_all_reports, get_client_history, get_current_clients
from recommender import get_recommendations
from dotenv import load_dotenv

load_dotenv()
API_SECRET = os.getenv("API_SECRET_TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
clients = {}  # hostname -> latest data
REQUIRED_AGENT_VERSION = "1.0.1"  # En son ajan versiyonu

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/report", methods=["POST"])
def api_report():

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid authorization header"}), 401
    token = auth_header.split(" ")[1]
    if token != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        if not data or "hostname" not in data:
            logger.warning(f"Invalid data received: {data}")
            return jsonify({"error": "Invalid data - hostname required"}), 400

        data["last_seen"] = time.time()
        data["server_timestamp"] = datetime.now().isoformat()
        data["installed_programs"] = data.get("installed_programs", [])

        agent_version = data.get("agent_version", "0.0.0")
        data["status"] = "outdated" if agent_version < REQUIRED_AGENT_VERSION else "ok"

        clients[data["hostname"]] = data
        insert_report(data)

        if "cpu" in data and "memory" in data and "disk" in data:
            cpu_percent = data["cpu"].get("percent", 0) if isinstance(data["cpu"], dict) else data.get("cpu", 0)
            memory_percent = data["memory"].get("percent", 0) if isinstance(data["memory"], dict) else data.get("ram", 0)

            disk_percent = 0
            if isinstance(data.get("disk"), dict):
                disk_info = list(data["disk"].values())
                if disk_info:
                    disk_percent = disk_info[0].get("percent", 0)

            metrics = {
                "cpu": cpu_percent,
                "ram": memory_percent,
                "disk": disk_percent
            }

            top_processes = data.get("top_processes", [])
            recommendations = get_recommendations(metrics, top_processes)
            data["recommendations"] = recommendations

        logger.info(f"Report received from {data['hostname']}")
        return jsonify({
            "status": "ok",
            "timestamp": data["server_timestamp"],
            "agent_status": data["status"],
            "required_version": REQUIRED_AGENT_VERSION
        })

    except Exception as e:
        logger.error(f"Error processing report: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/reports")
def reports_page():
    return render_template("reports.html")

@app.route("/api/reports")
def api_reports():
    try:
        rows = get_all_reports()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error fetching reports: {str(e)}")
        return jsonify({"error": "Database fetch failed"}), 500

@app.route("/api/clients")
def api_clients():
    """Get current client status from database (persistent)"""
    try:
        rows = get_current_clients()
        return jsonify({client["hostname"]: client for client in rows})
    except Exception as e:
        logger.error(f"Failed to fetch current clients: {e}")
        return jsonify({})


@app.route("/api/client/<hostname>/history")
def api_client_history(hostname):
    try:
        history = get_client_history(hostname)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error fetching client history for {hostname}: {str(e)}")
        return jsonify({"error": "Failed to fetch client history"}), 500

@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_clients": len(clients),
        "uptime": time.time()
    })

@app.route("/updates/<path:filename>")
def download_update(filename):
    updates_dir = os.path.join(os.getcwd(), "updates")
    safe_path = os.path.abspath(os.path.join(updates_dir, filename))
    if not safe_path.startswith(os.path.abspath(updates_dir)):
        return jsonify({"error": "Unauthorized access"}), 403
    return send_from_directory(updates_dir, filename, as_attachment=True)

@app.errorhandler(404)
def redirect_to_dashboard(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found"}), 404
    return redirect(url_for("index"))

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting WinPerfAgent server...")
    app.run(host="0.0.0.0", port=5000, debug=True)
