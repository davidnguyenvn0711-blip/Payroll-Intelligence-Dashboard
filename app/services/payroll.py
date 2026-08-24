from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class PayrollInput:
    employee_id: str
    regular_hours: float = 0
    ot_weekday_hours: float = 0
    ot_weekend_hours: float = 0
    ot_holiday_hours: float = 0
    night_hours: float = 0
    night_ot_hours: float = 0
    paid_leave_hours: float = 0
    unpaid_leave_hours: float = 0
    allowances: float = 0
    bonuses: float = 0
    additions: float = 0
    advances: float = 0
    deductions: float = 0
    insurance_salary: float = 0
    dependents: int = 0
    tax_resident: bool = True
    insured: bool = True


def hours_between(work_date: date, check_in: time, check_out: time, break_minutes: float = 0) -> float:
    start = datetime.combine(work_date, check_in)
    end = datetime.combine(work_date, check_out)
    if end < start:
        end += timedelta(days=1)
    return max(0.0, (end - start).total_seconds() / 3600 - break_minutes / 60)


def progressive_tax(taxable: float, brackets: list[dict]) -> float:
    taxable = max(0.0, taxable)
    tax = 0.0
    for bracket in brackets:
        lower, upper, rate = bracket["from"], bracket["to"], bracket["rate"]
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower if upper is not None else taxable - lower) * rate
        if upper is None or taxable <= upper:
            break
    return tax


def rate_segments(history: list[dict], period_start: date, period_end: date) -> list[tuple[date, date, float]]:
    ordered = sorted(history, key=lambda x: x["effective_from"])
    segments = []
    for i, item in enumerate(ordered):
        start = max(period_start, date.fromisoformat(item["effective_from"]))
        explicit_end = date.fromisoformat(item["effective_to"]) if item.get("effective_to") else period_end
        next_start = date.fromisoformat(ordered[i + 1]["effective_from"]) - timedelta(days=1) if i + 1 < len(ordered) else period_end
        end = min(period_end, explicit_end, next_start)
        if start <= end:
            segments.append((start, end, float(item["hourly_rate"])))
    return segments


def calculate_payroll(data: PayrollInput, hourly_rate: float, rules: dict[str, dict], tax_brackets: list[dict]) -> dict:
    rv = lambda name: float(rules[name]["value"])
    regular_pay = (data.regular_hours + data.paid_leave_hours) * hourly_rate
    ot_weekday_pay = data.ot_weekday_hours * hourly_rate * rv("ot_weekday")
    ot_weekend_pay = data.ot_weekend_hours * hourly_rate * rv("ot_weekend")
    ot_holiday_pay = data.ot_holiday_hours * hourly_rate * rv("ot_holiday")
    night_pay = data.night_hours * hourly_rate * rv("night_premium")
    night_ot_pay = data.night_ot_hours * hourly_rate * (rv("ot_weekday") + rv("night_premium") + 0.2)
    unpaid_leave = data.unpaid_leave_hours * hourly_rate
    gross = regular_pay + ot_weekday_pay + ot_weekend_pay + ot_holiday_pay + night_pay + night_ot_pay + data.allowances + data.bonuses + data.additions - unpaid_leave
    employee_insurance = data.insurance_salary * rv("employee_insurance") if data.insured else 0
    employer_insurance = data.insurance_salary * rv("employer_insurance") if data.insured else 0
    taxable = gross - employee_insurance - rv("personal_deduction") - data.dependents * rv("dependent_deduction")
    pit = progressive_tax(taxable, tax_brackets) if data.tax_resident else max(0, gross) * 0.2
    total_deductions = employee_insurance + pit + data.advances + data.deductions
    net = gross - total_deductions
    total_cost = gross + employer_insurance
    rounding = Decimal(str(rv("rounding")))
    def rounded(value):
        return float((Decimal(str(value)) / rounding).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * rounding)
    result = {**asdict(data), "hourly_rate": hourly_rate, "regular_pay": regular_pay,
              "ot_weekday_pay": ot_weekday_pay, "ot_weekend_pay": ot_weekend_pay,
              "ot_holiday_pay": ot_holiday_pay, "night_pay": night_pay, "night_ot_pay": night_ot_pay,
              "unpaid_leave_deduction": unpaid_leave, "gross_pay": gross,
              "employee_insurance": employee_insurance, "taxable_income": max(0, taxable), "pit": pit,
              "total_deductions": total_deductions, "net_pay": net,
              "employer_insurance": employer_insurance, "total_employer_cost": total_cost}
    return {key: rounded(value) if isinstance(value, float) and key != "hourly_rate" else value for key, value in result.items()}

