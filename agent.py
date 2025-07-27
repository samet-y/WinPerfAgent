import psutil
import time
import requests
import socket
import platform
import threading
import sys
import json
import logging
import shutil
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image, ImageDraw
from typing import Dict, Any, Optional
import queue
import os

def get_agent_version():
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Normal script olarak çalışıyor
            base_path = os.path.abspath(os.path.dirname(__file__))

        version_path = os.path.join(base_path, "VERSION")
        with open(version_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    except Exception as e:
        import logging
        logging.warning(f"VERSION dosyası okunamadı: {e}")
        return "0.0.0"


# Configuration
CONFIG_FILE = "agent_config.json"
LOG_FILE = "agent.log"

DEFAULT_CONFIG = {
    "dashboard_url": "http://10.0.0.10:5000/api/report",
    "enable_auto_update": False,
    "auth_token": "secret_api_key",
    "agent_version": get_agent_version(),
    "update_url": "http://10.0.0.10:5000/updates/agent-latest.exe",
    "report_interval": 10,
    "connection_timeout": 5,
    "retry_attempts": 3,
    "retry_delay": 2,
    "log_level": "INFO",
    "max_log_size": 10485760,  # 10MB
    "enable_notifications": True
}

class Config:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        try:
            if Path(CONFIG_FILE).exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                return config
        except Exception as e:
            logging.error(f"Config load error: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Config save error: {e}")
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save_config()

class SystemMonitor:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        self.last_data = {}
        self.connection_status = {"connected": False, "last_success": None, "error_count": 0}
        self.status_queue = queue.Queue()
        self.running = True
        
    def setup_logging(self):
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # Rotate log if too large
        try:
            if Path(LOG_FILE).exists() and Path(LOG_FILE).stat().st_size > self.config.get('max_log_size', 10485760):
                Path(LOG_FILE).rename(f"{LOG_FILE}.old")
        except Exception as e:
            logging.error(f"Log rotation hatası: {e}")
    
    def get_network_interfaces(self) -> Dict[str, Dict[str, int]]:
        """Get network statistics for all interfaces"""
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
            logging.error(f"Network interface data get error: {e}")
        return interfaces
    
    def get_disk_info(self) -> Dict[str, Dict[str, Any]]:
        """Get disk usage for all mounted drives"""
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
            logging.error(f"Disk bilgisi alınamadı: {e}")
        return disks
    
    def check_for_updates(self, server_response: dict):
        if not self.config.get("enable_auto_update", False):
            logging.info("🔕 Auto Update Disabled.")
            return
        
        if server_response.get("agent_status") == "outdated":
            logging.warning("🟡 New Version Available! Update Starting...")
            update_url = self.config.get("update_url")
            if not update_url:
                logging.error("Update URL not defined!")
                return
        
            try:
                response = requests.get(update_url, stream=True, timeout=20)
                if response.status_code != 200:
                    logging.error(f"Updated not complete: HTTP {response.status_code}")
                    return
                
                exe_path = Path(__file__).resolve()
                new_file = exe_path.parent / "agent-latest.exe"
                
                with open(new_file, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)

                logging.info(f"Update Downloaded: {new_file}")

                subprocess.Popen([str(new_file)], shell=True)
                logging.info("🚀 New Agent Started. Current agent closing...")
                self.stop()
                os.kill(os.getpid(), signal.SIGTERM)
                sys.exit(0)

            except Exception as e:
                logging.error(f"Update Failed: {e}")


    def get_system_uptime(self) -> str:
        """Get system uptime"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            return str(uptime).split('.')[0]  # Remove microseconds
        except Exception as e:
            logging.error(f"Uptime information error: {e}")
            return "Unknown"
        

    def get_top_processes(self, limit=5):
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

    def get_installed_programs(self):
        try:
            si = None
            if platform.system() == "Windows":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            combined = []
            for reg_path in [
                "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*"
            ]:
                result = subprocess.run(
                    ['powershell', '-Command',
                    f"Get-ItemProperty {reg_path} | "
                    "Where-Object { $_.DisplayName -ne $null } | "
                    "Select-Object DisplayName, DisplayVersion | ConvertTo-Json"],
                    capture_output=True, text=True, timeout=15,
                    startupinfo=si
                )
                if result.returncode != 0 or not result.stdout.strip():
                    continue
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    combined.extend(data)
                except json.JSONDecodeError:
                    continue

            programs = []
            for entry in combined:
                name = (entry.get("DisplayName") or "").strip()
                version = (entry.get("DisplayVersion") or "Unknown").strip()
                if name:
                    programs.append({"name": name, "version": version})

            return programs
        except Exception as e:
            logging.error(f"Installed programs info error: {e}")
            return []

    
    def get_metrics(self) -> Dict[str, Any]:
        try:
            # Basic system info
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
            except Exception:
                hostname = platform.node()
                ip = "127.0.0.1"
            
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Network info
            net_io = psutil.net_io_counters()
            network_interfaces = self.get_network_interfaces()
            
            # Disk info
            disk_info = self.get_disk_info()
            
            
            # Process count
            process_count = len(psutil.pids())
            
            self.last_data = {
                "timestamp": datetime.now().isoformat(),
                "hostname": hostname,
                "ip": ip,
                "os": f"{platform.system()} {platform.release()}",
                "architecture": platform.architecture()[0],
                "uptime": self.get_system_uptime(),
                
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
                    "interfaces": network_interfaces
                },
                
                "disk": disk_info,
                "installed_programs": self.get_installed_programs(),
                "agent_version": self.config.get("agent_version", "1.0.0"),
                "top_processes": self.get_top_processes(),
                "status": "ok",
                "process_count": process_count
            }
            
            return self.last_data
            
        except Exception as e:
            logging.error(f"Metrics info error: {e}")
            return {}
    
    def send_data_with_retry(self, data: Dict[str, Any]) -> bool:
        """Send data with retry mechanism"""
        retry_attempts = self.config.get('retry_attempts', 3)
        retry_delay = self.config.get('retry_delay', 2)
        
        for attempt in range(retry_attempts):
            try:
                response = requests.post(
                    self.config.get('dashboard_url'),
                    json=data,
                    timeout=self.config.get('connection_timeout', 5),
                    headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.config.get('auth_token', '')}"
                    }
                )
                
                if response.ok:
                    self.connection_status.update({
                        "connected": True,
                        "last_success": datetime.now(),
                        "error_count": 0
                    })
                    logging.info(f"✅ [{data.get('hostname', 'Unknown')}] Report sent succesfully!")

                    try:
                        self.check_for_updates(response.json())
                    except Exception as e:
                        logging.error(f"Update check error: {e}")
                    return True
                else:
                    logging.warning(f"⚠️ HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logging.error(f"❌ Timeout (Try {attempt + 1}/{retry_attempts})")
            except requests.exceptions.ConnectionError:
                logging.error(f"❌ Connection Error (Try {attempt + 1}/{retry_attempts})")
            except Exception as e:
                logging.error(f"❌ Error: {e} (Try {attempt + 1}/{retry_attempts})")
            
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
        
        self.connection_status.update({
            "connected": False,
            "error_count": self.connection_status.get("error_count", 0) + 1
        })
        
        return False
    
    def send_loop(self):
        """Main sending loop"""
        logging.info("Monitoring agent started")
        
        while self.running:
            try:
                data = self.get_metrics()
                if data:
                    success = self.send_data_with_retry(data)
                    self.status_queue.put(("status_update", success))
                else:
                    logging.error("Metrics Error")
                    
            except Exception as e:
                logging.error(f"Send loop error: {e}")
            
            time.sleep(self.config.get('report_interval', 10))
    
    def stop(self):
        """Stop the monitoring agent"""
        self.running = False
        logging.info("Monitoring agent stopping...")

class AgentGUI:
    def __init__(self, monitor: SystemMonitor):
        self.monitor = monitor
        self.icon = None
        
    def show_connection_details(self):
        """Show detailed connection and system information"""
        root = tk.Tk()
        root.title("System Monitor - Advanced")
        root.geometry("600x500")
        root.resizable(True, True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(root)
        
        # System Info Tab
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="System Information")
        
        # Connection Info Tab
        connection_frame = ttk.Frame(notebook)
        notebook.add(connection_frame, text="Connection Status")
        
        # Logs Tab
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="Logs")
        
        # Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.populate_system_tab(system_frame)
        self.populate_connection_tab(connection_frame)
        self.populate_logs_tab(logs_frame)
        self.populate_settings_tab(settings_frame, root)
        
        root.mainloop()
    
    def populate_system_tab(self, frame):
        """Populate system information tab"""
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        if self.monitor.last_data:
            self.display_system_info(scrollable_frame)
        else:
            tk.Label(scrollable_frame, text="No data available", font=("Arial", 12)).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def display_system_info(self, frame):
        """Display detailed system information"""
        data = self.monitor.last_data
        
        # Basic Info
        basic_frame = ttk.LabelFrame(frame, text="General Information", padding=10)
        basic_frame.pack(fill="x", pady=5)
        
        basic_info = [
            ("Hostname", data.get("hostname", "N/A")),
            ("IP Adress", data.get("ip", "N/A")),
            ("Operating System", data.get("os", "N/A")),
            ("Architecture", data.get("architecture", "N/A")),
            ("Uptime", data.get("uptime", "N/A")),
            ("Last Update", data.get("timestamp", "N/A")),
        ]
        
        for label, value in basic_info:
            row = tk.Frame(basic_frame)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 9, "bold"), width=15, anchor="w").pack(side="left")
            tk.Label(row, text=str(value), font=("Arial", 9), anchor="w").pack(side="left")
        
        # CPU Info
        if "cpu" in data:
            cpu_frame = ttk.LabelFrame(frame, text="CPU Information", padding=10)
            cpu_frame.pack(fill="x", pady=5)
            
            cpu_data = data["cpu"]
            cpu_info = [
                ("Kullanım", f"{cpu_data.get('percent', 0):.1f}%"),
                ("Çekirdek Sayısı", str(cpu_data.get('count', 'N/A'))),
            ]
            
            if cpu_data.get('frequency'):
                freq = cpu_data['frequency']
                cpu_info.append(("Frequency", f"{freq.get('current', 0):.0f} MHz"))
            
            for label, value in cpu_info:
                row = tk.Frame(cpu_frame)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{label}:", font=("Arial", 9, "bold"), width=15, anchor="w").pack(side="left")
                tk.Label(row, text=value, font=("Arial", 9), anchor="w").pack(side="left")
        
        # Memory Info
        if "memory" in data:
            mem_frame = ttk.LabelFrame(frame, text="RAM Information", padding=10)
            mem_frame.pack(fill="x", pady=5)
            
            mem_data = data["memory"]
            mem_info = [
                ("Usage", f"{mem_data.get('percent', 0):.1f}%"),
                ("Sum", f"{mem_data.get('total', 0) / (1024**3):.1f} GB"),
                ("Using", f"{mem_data.get('used', 0) / (1024**3):.1f} GB"),
                ("Free", f"{mem_data.get('free', 0) / (1024**3):.1f} GB"),
            ]
            
            for label, value in mem_info:
                row = tk.Frame(mem_frame)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{label}:", font=("Arial", 9, "bold"), width=15, anchor="w").pack(side="left")
                tk.Label(row, text=value, font=("Arial", 9), anchor="w").pack(side="left")
    
    def populate_connection_tab(self, frame):
        """Populate connection status tab"""
        status_frame = ttk.LabelFrame(frame, text="Connection Information", padding=10)
        status_frame.pack(fill="x", pady=10)
        
        status = self.monitor.connection_status
        
        status_info = [
            ("Dashboard URL", self.monitor.config.get('dashboard_url', 'N/A')),
            ("Status", "🟢 Connected" if status.get('connected') else "🔴 No Connection"),
            ("Last Success Data", 
             status.get('last_success').strftime('%Y-%m-%d %H:%M:%S') if status.get('last_success') else 'No Information'),
            ("Error Count", str(status.get('error_count', 0))),
            ("Report Interval", f"{self.monitor.config.get('report_interval', 10)} second"),
        ]
        
        for label, value in status_info:
            row = tk.Frame(status_frame)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), width=20, anchor="w").pack(side="left")
            tk.Label(row, text=str(value), font=("Arial", 10), anchor="w").pack(side="left")
    
    def populate_logs_tab(self, frame):
        """Populate logs tab"""
        log_text = scrolledtext.ScrolledText(frame, height=20, width=70)
        log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        try:
            if Path(LOG_FILE).exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = f.read()
                    log_text.insert('1.0', logs)
                    log_text.see('end')  # Scroll to bottom
            else:
                log_text.insert('1.0', "Log file error.")
        except Exception as e:
            log_text.insert('1.0', f"Log file error: {e}")
        
        log_text.config(state='disabled')
    
    def populate_settings_tab(self, frame, root):
        """Populate settings tab"""
        settings_frame = ttk.LabelFrame(frame, text="Setting", padding=10)
        settings_frame.pack(fill="x", pady=10)
        
        # Dashboard URL
        url_frame = tk.Frame(settings_frame)
        url_frame.pack(fill="x", pady=5)
        tk.Label(url_frame, text="Dashboard URL:", width=20, anchor="w").pack(side="left")
        url_var = tk.StringVar(value=self.monitor.config.get('dashboard_url', ''))
        url_entry = tk.Entry(url_frame, textvariable=url_var, width=40)
        url_entry.pack(side="left", padx=5)
        
        # Report Interval
        interval_frame = tk.Frame(settings_frame)
        interval_frame.pack(fill="x", pady=5)
        tk.Label(interval_frame, text="Report Interval (s):", width=20, anchor="w").pack(side="left")
        interval_var = tk.StringVar(value=str(self.monitor.config.get('report_interval', 10)))
        interval_entry = tk.Entry(interval_frame, textvariable=interval_var, width=10)
        interval_entry.pack(side="left", padx=5)
        
        # Timeout
        timeout_frame = tk.Frame(settings_frame)
        timeout_frame.pack(fill="x", pady=5)
        tk.Label(timeout_frame, text="Timeout (s):", width=20, anchor="w").pack(side="left")
        timeout_var = tk.StringVar(value=str(self.monitor.config.get('connection_timeout', 5)))
        timeout_entry = tk.Entry(timeout_frame, textvariable=timeout_var, width=10)
        timeout_entry.pack(side="left", padx=5)
        
        # Save button
        def save_settings():
            try:
                self.monitor.config.set('dashboard_url', url_var.get())
                self.monitor.config.set('report_interval', int(interval_var.get()))
                self.monitor.config.set('connection_timeout', int(timeout_var.get()))
                messagebox.showinfo("Success", "Setting Saved. Restart the application.")
            except ValueError:
                messagebox.showerror("Error", "Integer error!")
        
        tk.Button(settings_frame, text="Save", command=save_settings).pack(pady=10)
    
    def create_tray_icon(self):
        """Create system tray icon"""
        img = Image.new("RGB", (64, 64), (255, 255, 255))
        d = ImageDraw.Draw(img)
        
        # Draw a simple monitoring icon
        d.ellipse((8, 8, 56, 56), fill=(0, 100, 200))
        d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
        d.rectangle((28, 20, 36, 44), fill=(0, 100, 200))
        d.rectangle((20, 28, 44, 36), fill=(0, 100, 200))
        
        return img
    
    def quit_application(self, icon, item):
        """Quit the application"""
        self.monitor.stop()
        icon.stop()
        sys.exit(0)
    
    def run_tray(self):
        """Run system tray application"""
        menu = Menu(
            Item("🔍 Details", lambda icon, item: threading.Thread(target=self.show_connection_details, daemon=True).start()),
            Item("📊 Open Dashboard", self.open_dashboard),
            Menu.SEPARATOR,
            Item("❌ Çıkış", self.quit_application)
        )
        
        self.icon = Icon("SystemMonitorAgent", icon=self.create_tray_icon(), menu=menu)
        self.icon.run()
    
    def open_dashboard(self, icon, item):
        """Open dashboard in browser"""
        import webbrowser
        dashboard_url = self.monitor.config.get('dashboard_url', '').replace('/api/report', '')
        if dashboard_url:
            webbrowser.open(dashboard_url)

def main():
    """Main application entry point"""
    try:
        monitor = SystemMonitor()
        gui = AgentGUI(monitor)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor.send_loop, daemon=True)
        monitor_thread.start()
        
        # Start GUI
        gui.run_tray()
        
    except KeyboardInterrupt:
        logging.info("Application stopped by user")
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()