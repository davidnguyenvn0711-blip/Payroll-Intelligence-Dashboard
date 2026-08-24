from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_DB = Path(__file__).parents[2] / "data" / "database" / "payroll.sqlite3"


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS employees (
 employee_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, company TEXT, department TEXT,
 job_title TEXT, employment_status TEXT NOT NULL DEFAULT 'Đang làm việc', start_date TEXT,
 end_date TEXT, standard_schedule TEXT, hours_per_day REAL DEFAULT 8,
 hours_per_week REAL DEFAULT 48, insurance_salary REAL DEFAULT 0,
 social_insurance INTEGER DEFAULT 0, health_insurance INTEGER DEFAULT 0,
 unemployment_insurance INTEGER DEFAULT 0, tax_id TEXT, tax_residency TEXT DEFAULT 'Cư trú',
 dependents INTEGER DEFAULT 0, bank_account TEXT, bank_name TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS salary_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT NOT NULL, hourly_rate REAL NOT NULL,
 effective_from TEXT NOT NULL, effective_to TEXT, created_at TEXT NOT NULL,
 UNIQUE(employee_id, effective_from), FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
CREATE TABLE IF NOT EXISTS payroll_periods (
 period TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'Bản nháp', locked INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, approved_by TEXT, approved_at TEXT, paid_at TEXT
);
CREATE TABLE IF NOT EXISTS adjustments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT NOT NULL, period TEXT NOT NULL,
 adjustment_type TEXT NOT NULL, amount REAL NOT NULL, reason TEXT NOT NULL, entered_by TEXT NOT NULL,
 entered_at TEXT NOT NULL, approval_status TEXT NOT NULL DEFAULT 'Chờ duyệt', approved_by TEXT,
 FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
CREATE TABLE IF NOT EXISTS exceptions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT NOT NULL, employee_id TEXT, code TEXT NOT NULL,
 severity TEXT NOT NULL, message TEXT NOT NULL, source_row INTEGER, resolved INTEGER DEFAULT 0,
 resolution_note TEXT, resolved_by TEXT, resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS payroll_results (
 period TEXT NOT NULL, employee_id TEXT NOT NULL, payload TEXT NOT NULL, calculated_at TEXT NOT NULL,
 PRIMARY KEY(period, employee_id), FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_time TEXT NOT NULL, actor TEXT NOT NULL,
 action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT, old_value TEXT, new_value TEXT
);
"""


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def log_event(conn, actor: str, action: str, entity_type: str, entity_id: str = "", old=None, new=None):
    conn.execute(
        "INSERT INTO audit_log VALUES(NULL,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), actor, action, entity_type, entity_id,
         json.dumps(old, ensure_ascii=False) if old is not None else None,
         json.dumps(new, ensure_ascii=False) if new is not None else None),
    )
    conn.commit()


def set_period_status(conn, period: str, new_status: str, actor: str, confirm_unlock: bool = False):
    allowed = ["Bản nháp", "Đang kiểm tra", "Chờ phê duyệt", "Đã phê duyệt", "Đã khóa", "Đã thanh toán"]
    if new_status not in allowed:
        raise ValueError("Trạng thái kỳ lương không hợp lệ")
    row = conn.execute("SELECT * FROM payroll_periods WHERE period=?", (period,)).fetchone()
    old_status = row["status"] if row else None
    if row and row["locked"] and new_status != "Đã khóa" and not confirm_unlock:
        raise ValueError("Kỳ lương đã khóa; cần xác nhận mở khóa rõ ràng")
    critical = conn.execute(
        "SELECT COUNT(*) FROM exceptions WHERE period=? AND severity='Nghiêm trọng' AND resolved=0", (period,)
    ).fetchone()[0]
    if new_status in {"Đã phê duyệt", "Đã khóa", "Đã thanh toán"} and critical:
        raise ValueError(f"Còn {critical} lỗi nghiêm trọng chưa xử lý")
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT OR IGNORE INTO payroll_periods(period,status,locked,created_at) VALUES(?,?,0,?)", (period,"Bản nháp",now))
    conn.execute("UPDATE payroll_periods SET status=?, locked=? WHERE period=?", (new_status, int(new_status in {"Đã khóa","Đã thanh toán"}), period))
    log_event(conn, actor, "Đổi trạng thái", "payroll_period", period, old_status, new_status)

