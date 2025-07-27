import psycopg2
import psycopg2.extras
import os
import json
import logging
from urllib.parse import urlparse
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

def get_connection():
    """Get database connection with proper error handling"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://admin:secret@winperf-db:5432/winperf")
        parsed = urlparse(db_url)

        return psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def init_database():
    """Initialize database tables"""
    create_tables_sql = """
    -- Main reports table
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        hostname VARCHAR(255) NOT NULL,
        ip_address INET,
        os_info TEXT,
        architecture VARCHAR(50),
        cpu_data JSONB,
        memory_data JSONB,
        disk_data JSONB,
        network_data JSONB,
        process_count INTEGER,
        top_processes JSONB,
        recommendations JSONB,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        raw_data JSONB
    );

    -- Index for faster queries
    CREATE INDEX IF NOT EXISTS idx_reports_hostname ON reports(hostname);
    CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON reports(timestamp);
    CREATE INDEX IF NOT EXISTS idx_reports_hostname_timestamp ON reports(hostname, timestamp);

    -- Clients summary table for current status
    CREATE TABLE IF NOT EXISTS clients_current (
        hostname VARCHAR(255) PRIMARY KEY,
        ip_address INET,
        os_info TEXT,
        architecture VARCHAR(50),
        last_cpu_percent DECIMAL(5,2),
        last_memory_percent DECIMAL(5,2),
        last_disk_percent DECIMAL(5,2),
        process_count INTEGER,
        last_seen TIMESTAMP WITH TIME ZONE,
        status VARCHAR(20) DEFAULT 'offline',
        raw_data JSONB
    );
    """
    
    try:
        with get_db_cursor() as cur:
            cur.execute(create_tables_sql)
            logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def insert_report(data):
    """Insert a new system report"""
    try:
        with get_db_cursor() as cur:
            # Extract data with proper error handling
            hostname = data.get("hostname")
            ip_address = data.get("ip")
            os_info = data.get("os")
            architecture = data.get("architecture")
            
            
            # Handle CPU data
            cpu_data = data.get("cpu", {})
            cpu_percent = cpu_data.get("percent", 0) if isinstance(cpu_data, dict) else cpu_data
            
            # Handle memory data
            memory_data = data.get("memory", {})
            memory_percent = memory_data.get("percent", 0) if isinstance(memory_data, dict) else data.get("ram", 0)
            
            # Handle disk data
            disk_data = data.get("disk", {})
            disk_percent = 0
            if isinstance(disk_data, dict) and disk_data:
                # Get the first disk's usage percentage
                first_disk = list(disk_data.values())[0]
                disk_percent = first_disk.get("percent", 0) if isinstance(first_disk, dict) else 0
            
            # Insert into reports table
            cur.execute("""
                INSERT INTO reports (
                    hostname, ip_address, os_info, architecture,
                    cpu_data, memory_data, disk_data, network_data,
                    process_count, top_processes, recommendations, installed_programs, 
                    last_cpu_percent, last_memory_percent, last_disk_percent, 
                    raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                hostname, ip_address, os_info, architecture,
                json.dumps(cpu_data), json.dumps(memory_data), json.dumps(disk_data),  
                json.dumps(data.get("network", {})),
                data.get("process_count"), 
                json.dumps(data.get("top_processes", [])),
                json.dumps(data.get("recommendations", [])), 
                json.dumps(data.get("installed_programs", [])), 
                cpu_percent, memory_percent, disk_percent,
                json.dumps(data)
            ))
            
            # Update current status table
            cur.execute("""
                INSERT INTO clients_current (
                    hostname, ip_address, os_info, architecture,
                    last_cpu_percent, last_memory_percent, last_disk_percent,
                    process_count, last_seen, status, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'online', %s)
                ON CONFLICT (hostname) DO UPDATE SET
                    ip_address = EXCLUDED.ip_address,
                    os_info = EXCLUDED.os_info,
                    architecture = EXCLUDED.architecture,
                    last_cpu_percent = EXCLUDED.last_cpu_percent,
                    last_memory_percent = EXCLUDED.last_memory_percent,
                    last_disk_percent = EXCLUDED.last_disk_percent,
                    process_count = EXCLUDED.process_count,
                    last_seen = NOW(),
                    status = 'online',
                    raw_data = EXCLUDED.raw_data
            """, (
                hostname, ip_address, os_info, architecture,
                cpu_percent, memory_percent, disk_percent,
                data.get("process_count"), json.dumps(data)
            ))
            
    except Exception as e:
        logger.error(f"Failed to insert report for {data.get('hostname', 'unknown')}: {e}")
        raise

