import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from app.services.importer import normalize_columns, read_authoritative_payroll, reconcile_employee_ids, validate_timesheet


def test_column_normalization_and_missing():
    df=normalize_columns(pd.DataFrame({"Mã nhân viên":["NV1"],"Ngày làm việc":["2026-07-01"],"Giờ vào":["08:00"],"Giờ ra":[None]}))
    errors=validate_timesheet(df,{"NV1"})
    assert df.columns.tolist()==["employee_id","work_date","check_in","check_out"]
    assert any(e["code"]=="MISSING_PUNCH" for e in errors)

def test_duplicate_unknown_and_unapproved_ot():
    df=pd.DataFrame([{"employee_id":"BAD","work_date":"2026-07-01","check_in":"08:00","check_out":"17:00","ot_weekday_hours":2,"ot_approved":False}]*2)
    codes=[e["code"] for e in validate_timesheet(df,{"NV1"})]
    assert "UNKNOWN_EMPLOYEE" in codes and "DUPLICATE" in codes and "OT_NOT_APPROVED" in codes


def test_authoritative_payroll_and_id_reconciliation():
    wb=Workbook(); ws=wb.active; ws.title="Sheet1"
    ws.append(["LƯƠNG THÁNG"]); ws.append([])
    ws.append(["ID","CTY","HỌ VÀ TÊN","CHỨC VỤ\n(P.BAN)","TỔNG\nLƯƠNG","LƯƠNG CƠ BẢN\n(ĐÓNG BH + TNCN)","TỔNG THƯỞNG", "KPI","DS","PHỤ CẤP",None,None,None,"BH CTY","BH NV","TỔNG BH"])
    ws.append([None]*9+["TIỀN ĂN","ĐIỆN THOẠI","XĂNG XE","CHUYÊN CẦN",.215,.105,None])
    ws.append([1,"HHP","NGUYỄN AN","SẢN XUẤT",10_000_000,6_000_000,2_000_000,1_000_000,1_000_000,500_000,200_000,300_000,100_000,1_290_000,630_000,1_920_000])
    output=BytesIO(); wb.save(output); output.seek(0)
    payroll=read_authoritative_payroll(output)
    timesheet=pd.DataFrame([{"employee_id":"1","full_name":"NGUYEN AN"}])
    assert payroll.iloc[0].gross_pay==10_000_000
    assert reconcile_employee_ids(timesheet,payroll)==[]
