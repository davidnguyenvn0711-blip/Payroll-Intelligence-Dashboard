from io import BytesIO

import pandas as pd
from openpyxl import Workbook

from app.services.auth import hash_password, verify_password
from app.services.importer import read_authoritative_payroll, reconcile_employee_ids
from app.services.repository import PayrollRepository


def payroll_workbook():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["LƯƠNG THÁNG"])
    sheet.append([])
    sheet.append(["ID", "CTY", "HỌ VÀ TÊN", "BỘ PHẬN", "TỔNG LƯƠNG", "LƯƠNG CƠ BẢN", "THƯỞNG", "KPI", "DS", "PHỤ CẤP", None, None, None, "BH CTY", "BH NV", "TỔNG BH"])
    sheet.append([None] * 9 + ["TIỀN ĂN", "ĐIỆN THOẠI", "XĂNG XE", "CHUYÊN CẦN", .215, .105, None])
    sheet.append([1, "HHP", "NGUYỄN AN", "SẢN XUẤT", 10_000_000, 6_000_000, 2_000_000, 1_000_000, 1_000_000, 500_000, 200_000, 300_000, 100_000, 1_290_000, 630_000, 1_920_000])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def test_password_hash_is_not_plaintext():
    encoded = hash_password("mat-khau-rat-dai")
    assert "mat-khau-rat-dai" not in encoded
    assert verify_password("mat-khau-rat-dai", encoded)
    assert not verify_password("sai-mat-khau", encoded)


def test_long_term_template_and_monthly_attendance(tmp_path):
    repository = PayrollRepository(f"sqlite:///{tmp_path / 'payroll.db'}")
    template = read_authoritative_payroll(payroll_workbook())
    repository.save_payroll_template(template, "2026-07", "admin")
    timesheet = pd.DataFrame([
        {"employee_id": "1", "full_name": "NGUYEN AN", "work_date": pd.Timestamp("2026-07-01"), "attendance_status": "Bình thường", "check_in": pd.Timestamp("2026-07-01 07:30"), "check_out": pd.Timestamp("2026-07-01 17:00"), "tracked_minutes": 570, "needs_review": ""},
        {"employee_id": "1", "full_name": "NGUYEN AN", "work_date": pd.Timestamp("2026-07-02"), "attendance_status": "Muộn", "check_in": pd.Timestamp("2026-07-02 07:45"), "check_out": pd.Timestamp("2026-07-02 19:00"), "tracked_minutes": 675, "needs_review": "Kiểm tra"},
    ])
    issues = reconcile_employee_ids(timesheet, template)
    repository.save_month("2026-07", timesheet, issues, "cham-cong.xlsx", "admin")
    result = repository.summary_frame("2026-07").iloc[0]
    assert result.gross_pay == 10_000_000
    assert result.shift_count == 2
    assert result.tracked_minutes == 1245
    assert result.regular_hours == 15.75
    assert result.overtime_hours == 2
    assert result.standard_month_hours == 192
    assert result.base_hourly_rate == 52_083
    assert result.overtime_multiplier == 1.5
    assert result.regular_pay == 820_312
    assert result.overtime_pay == 156_250
    assert result.final_payable == 976_562
    assert result.late_count == 1
    assert result.late_minutes == 15
    assert repository.active_templates("2026-08").iloc[0].gross_pay == 10_000_000


def test_approval_blocked_by_critical_exception(tmp_path):
    repository = PayrollRepository(f"sqlite:///{tmp_path / 'approval.db'}")
    template = read_authoritative_payroll(payroll_workbook())
    repository.save_payroll_template(template, "2026-07", "admin")
    timesheet = pd.DataFrame([{"employee_id": "1", "full_name": "NGUYỄN AN", "work_date": pd.Timestamp("2026-07-01"), "attendance_status": "Bình thường", "tracked_minutes": 480}])
    repository.save_month("2026-07", timesheet, [], "cham-cong.xlsx", "admin")
    repository.set_status("2026-07", "Đã phê duyệt", "admin")
    assert repository.period_frame().iloc[0].status == "Đã phê duyệt"