def get_all_reports(limit=100):
    """Get recent reports from all clients"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    hostname,
                    ip_address,
                    os_info,
                    cpu_data,
                    memory_data,
                    disk_data,
                    process_count,
                    timestamp,
                    raw_data
                FROM reports
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()
            result = []

            for row in rows:
                cpu_data = row["cpu_data"] or {}
                memory_data = row["memory_data"] or {}
                disk_data = row["disk_data"] or {}

                result.append({
                    "hostname": row["hostname"],
                    "ip_address": str(row["ip_address"]) if row["ip_address"] else None,
                    "os_info": row["os_info"],
                    "cpu_percent": float(cpu_data.get("percent", 0)),
                    "memory_percent": float(memory_data.get("percent", 0)),
                    "disk_percent": parse_disk_percent(disk_data),
                    "process_count": row["process_count"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None
                })

            return result

    except Exception as e:
        logger.error(f"Failed to fetch reports: {e}")
        raise


    except Exception as e:
        logger.error(f"Failed to fetch reports: {e}")
        raise

def parse_disk_percent(disk_data: dict) -> float:
    try:
        return max(
            volume.get("percent", 0)
            for volume in disk_data.values()
            if isinstance(volume, dict)
        )
    except Exception:
        return 0.0

def get_client_history(hostname, hours=24):
    """Get historical data for a specific client"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    (cpu_data->>'percent')::decimal as cpu_percent,
                    (memory_data->>'percent')::decimal as memory_percent,
                    timestamp
                FROM reports 
                WHERE hostname = %s 
                    AND timestamp > NOW() - INTERVAL '%s hours'
                ORDER BY timestamp ASC
            """, (hostname, hours))
            
            rows = cur.fetchall()
            return [
                {
                    "cpu_percent": float(row["cpu_percent"]) if row["cpu_percent"] else 0,
                    "memory_percent": float(row["memory_percent"]) if row["memory_percent"] else 0,
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in rows
            ]
            
    except Exception as e:
        logger.error(f"Failed to fetch history for {hostname}: {e}")
        raise

def get_current_clients():
    """Get current status of all clients"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT * FROM clients_current
                ORDER BY last_seen DESC
            """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)

                # last_seen epoch'a dönüştür
                if isinstance(row_dict.get("last_seen"), datetime):
                    row_dict["last_seen"] = int(row_dict["last_seen"].timestamp())

                # raw_data içindeki bilgileri aç
                raw_data = row_dict.get("raw_data", {})
                if isinstance(raw_data, str):
                    try:
                        raw_data = json.loads(raw_data)
                    except Exception:
                        raw_data = {}

                for key in [
                    "cpu", "memory", "disk", "network", "top_processes", 
                    "recommendations", "installed_programs", "hostname", "ip", "os", "architecture"
                ]:
                    if key in raw_data:
                        row_dict[key] = raw_data[key]

                result.append(row_dict)
            return result
    except Exception as e:
        logger.error(f"Failed to fetch current clients: {e}")
        raise


def cleanup_old_data(days=30):
    """Clean up old data to prevent database bloat"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                DELETE FROM reports 
                WHERE timestamp < NOW() - INTERVAL '%s days'
            """, (days,))
            
            deleted_count = cur.rowcount
            logger.info(f"Cleaned up {deleted_count} old reports")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        raise

# Initialize database on module import
if __name__ == "__main__":
    init_database()