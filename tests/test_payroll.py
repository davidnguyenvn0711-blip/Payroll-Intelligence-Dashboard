from datetime import date, time
from app.services.payroll import PayrollInput, calculate_payroll, hours_between, progressive_tax, rate_segments
from app.services.rules import effective_rules, load_config


CONFIG=load_config(); RULES=effective_rules(date(2026,7,1),CONFIG)

def test_regular_and_insurance_and_tax():
    r=calculate_payroll(PayrollInput("NV1",regular_hours=160,insurance_salary=8_000_000,dependents=0),100_000,RULES,CONFIG["tax_brackets"])
    assert r["regular_pay"]==16_000_000
    assert r["employee_insurance"]==840_000
    assert r["taxable_income"]==0
    assert r["net_pay"]==15_160_000
    assert r["employer_insurance"]==1_720_000

def test_overnight_shift():
    assert hours_between(date(2026,7,1),time(22),time(6),60)==7

def test_overtime_types_and_night():
    r=calculate_payroll(PayrollInput("NV1",ot_weekday_hours=2,ot_weekend_hours=2,ot_holiday_hours=2,night_hours=2,night_ot_hours=2,insured=False),100_000,RULES,CONFIG["tax_brackets"])
    assert r["ot_weekday_pay"]==300_000
    assert r["ot_weekend_pay"]==400_000
    assert r["ot_holiday_pay"]==600_000
    assert r["night_pay"]==60_000
    assert r["night_ot_pay"]==400_000

def test_paid_and_unpaid_leave():
    r=calculate_payroll(PayrollInput("NV1",paid_leave_hours=8,unpaid_leave_hours=4,insured=False),50_000,RULES,CONFIG["tax_brackets"])
    assert r["gross_pay"]==200_000

def test_dependents_and_progressive_tax():
    assert progressive_tax(10_000_000,CONFIG["tax_brackets"])==500_000
    assert progressive_tax(20_000_000,CONFIG["tax_brackets"])==1_500_000
    r=calculate_payroll(PayrollInput("NV1",regular_hours=400,dependents=2,insured=False),100_000,RULES,CONFIG["tax_brackets"])
    assert r["taxable_income"]==12_100_000

def test_rate_change_segments():
    history=[{"effective_from":"2026-01-01","hourly_rate":50_000},{"effective_from":"2026-07-16","hourly_rate":60_000}]
    seg=rate_segments(history,date(2026,7,1),date(2026,7,31))
    assert seg==[(date(2026,7,1),date(2026,7,15),50_000),(date(2026,7,16),date(2026,7,31),60_000)]

def test_approved_adjustments_and_rounding():
    r=calculate_payroll(PayrollInput("NV1",bonuses=123_456,additions=10_000,advances=20_000,deductions=5_000,insured=False),0,RULES,CONFIG["tax_brackets"])
    assert r["gross_pay"]==133_456
    assert r["net_pay"]==108_456

