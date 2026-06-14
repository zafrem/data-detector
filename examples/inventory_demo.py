"""Demonstration of PII Resource Scanning and Inventory Generation."""

import os
import sqlite3
from pathlib import Path
from datadetector.cli import main
from click.testing import CliRunner

def setup_demo_db(db_path: str):
    """Create a sample database with PII for scanning."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT, phone TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'John Doe', 'john.doe@example.com', '010-1234-5678')")
    cursor.execute("INSERT INTO users VALUES (2, 'Jane Smith', 'jane@company.kr', '010-9876-5432')")
    
    cursor.execute("CREATE TABLE logs (id INTEGER, ip_address TEXT, message TEXT)")
    cursor.execute("INSERT INTO logs VALUES (1, '192.168.1.1', 'Login successful')")
    
    conn.commit()
    conn.close()

def run_demo():
    runner = CliRunner()
    db_path = "demo_pii.db"
    scan_file = "scan_result.json"
    report_file = "inventory_report.html"
    
    try:
        # 1. Setup sample data
        print(f"--- Setting up demo database: {db_path} ---")
        if os.path.exists(db_path):
            os.remove(db_path)
        setup_demo_db(db_path)
        
        # 2. Run scan via CLI
        print(f"\n--- Running PII scan on {db_path} ---")
        result = runner.invoke(main, [
            "resource", "scan",
            "--type", "database",
            "--uri", f"sqlite:///{db_path}",
            "--name", "demo-database",
            "--out", scan_file
        ])
        print(result.output)
        
        # 3. Generate inventory report via CLI
        print(f"\n--- Generating Inventory Report (HTML) ---")
        result = runner.invoke(main, [
            "resource", "inventory",
            "--in", scan_file,
            "--format", "html",
            "--out", report_file
        ])
        print(result.output)
        
        if os.path.exists(report_file):
            print(f"SUCCESS: Report generated at {os.getcwd()}/{report_file}")
            
    finally:
        # Cleanup
        for f in [db_path, scan_file]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    run_demo()
