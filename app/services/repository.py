from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)

from app.services.rules import effective_rules, load_config


ROOT = Path(__file__).parents[2]
LOCAL_DATABASE_URL = f"sqlite:///{ROOT / 'data' / 'database' / 'payroll.sqlite3'}"
metadata = MetaData()

users = Table(
    "app_users", metadata,
    Column("username", String(100), primary_key=True),
    Column("display_name", String(200), nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("role", String(30), nullable=False, default="viewer"),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, nullable=False),
)
employees = Table(
    "employee_master", metadata,
    Column("employee_id", String(50), primary_key=True),
    Column("full_name", String(250), nullable=False),
    Column("company", String(100)),
    Column("department", String(150)),
    Column("job_title", String(150)),
    Column("active", Boolean, nullable=False, default=True),
    Column("updated_at", DateTime, nullable=False),
)
templates = Table(
    "payroll_templates", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("employee_id", String(50), nullable=False),
    Column("effective_from", String(7), nullable=False),
    Column("effective_to", String(7)),
    Column("payload", Text, nullable=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, nullable=False),
    Column("created_by", String(100), nullable=False),
    UniqueConstraint("employee_id", "effective_from", name="uq_template_employee_effective"),
)
periods = Table(
    "monthly_periods", metadata,
    Column("period", String(7), primary_key=True),
    Column("status", String(40), nullable=False, default="Bản nháp"),
    Column("source_file", String(300)),
    Column("row_count", Integer, nullable=False, default=0),
    Column("employee_count", Integer, nullable=False, default=0),
    Column("exception_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("approved_by", String(100)),
    Column("approved_at", DateTime),
    Column("locked", Boolean, nullable=False, default=False),
)
attendance = Table(
    "monthly_attendance", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("period", String(7), nullable=False),
    Column("employee_id", String(50), nullable=False),
    Column("work_date", String(10)),
    Column("shift", String(200)),
    Column("attendance_status", String(80)),
    Column("check_in", String(30)),
    Column("check_out", String(30)),
    Column("tracked_minutes", Float, nullable=False, default=0),
    Column("needs_review", Boolean, nullable=False, default=False),
)
summaries = Table(
    "monthly_employee_summary", metadata,
    Column("period", String(7), primary_key=True),
    Column("employee_id", String(50), primary_key=True),
    Column("full_name", String(250), nullable=False),
    Column("company", String(100)),
    Column("department", String(150)),
    Column("shift_count", Integer, nullable=False, default=0),
    Column("normal_count", Integer, nullable=False, default=0),
    Column("late_count", Integer, nullable=False, default=0),
    Column("early_count", Integer, nullable=False, default=0),
    Column("absent_count", Integer, nullable=False, default=0),
    Column("tracked_minutes", Float, nullable=False, default=0),
    Column("review_count", Integer, nullable=False, default=0),
    Column("payroll_payload", Text, nullable=False),
)
exceptions = Table(
    "monthly_exceptions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("period", String(7), nullable=False),
    Column("employee_id", String(50)),
    Column("code", String(80), nullable=False),
    Column("severity", String(30), nullable=False),
    Column("message", Text, nullable=False),
    Column("resolved", Boolean, nullable=False, default=False),
    Column("resolution_note", Text),
    Column("resolved_by", String(100)),
    Column("resolved_at", DateTime),
)
audit = Table(
    "app_audit_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_time", DateTime, nullable=False),
    Column("actor", String(100), nullable=False),
    Column("action", String(120), nullable=False),
    Column("entity_type", String(80), nullable=False),
    Column("entity_id", String(100)),
    Column("details", Text),
)


