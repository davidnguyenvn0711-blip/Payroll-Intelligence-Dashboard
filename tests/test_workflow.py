import json
from pathlib import Path
import pytest
from app.services.database import connect, set_period_status
from app.services.exporter import payroll_excel, payslip_pdf


def test_lock_and_critical_exception(tmp_path: Path):
    conn=connect(tmp_path/"test.db")
    conn.execute("INSERT INTO exceptions(period,code,severity,message) VALUES('2026-07','X','Nghiêm trọng','Lỗi')"); conn.commit()
    with pytest.raises(ValueError): set_period_status(conn,"2026-07","Đã phê duyệt","tester")
    conn.execute("UPDATE exceptions SET resolved=1"); conn.commit()
    set_period_status(conn,"2026-07","Đã khóa","tester")
    with pytest.raises(ValueError): set_period_status(conn,"2026-07","Bản nháp","tester")

def test_exports_are_nonempty():
    rows=[{"employee_id":"NV1","full_name":"Nguyễn An","gross_pay":10_000_000,"employee_insurance":1_000_000,"pit":0,"total_deductions":1_000_000,"net_pay":9_000_000,"employer_insurance":2_000_000,"total_employer_cost":12_000_000}]
    assert payroll_excel(rows)[:2]==b"PK"
    assert payslip_pdf(rows[0],"2026-07")[:4]==b"%PDF"

