# 💻 WinPerfAgent

**WinPerfAgent** is an open-source monitoring solution for Windows systems. It collects system performance data and sends it to a central Flask-based dashboard, storing it in PostgreSQL for real-time and historical analysis.

<img width="1982" height="1128" alt="image" src="https://github.com/user-attachments/assets/6d4f3bf2-27ff-4712-889c-af7302c163c0" />

---

## 🚀 Features

- ✅ Multi-client support
- ✅ Real-time monitoring (CPU, RAM, Disk, Network, Uptime)
- ✅ Intelligent recommendations system
- ✅ Tray application with GUI interface
- ✅ PostgreSQL-based historical database
- ✅ Modern, responsive dashboard (HTML + CSS + Chart.js)
- ✅ Easy deployment via Docker

---

## 📁 Project Structure

```
WinPerfAgent/
├── agent.py                # Tray agent for Windows
├── app.py                  # Flask server
├── db.py                   # PostgreSQL operations
├── monitor.py              # System metrics collection
├── recommender.py          # Recommendation engine
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── static/                 # CSS / JS assets
├── templates/              # HTML views
├── updates/                # (Optional) Update mechanism
├── VERSION
└── README.md
```

---

## ⚙️ Server Setup

### Option 1: 🐳 Docker (Recommended)

```bash
git clone https://github.com/samet-y/WinPerfAgentServer.git
cd WinPerfAgentServer
docker-compose up -d
```

- Access the dashboard via `http://localhost:5000`

---

### Option 2: Manual Setup (For Developers)

> 🧠 Requirements: Python 3.10+ and PostgreSQL 13+

```bash
# 1. Clone the repository
git clone https://github.com/samet-y/WinPerfAgentServer.git
cd WinPerfAgentServer

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install and configure PostgreSQL
sudo apt install postgresql
sudo -u postgres psql
```

In PostgreSQL shell:

```sql
CREATE DATABASE winperf;
CREATE USER admin WITH PASSWORD 'secret';
GRANT ALL PRIVILEGES ON DATABASE winperf TO admin;
```

Then create `.env` file:

```
DATABASE_URL=postgresql://admin:secret@localhost:5432/winperf
```

Initialize the database:

```bash
python db.py
```

Start the Flask server:

```bash
python app.py
```

---

## 🖥️ Windows Agent Setup

### Option 1: Run with Python

> Requires Python 3.10+

```bash
pip install -r requirements.txt
python agent.py
```

- Tray icon will appear
- Double-click to open GUI with system details

### Option 2: Build `.exe` Executable

```bash
pip install pyinstaller
pyinstaller agent.py --noconsole --onefile --name WinPerfAgent
```

- Run `dist/WinPerfAgent.exe`
- Optionally add shortcut to startup folder for auto-run

---

## 🔧 Agent Configuration (`agent_config.json`)

```json
{
  "dashboard_url": "http://10.0.0.10:5000/api/report",
  "report_interval": 10,
  "connection_timeout": 5
}
```

---

## 🧠 Recommendation Engine

Recommendations are automatically generated based on high CPU, RAM or Disk usage:

```text
High CPU usage detected (93%). Consider closing 'chrome.exe'.
```

---

## 🧪 Database Structure

- `reports` → all incoming agent reports
- `clients_current` → latest snapshot per client
- `cleanup_old_data()` → cleans up outdated logs

---

## 📡 API Endpoints

| Method | URL                            | Description                    |
|--------|--------------------------------|--------------------------------|
| POST   | `/api/report`                 | Agent sends system report      |
| GET    | `/api/clients`                | Returns all active clients     |
| GET    | `/api/reports`                | Returns full report history    |
| GET    | `/api/client/<hostname>`      | Returns data for one client    |
| GET    | `/api/health`                 | Server health check            |

---

## 📸 Screenshots

<img width="1982" height="1128" alt="image" src="https://github.com/user-attachments/assets/6d4f3bf2-27ff-4712-889c-af7302c163c0" />
<img width="1001" height="1194" alt="image" src="https://github.com/user-attachments/assets/7fef791e-761c-489c-a2b0-5a920ae27940" />
<img width="1619" height="1218" alt="image" src="https://github.com/user-attachments/assets/875fc554-0b3d-4481-81d9-71922baac904" />
<img width="692" height="627" alt="image" src="https://github.com/user-attachments/assets/a75b13b1-56d1-41b4-9501-8ae80939e2b1" />
<img width="691" height="629" alt="image" src="https://github.com/user-attachments/assets/929226bc-643c-4b6f-99dd-fdbc11d623b3" />


---

## 🧾 License

This project is licensed under the MIT License and can be freely used in commercial or personal projects.