class PayrollRepository:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL") or LOCAL_DATABASE_URL
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgresql://") and "+psycopg" not in self.database_url:
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("sqlite"):
            (ROOT / "data" / "database").mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        metadata.create_all(self.engine)

    def has_users(self) -> bool:
        with self.engine.connect() as conn:
            return bool(conn.execute(select(func.count()).select_from(users)).scalar_one())

    def get_user(self, username: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(users).where(users.c.username == username, users.c.active.is_(True))).mappings().first()
            return dict(row) if row else None

    def save_user(self, username: str, display_name: str, password_hash: str, role: str, actor: str = "Thiết lập"):
        now = datetime.now()
        with self.engine.begin() as conn:
            exists = conn.execute(select(users.c.username).where(users.c.username == username)).first()
            values = {"display_name": display_name, "password_hash": password_hash, "role": role, "active": True}
            if exists:
                conn.execute(update(users).where(users.c.username == username).values(**values))
            else:
                conn.execute(insert(users).values(username=username, created_at=now, **values))
            self._audit(conn, actor, "Lưu tài khoản", "user", username, {"role": role})

    def user_frame(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            rows = conn.execute(select(users.c.username, users.c.display_name, users.c.role, users.c.active, users.c.created_at)).mappings().all()
        return pd.DataFrame(rows)

    def save_payroll_template(self, frame: pd.DataFrame, effective_from: str, actor: str):
        now = datetime.now()
        with self.engine.begin() as conn:
            for record in frame.to_dict("records"):
                employee_id = str(record["employee_id"])
                emp_values = {
                    "full_name": record["full_name"], "company": record.get("company"),
                    "department": record.get("department"), "job_title": record.get("department"),
                    "active": True, "updated_at": now,
                }
                exists = conn.execute(select(employees.c.employee_id).where(employees.c.employee_id == employee_id)).first()
                if exists:
                    conn.execute(update(employees).where(employees.c.employee_id == employee_id).values(**emp_values))
                else:
                    conn.execute(insert(employees).values(employee_id=employee_id, **emp_values))
                conn.execute(update(templates).where(templates.c.employee_id == employee_id, templates.c.active.is_(True)).values(active=False, effective_to=effective_from))
                payload = {key: self._json_value(value) for key, value in record.items()}
                existing_template = conn.execute(select(templates.c.id).where(templates.c.employee_id == employee_id, templates.c.effective_from == effective_from)).first()
                values = {"payload": json.dumps(payload, ensure_ascii=False), "active": True, "effective_to": None, "created_at": now, "created_by": actor}
                if existing_template:
                    conn.execute(update(templates).where(templates.c.id == existing_template[0]).values(**values))
                else:
                    conn.execute(insert(templates).values(employee_id=employee_id, effective_from=effective_from, **values))
            self._audit(conn, actor, "Cập nhật phân bổ lương chuẩn", "template", effective_from, {"employees": len(frame)})

    def active_templates(self, period: str) -> pd.DataFrame:
        statement = select(templates.c.employee_id, templates.c.payload).where(
            templates.c.effective_from <= period,
            (templates.c.effective_to.is_(None)) | (templates.c.effective_to > period),
        )
        with self.engine.connect() as conn:
            rows = conn.execute(statement).mappings().all()
        return pd.DataFrame([json.loads(row["payload"]) for row in rows])

    def template_history(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            rows = conn.execute(select(templates).order_by(templates.c.effective_from.desc(), templates.c.employee_id)).mappings().all()
        result = []
        for row in rows:
            payload = json.loads(row["payload"])
            result.append({"Mã nhân viên": row["employee_id"], "Họ và tên": payload.get("full_name"), "Hiệu lực từ": row["effective_from"], "Hiệu lực đến": row["effective_to"], "Đang áp dụng": row["active"], "Người cập nhật": row["created_by"]})
        return pd.DataFrame(result)

    def save_month(self, period: str, timesheet: pd.DataFrame, issues: list[dict], filename: str, actor: str):
        template = self.active_templates(period)
        if template.empty:
            raise ValueError("Chưa có phân bổ lương chuẩn có hiệu lực cho kỳ này")
        critical = [item for item in issues if item["severity"] == "Nghiêm trọng"]
        if critical:
            raise ValueError("Không thể lưu khi còn lỗi ID hoặc tên nghiêm trọng")
        now = datetime.now()
        period_date = datetime.strptime(f"{period}-01", "%Y-%m-%d").date()
        rules = effective_rules(period_date, load_config())
        standard_hours = float(rules["standard_hours_per_day"]["value"])
        standard_month_hours = float(rules["standard_hours_per_month"]["value"])
        overtime_multiplier = float(rules["overtime_multiplier_business"]["value"])
        overtime_basis = str(rules["overtime_salary_basis"]["value"])
        work_schedule = {
            "morning_start": self._minutes_from_rule(rules["work_morning_start"]["value"]),
            "morning_end": self._minutes_from_rule(rules["work_morning_end"]["value"]),
            "afternoon_start": self._minutes_from_rule(rules["work_afternoon_start"]["value"]),
            "afternoon_end": self._minutes_from_rule(rules["work_afternoon_end"]["value"]),
        }
        name_lookup = template.set_index("employee_id").to_dict("index")
        normalized = timesheet.copy()
        normalized["employee_id"] = normalized.employee_id.astype(str).str.strip()
        standard_workdays = round(standard_month_hours / standard_hours)
        with self.engine.begin() as conn:
            old = conn.execute(select(periods.c.locked).where(periods.c.period == period)).first()
            if old and old[0]:
                raise ValueError("Kỳ lương đã khóa; không thể nhập lại chấm công")
            conn.execute(delete(attendance).where(attendance.c.period == period))
            conn.execute(delete(summaries).where(summaries.c.period == period))
            conn.execute(delete(exceptions).where(exceptions.c.period == period, exceptions.c.resolved.is_(False)))
            attendance_rows = []
            for _, row in normalized.iterrows():
                tracked_value = pd.to_numeric(row.get("tracked_minutes", 0), errors="coerce")
                tracked_minutes = 0.0 if pd.isna(tracked_value) else float(tracked_value)
                attendance_rows.append({
                    "period": period, "employee_id": row["employee_id"],
                    "work_date": self._date_value(row.get("work_date")), "shift": self._text(row.get("ca")),
                    "attendance_status": self._text(row.get("attendance_status")),
                    "check_in": self._text(row.get("check_in")), "check_out": self._text(row.get("check_out")),
                    "tracked_minutes": tracked_minutes,
                    "needs_review": self._needs_review(row),
                })
            if attendance_rows:
                conn.execute(insert(attendance), attendance_rows)
            for issue in issues:
                conn.execute(insert(exceptions).values(period=period, employee_id=issue.get("employee_id"), code=issue["code"], severity=issue["severity"], message=issue["message"], resolved=False))
            for employee_id, info in name_lookup.items():
                rows = normalized[normalized.employee_id == employee_id]
                statuses = rows.get("attendance_status", pd.Series(dtype=str)).fillna("").astype(str).str.lower()
                payload = {key: self._json_value(value) for key, value in info.items()}
                time_metrics = self._employee_time_metrics(rows, work_schedule)
                salary_basis_value = pd.to_numeric(info.get(overtime_basis, 0), errors="coerce")
                salary_basis = 0.0 if pd.isna(salary_basis_value) else float(salary_basis_value)
                base_hourly_rate = salary_basis / standard_month_hours if standard_month_hours else 0
                overtime_hourly_rate = base_hourly_rate * overtime_multiplier
                regular_pay = round(time_metrics["regular_minutes"] / 60 * base_hourly_rate)
                overtime_pay = round(time_metrics["overtime_minutes"] / 60 * overtime_hourly_rate)
                gross_value = pd.to_numeric(info.get("gross_pay", 0), errors="coerce")
                gross_pay = 0.0 if pd.isna(gross_value) else float(gross_value)
                final_payable = regular_pay + overtime_pay
                payload.update({
                    "standard_hours_per_day": standard_hours,
                    "standard_workdays": standard_workdays,
                    "standard_month_hours": standard_month_hours,
                    "regular_hours": time_metrics["regular_hours"],
                    "overtime_hours": time_metrics["overtime_hours"],
                    "regular_minutes": round(time_metrics["regular_minutes"], 2),
                    "overtime_minutes": round(time_metrics["overtime_minutes"], 2),
                    "late_minutes": time_metrics["late_minutes"],
                    "early_minutes": time_metrics["early_minutes"],
                    "base_hourly_rate": round(base_hourly_rate),
                    "regular_pay": regular_pay,
                    "overtime_multiplier": overtime_multiplier,
                    "overtime_hourly_rate": round(overtime_hourly_rate),
                    "overtime_pay": overtime_pay,
                    "final_payable": final_payable,
                })
                conn.execute(insert(summaries).values(
                    period=period, employee_id=employee_id, full_name=info.get("full_name", ""),
                    company=info.get("company"), department=info.get("department"), shift_count=len(rows),
                    normal_count=int(statuses.eq("bình thường").sum()),
                    late_count=time_metrics["late_count"],
                    early_count=time_metrics["early_count"],
                    absent_count=int(statuses.str.contains("vắng mặt").sum()),
                    tracked_minutes=float(pd.to_numeric(rows.get("tracked_minutes", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
                    review_count=int(rows.apply(self._needs_review, axis=1).sum()) if not rows.empty else 0,
                    payroll_payload=json.dumps(payload, ensure_ascii=False),
                ))
            values = {"status": "Đang kiểm tra", "source_file": filename, "row_count": len(normalized), "employee_count": len(template), "exception_count": len(issues), "updated_at": now, "locked": False}
            exists = conn.execute(select(periods.c.period).where(periods.c.period == period)).first()
            if exists:
                conn.execute(update(periods).where(periods.c.period == period).values(**values))
            else:
                conn.execute(insert(periods).values(period=period, created_at=now, **values))
            self._audit(conn, actor, "Nhập chấm công tháng", "period", period, {"file": filename, "rows": len(normalized), "issues": len(issues)})

    def period_frame(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            rows = conn.execute(select(periods).order_by(periods.c.period.desc())).mappings().all()
        return pd.DataFrame(rows)

    def summary_frame(self, period: str | None = None) -> pd.DataFrame:
        statement = select(summaries)
        if period:
            statement = statement.where(summaries.c.period == period)
        with self.engine.connect() as conn:
            rows = conn.execute(statement.order_by(summaries.c.period.desc(), summaries.c.employee_id)).mappings().all()
        result = []
        for row in rows:
            payload = json.loads(row["payroll_payload"])
            result.append({**dict(row), **payload})
        return pd.DataFrame(result)

    def exception_frame(self, period: str) -> pd.DataFrame:
        with self.engine.connect() as conn:
            rows = conn.execute(select(exceptions).where(exceptions.c.period == period).order_by(exceptions.c.resolved, exceptions.c.severity, exceptions.c.id)).mappings().all()
        return pd.DataFrame(rows)

    def resolve_exception(self, exception_id: int, note: str, actor: str):
        with self.engine.begin() as conn:
            conn.execute(update(exceptions).where(exceptions.c.id == exception_id).values(resolved=True, resolution_note=note, resolved_by=actor, resolved_at=datetime.now()))
            self._audit(conn, actor, "Xử lý ngoại lệ", "exception", str(exception_id), {"note": note})

    def set_status(self, period: str, status: str, actor: str):
        allowed = ["Bản nháp", "Đang kiểm tra", "Chờ phê duyệt", "Đã phê duyệt", "Đã khóa", "Đã thanh toán"]
        if status not in allowed:
            raise ValueError("Trạng thái không hợp lệ")
        with self.engine.begin() as conn:
            row = conn.execute(select(periods).where(periods.c.period == period)).mappings().first()
            if not row:
                raise ValueError("Kỳ lương chưa có dữ liệu")
            unresolved = conn.execute(select(func.count()).select_from(exceptions).where(exceptions.c.period == period, exceptions.c.severity == "Nghiêm trọng", exceptions.c.resolved.is_(False))).scalar_one()
            if status in {"Đã phê duyệt", "Đã khóa", "Đã thanh toán"} and unresolved:
                raise ValueError(f"Còn {unresolved} lỗi nghiêm trọng chưa xử lý")
            values: dict[str, Any] = {"status": status, "updated_at": datetime.now(), "locked": status in {"Đã khóa", "Đã thanh toán"}}
            if status in {"Đã phê duyệt", "Đã khóa"}:
                values.update(approved_by=actor, approved_at=datetime.now())
            conn.execute(update(periods).where(periods.c.period == period).values(**values))
            self._audit(conn, actor, "Đổi trạng thái", "period", period, {"from": row["status"], "to": status})

    def audit_frame(self, limit: int = 500) -> pd.DataFrame:
        with self.engine.connect() as conn:
            rows = conn.execute(select(audit).order_by(audit.c.id.desc()).limit(limit)).mappings().all()
        return pd.DataFrame(rows)

    @staticmethod
    def _audit(conn, actor, action, entity_type, entity_id, details):
        conn.execute(insert(audit).values(event_time=datetime.now(), actor=actor, action=action, entity_type=entity_type, entity_id=entity_id, details=json.dumps(details, ensure_ascii=False)))

    @staticmethod
    def _json_value(value):
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return value

    @staticmethod
    def _date_value(value):
        if value is None or pd.isna(value):
            return None
        return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)[:10]

    @staticmethod
    def _text(value):
        if value is None or pd.isna(value):
            return None
        return str(value)

    @staticmethod
    def _needs_review(row):
        explicit = str(row.get("needs_review", "")).strip().lower()
        status = str(row.get("attendance_status", "")).strip().lower()
        return explicit not in {"", "nan", "none"} or status not in {"bình thường", "binh thuong"}

    @classmethod
    def _employee_time_metrics(cls, rows: pd.DataFrame, schedule: dict[str, float]) -> dict:
        if rows.empty:
            return {"regular_hours": 0.0, "overtime_hours": 0.0, "regular_minutes": 0.0, "overtime_minutes": 0.0, "late_count": 0, "late_minutes": 0, "early_count": 0, "early_minutes": 0}
        daily = rows.copy()
        daily["_date_key"] = daily.get("work_date", pd.Series(index=daily.index, data="Không rõ")).astype(str)
        regular_minutes = 0.0
        overtime_minutes = 0.0
        late_count = 0
        late_minutes = 0.0
        early_count = 0
        early_minutes = 0.0
        for _, day_rows in daily.groupby("_date_key"):
            punches = []
            for _, row in day_rows.iterrows():
                check_in = cls._minutes_of_day(row.get("check_in"))
                check_out = cls._minutes_of_day(row.get("check_out"))
                if check_in is None or check_out is None or check_out < check_in:
                    continue
                punches.append((check_in, check_out))
                regular_minutes += cls._overlap_minutes(check_in, check_out, schedule["morning_start"], schedule["morning_end"])
                regular_minutes += cls._overlap_minutes(check_in, check_out, schedule["afternoon_start"], schedule["afternoon_end"])
                overtime_minutes += max(0.0, check_out - max(check_in, schedule["afternoon_end"]))
            if not punches:
                continue
            morning = [(start, end) for start, end in punches if start < schedule["morning_end"]]
            afternoon = [(start, end) for start, end in punches if end > schedule["afternoon_start"]]
            if morning:
                morning_in = min(start for start, _ in morning)
                morning_out = max(end for _, end in morning)
                if morning_in > schedule["morning_start"]:
                    late_count += 1
                    late_minutes += morning_in - schedule["morning_start"]
                if morning_out < schedule["morning_end"]:
                    early_count += 1
                    early_minutes += schedule["morning_end"] - morning_out
            if afternoon:
                afternoon_in = min(start for start, _ in afternoon)
                afternoon_out = max(end for _, end in afternoon)
                if afternoon_in > schedule["afternoon_start"]:
                    late_count += 1
                    late_minutes += afternoon_in - schedule["afternoon_start"]
                if afternoon_out < schedule["afternoon_end"]:
                    early_count += 1
                    early_minutes += schedule["afternoon_end"] - afternoon_out
        return {
            "regular_hours": round(float(regular_minutes) / 60, 2),
            "overtime_hours": round(float(overtime_minutes) / 60, 2),
            "regular_minutes": float(regular_minutes),
            "overtime_minutes": float(overtime_minutes),
            "late_count": late_count,
            "late_minutes": round(late_minutes),
            "early_count": early_count,
            "early_minutes": round(early_minutes),
        }

    @staticmethod
    def _overlap_minutes(start: float, end: float, window_start: float, window_end: float) -> float:
        return max(0.0, min(end, window_end) - max(start, window_start))

    @staticmethod
    def _minutes_from_rule(value: str) -> float:
        hour, minute = str(value).split(":", 1)
        return int(hour) * 60 + int(minute)

    @staticmethod
    def _minutes_of_day(value):
        if value is None or pd.isna(value):
            return None
        if hasattr(value, "hour"):
            return value.hour * 60 + value.minute + value.second / 60
        try:
            parsed = pd.to_datetime(str(value))
            return parsed.hour * 60 + parsed.minute + parsed.second / 60
        except (TypeError, ValueError):
            return None
