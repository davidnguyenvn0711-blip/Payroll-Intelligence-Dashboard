from __future__ import annotations

import base64
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.services.auth_en import hash_password, logout, require_authentication
from app.services.exporter_en import payroll_excel, payslip_pdf
from app.services.importer import read_authoritative_payroll, read_timesheet, reconcile_employee_ids
from app.services.repository import PayrollRepository


STATUS_ORDER = ["Bản nháp", "Đang kiểm tra", "Chờ phê duyệt", "Đã phê duyệt", "Đã khóa", "Đã thanh toán"]
STATUS_LABELS = {"Bản nháp": "Draft", "Đang kiểm tra": "Under review", "Chờ phê duyệt": "Pending approval", "Đã phê duyệt": "Approved", "Đã khóa": "Locked", "Đã thanh toán": "Paid"}
ADMIN_PAGES = ["Monthly Attendance", "Review & Approval", "Salary Allocation", "System Administration"]
PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}
ROOT = Path(__file__).parents[1]
HERO_ASSET = ROOT / "app" / "assets" / "payroll-operations-hero.png"


def main():
    st.set_page_config(page_title="Payroll Intelligence", page_icon="₫", layout="wide", initial_sidebar_state="expanded")
    apply_styles()
    repository = build_repository()
    user = require_authentication(repository)
    page, selected_period = sidebar(repository, user)
    render_page(repository, user, page, selected_period)


@st.cache_resource
def build_repository():
    database_url = None
    try:
        database_url = st.secrets.get("DATABASE_URL")
    except (FileNotFoundError, KeyError):
        pass
    return PayrollRepository(database_url)


def apply_styles():
    hero_uri = image_data_uri(HERO_ASSET)
    css = """
        <style>
        :root {--ink:#20231f;--muted:#6b7168;--line:#dce1d7;--green:#405f4a;--lime:#b8d94f;--amber:#d2a642;--paper:#ffffff;--canvas:#eef1ec;}
        .stApp {background:var(--canvas);color:var(--ink)}
        [data-testid="stHeader"] {background:transparent}
        [data-testid="stSidebar"] {background:#20231f;color:#f8faf5;border-right:1px solid #343831}
        [data-testid="stSidebar"] * {color:#f8fafc}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {color:#aeb5aa}
        [data-testid="stSidebar"] [role="radiogroup"] {gap:.18rem}
        [data-testid="stSidebar"] [role="radiogroup"] label {padding:.55rem .7rem;border-radius:8px;margin:.04rem 0;border:1px solid transparent;transition:background .16s ease,border-color .16s ease}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#2e322c;border-color:#41463e}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:var(--lime);border-color:var(--lime)}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {color:#1d211c!important;font-weight:750}
        [data-testid="stMetric"] {position:relative;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:1.05rem 1.1rem;min-height:116px;box-shadow:0 8px 24px rgba(37,45,35,.055);overflow:hidden}
        [data-testid="stMetric"]:before {content:"";position:absolute;left:0;top:0;width:5px;height:100%;background:var(--lime)}
        [data-testid="stMetricLabel"] {color:var(--muted);font-size:.81rem;font-weight:700;text-transform:uppercase}
        [data-testid="stMetricValue"] {color:var(--ink);font-size:1.48rem;font-weight:780}
        [data-testid="stMetricDelta"] {font-size:.72rem}
        [data-testid="stFileUploaderDropzone"] {background:#fbfcfa;border:1px dashed #9aa496;border-radius:8px;min-height:132px}
        [data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:8px;overflow:hidden;box-shadow:0 8px 24px rgba(37,45,35,.04)}
        [data-testid="stForm"] {background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:1.1rem;box-shadow:0 10px 30px rgba(37,45,35,.05)}
        [data-testid="stPlotlyChart"] {background:var(--paper);border:1px solid var(--line);border-radius:8px;overflow:hidden;box-shadow:0 10px 30px rgba(37,45,35,.05)}
        .block-container {max-width:1480px;padding-top:1.15rem;padding-bottom:4rem}
        h1,h2,h3 {letter-spacing:0!important;color:var(--ink)}
        h1 {font-size:2rem!important;margin-bottom:.15rem!important}
        h2 {font-size:1.28rem!important;margin-top:.8rem!important}
        h3 {font-size:1rem!important}
        .page-kicker {font-size:.72rem;text-transform:uppercase;color:var(--green);font-weight:850;margin-bottom:.3rem}
        .page-subtitle {color:var(--muted);margin:.15rem 0 1.25rem}
        .section-label {font-size:.75rem;color:#555d52;font-weight:850;margin:1.15rem 0 .55rem;text-transform:uppercase}
        .status-pill {display:inline-flex;align-items:center;padding:.27rem .62rem;border-radius:999px;background:#dfeeb4;color:#33451e;font-size:.75rem;font-weight:800}
        .notice-band {background:#fff8e7;border-left:4px solid var(--amber);padding:.85rem 1rem;border-radius:6px;color:#634b15;margin:.8rem 0 1rem}
        .schedule-band {display:flex;align-items:center;justify-content:space-between;gap:1rem;background:#20231f;border:1px solid #32372f;padding:.82rem 1rem;margin:.95rem 0 1.35rem;color:#e9ede5;font-size:.84rem;border-radius:8px;box-shadow:0 10px 28px rgba(31,35,29,.12)}
        .schedule-band strong {color:var(--lime)}
        .schedule-step {white-space:nowrap}
        .dashboard-hero {min-height:270px;background-size:cover;background-position:center 48%;border:1px solid #d6dbd0;border-radius:8px;padding:2.25rem 2.4rem;margin:.2rem 0 1.15rem;box-shadow:0 18px 44px rgba(38,46,34,.1);display:flex;align-items:center;overflow:hidden}
        .hero-copy {width:48%;max-width:570px}
        .hero-eyebrow {font-size:.7rem;font-weight:900;text-transform:uppercase;color:#4b6045;margin-bottom:.55rem}
        .dashboard-hero h1 {font-size:2.55rem!important;line-height:1.02;margin:0 0 .7rem!important;max-width:460px}
        .dashboard-hero p {color:#535b50;font-size:.96rem;line-height:1.55;margin:0 0 1rem;max-width:470px}
        .hero-meta {display:flex;gap:.45rem;flex-wrap:wrap}
        .hero-tag {display:inline-flex;align-items:center;background:rgba(255,255,255,.82);border:1px solid #d7ddd1;border-radius:999px;padding:.35rem .65rem;font-size:.72rem;font-weight:750;color:#363d34}
        .side-brand {display:flex;align-items:center;gap:.72rem;margin:.15rem 0 .9rem}
        .brand-mark {width:36px;height:36px;border-radius:8px;background:var(--lime);color:#20231f!important;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:900}
        .side-brand b {display:block;font-size:.93rem;letter-spacing:0!important}.side-brand small {display:block;color:#9da69a!important;font-size:.7rem;margin-top:.06rem}
        .empty-state {background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:2rem;text-align:center;color:var(--muted)}
        .login-hero {min-height:280px;background-size:cover;background-position:center 48%;border-radius:8px;padding:2.35rem;margin:1rem 0 1.4rem;border:1px solid var(--line);display:flex;align-items:center}
        .login-hero-copy {max-width:460px}.login-hero h1 {font-size:2.45rem!important;line-height:1.02}.login-hero p {max-width:430px;color:#555d52}
        .login-shell {max-width:520px;margin:0 auto 4rem}
        .stButton button,.stDownloadButton button {border-radius:7px;font-weight:750;min-height:40px}
        .stButton button[kind="primary"],.stDownloadButton button[kind="primary"] {background:#20231f;border-color:#20231f;color:#fff}
        div[data-baseweb="select"] > div, input, textarea {border-radius:7px!important}
        @media(max-width:800px){.block-container{padding:.75rem .75rem 3rem}h1{font-size:1.55rem!important}[data-testid="stMetric"]{min-height:98px;padding:.82rem}.schedule-band{align-items:flex-start;flex-direction:column;gap:.35rem}.schedule-step{white-space:normal}.dashboard-hero,.login-hero{min-height:300px;padding:1.35rem;background-position:left 48%}.hero-copy,.login-hero-copy{width:64%;}.dashboard-hero h1,.login-hero h1{font-size:1.85rem!important}.dashboard-hero p,.login-hero p{font-size:.82rem;line-height:1.4}.hero-meta{gap:.3rem}.hero-tag{font-size:.64rem;padding:.25rem .45rem}}
        </style>
        """
    css = css.replace("</style>", f'.dashboard-hero,.login-hero {{background-image:url("{hero_uri}")}}</style>')
    st.markdown(css, unsafe_allow_html=True)


@st.cache_data
def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def sidebar(repository, user):
    periods = repository.period_frame()
    period_options = periods.period.tolist() if not periods.empty else [date.today().strftime("%Y-%m")]
    with st.sidebar:
        st.markdown('<div class="side-brand"><div class="brand-mark">₫</div><div><b>PAYROLL 360</b><small>HHP + SBC</small></div></div>', unsafe_allow_html=True)
        st.divider()
        all_pages = ["Executive Overview", "Monthly Attendance", "Review & Approval", "Employee Payroll", "History & Comparison", "Salary Allocation", "System Administration"]
        pages = all_pages if user["role"] == "admin" else [item for item in all_pages if item not in ADMIN_PAGES]
        page = st.radio("Navigation", pages, label_visibility="collapsed")
        st.divider()
        selected_period = st.selectbox("Viewing period", period_options, format_func=period_label)
        st.caption(f"Signed in: {user['display_name']}")
        role_label = "Administrator" if user["role"] == "admin" else "Viewer"
        st.caption(f"Role: {role_label}")
        if st.button("Sign out", width="stretch"):
            logout()
    return page, selected_period


def render_page(repository, user, page, period):
    if page == "Executive Overview": render_dashboard(repository, period)
    elif page == "Monthly Attendance": render_monthly_import(repository, user)
    elif page == "Review & Approval": render_approval(repository, user, period)
    elif page == "Employee Payroll": render_employee_payroll(repository, period)
    elif page == "History & Comparison": render_history(repository)
    elif page == "Salary Allocation": render_template(repository, user)
    else: render_admin(repository, user)


def render_dashboard(repository, period):
    periods = repository.period_frame()
    frame = repository.summary_frame(period)
    if frame.empty:
        header("Executive Overview", "Monitor payroll costs, attendance, and issues requiring attention.", "Management report")
        empty("No data for this period", "An administrator must upload the attendance file and complete employee ID reconciliation.")
        return
    period_row = periods[periods.period == period].iloc[0] if not periods.empty and period in periods.period.values else None
    status = period_row.status if period_row is not None else "Bản nháp"
    updated_at = format_datetime(period_row.updated_at) if period_row is not None else "Unknown"
    dashboard_hero(period, status, updated_at)
    previous_period = previous_available_period(periods, period)
    previous = repository.summary_frame(previous_period) if previous_period else pd.DataFrame()
    total_salary = total(frame, "gross_pay")
    total_regular_pay = total(frame, "regular_pay")
    total_overtime_pay = total(frame, "overtime_pay")
    total_final = total(frame, "final_payable")
    finance_cols = st.columns(4)
    finance_cols[0].metric("Total payable", money(total_final), percentage_delta(total_final, total(previous, "final_payable") if not previous.empty else None))
    finance_cols[1].metric("Standard payroll", money(total_salary))
    finance_cols[2].metric("Regular pay", money(total_regular_pay))
    finance_cols[3].metric("Overtime pay", money(total_overtime_pay))
    operation_cols = st.columns(4)
    operation_cols[0].metric("Regular hours", hours(total(frame, "regular_hours")))
    operation_cols[1].metric("Overtime hours", hours(total(frame, "overtime_hours")))
    operation_cols[2].metric("Late arrival", f"{int(total(frame, 'late_minutes')):,} min")
    operation_cols[3].metric("Early departure", f"{int(total(frame, 'early_minutes')):,} min")
    st.markdown(
        '<div class="schedule-band"><span class="schedule-step"><strong>Morning shift</strong> 07:30–11:30</span><span class="schedule-step"><strong>Lunch break</strong> 11:30–13:00</span><span class="schedule-step"><strong>Afternoon shift</strong> 13:00–17:00</span><span class="schedule-step"><strong>Overtime</strong> after 17:00 × 1.5</span><span class="schedule-step"><strong>Standard hours</strong> 192 hours/month</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-label">Operations snapshot</div>', unsafe_allow_html=True)
    chart_left, chart_right = st.columns([1.18, 1])
    with chart_left:
        render_cost_chart(frame)
    with chart_right:
        render_hours_chart(frame)
    attendance_left, attendance_right = st.columns([0.72, 1.28])
    with attendance_left:
        render_attendance_health(frame)
    with attendance_right:
        render_discipline_chart(frame)
    if total_overtime_pay == 0:
        st.info("No employee clocked out after 17:00 this month, so overtime hours and overtime pay are both zero.")
    review = frame[frame.review_count > 0].copy()
    if not review.empty:
        st.markdown('<div class="notice-band"><b>Attention:</b> Some employees have late arrivals, early departures, absences, or records requiring review.</div>', unsafe_allow_html=True)
        display = review[["employee_id","full_name","department","late_count","late_minutes","early_count","early_minutes","absent_count","review_count"]].rename(columns={"employee_id":"Employee ID","full_name":"Full name","department":"Department","late_count":"Late occurrences","late_minutes":"Late minutes","early_count":"Early occurrences","early_minutes":"Early departure minutes","absent_count":"Absences","review_count":"Requires review"})
        st.dataframe(display, hide_index=True, width="stretch")
    st.markdown('<div class="section-label">Payroll payment summary</div>', unsafe_allow_html=True)
    payment = frame[["employee_id","full_name","department","gross_pay","base_hourly_rate","regular_hours","regular_pay","overtime_hours","overtime_hourly_rate","overtime_pay","final_payable"]].copy()
    payment = payment.sort_values("final_payable", ascending=False).rename(columns={"employee_id":"Employee ID","full_name":"Full name","department":"Department","gross_pay":"Standard monthly salary","base_hourly_rate":"Hourly rate","regular_hours":"Regular hours","regular_pay":"Regular pay","overtime_hours":"Overtime hours","overtime_hourly_rate":"Overtime hourly rate","overtime_pay":"Overtime pay","final_payable":"Total payable"})
    for column in ["Standard monthly salary", "Hourly rate", "Regular pay", "Overtime hourly rate", "Overtime pay", "Total payable"]:
        payment[column] = payment[column].map(money)
    st.dataframe(payment, hide_index=True, width="stretch")


def render_cost_chart(frame):
    costs = frame.sort_values("final_payable").copy()
    costs["_chart_name"] = costs.apply(employee_chart_label, axis=1)
    st.caption("Forest green: regular pay • Amber: overtime pay")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=costs._chart_name, x=costs.regular_pay, name="Regular pay", orientation="h", marker_color="#405F4A", customdata=costs.full_name, hovertemplate="%{customdata}<br>Regular pay: %{x:,.0f} ₫<extra></extra>"))
    fig.add_trace(go.Bar(y=costs._chart_name, x=costs.overtime_pay, name="Overtime pay", orientation="h", marker_color="#D2A642", customdata=costs.full_name, hovertemplate="%{customdata}<br>Overtime pay: %{x:,.0f} ₫<extra></extra>"))
    fig.add_trace(go.Scatter(y=costs._chart_name, x=costs.final_payable, mode="text", text=costs.final_payable.map(compact_money), textposition="middle right", showlegend=False, hoverinfo="skip"))
    fig.update_layout(barmode="stack")
    polish_chart(fig, "Payroll cost by employee", show_legend=False, height=430)
    fig.update_layout(margin=dict(l=102, r=58, t=55, b=16))
    fig.update_xaxes(showticklabels=False)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_hours_chart(frame):
    working = frame.sort_values("regular_hours").copy()
    working["_chart_name"] = working.apply(employee_chart_label, axis=1)
    st.caption("Lime: meets target • Blue-gray: monitor")
    fig = go.Figure()
    for name, mask, color in [
        ("At or above target", working.regular_hours >= 192, "#AFCF45"),
        ("Below 192 hours", working.regular_hours < 192, "#74877C"),
    ]:
        values = working.regular_hours.where(mask, 0)
        labels = [f"{value:.1f}g" if active else "" for value, active in zip(working.regular_hours, mask)]
        fig.add_trace(go.Bar(y=working._chart_name, x=values, name=name, orientation="h", marker_color=color, text=labels, textposition="outside", cliponaxis=False, customdata=working.full_name, hovertemplate="%{customdata}<br>%{x:.2f} hours<extra></extra>"))
    fig.add_vline(x=192, line_width=2, line_dash="dot", line_color="#20231F")
    fig.update_layout(barmode="stack")
    polish_chart(fig, "Worked hours vs. 192-hour standard", show_legend=False, height=430)
    fig.update_layout(margin=dict(l=102, r=48, t=55, b=26), xaxis_range=[0, max(210, float(working.regular_hours.max()) * 1.12)])
    fig.update_xaxes(tickvals=[0, 96, 192], ticktext=["0", "96", "192 hours"], tickangle=0)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_attendance_health(frame):
    reviewed = int(total(frame, "review_count"))
    shifts = int(total(frame, "shift_count"))
    clean = max(0, shifts - reviewed)
    quality = clean / shifts if shifts else 0
    st.caption("Attendance data quality overview")
    fig = go.Figure(go.Pie(values=[clean, reviewed], labels=["Healthy", "Requires review"], hole=.72, sort=False, marker_colors=["#AFCF45", "#D2A642"], textinfo="none", hovertemplate="%{label}: %{value} ca<extra></extra>"))
    fig.add_annotation(text=f"<b>{quality:.0%}</b><br><span style='font-size:11px'>healthy shifts</span>", showarrow=False, font=dict(size=21, color="#20231F"))
    polish_chart(fig, "Attendance health", show_legend=True, height=390)
    fig.update_layout(margin=dict(l=22, r=22, t=62, b=28), legend=dict(orientation="h", y=-.02, x=.5, xanchor="center"))
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_discipline_chart(frame):
    discipline = frame.copy()
    discipline["Late minutes"] = discipline.get("late_minutes", 0)
    discipline["Early departure minutes"] = discipline.get("early_minutes", 0)
    discipline = discipline.assign(_total=discipline["Late minutes"] + discipline["Early departure minutes"]).sort_values("_total")
    discipline["_chart_name"] = discipline.apply(employee_chart_label, axis=1)
    st.caption("Amber: late arrival • Blue-gray: early departure")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=discipline._chart_name, x=discipline["Late minutes"], name="Late arrival", orientation="h", marker_color="#D2A642", customdata=discipline.full_name, hovertemplate="%{customdata}<br>Late arrival: %{x:,.0f} min<extra></extra>"))
    fig.add_trace(go.Bar(y=discipline._chart_name, x=discipline["Early departure minutes"], name="Early departure", orientation="h", marker_color="#74877C", customdata=discipline.full_name, hovertemplate="%{customdata}<br>Early departure: %{x:,.0f} min<extra></extra>"))
    fig.update_layout(barmode="group")
    polish_chart(fig, "Attendance exceptions by employee", show_legend=False, height=390)
    fig.update_layout(margin=dict(l=102, r=26, t=55, b=26))
    fig.update_xaxes(tickangle=0, nticks=5)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_monthly_import(repository, user):
    header("Monthly Attendance", "Each month, select a period, upload the attendance file, and review the reconciliation results.", "Monthly workflow")
    if repository.template_history().empty:
        st.warning("No salary allocation is available. Upload the salary allocation file before processing attendance.")
        return
    with st.form("monthly_upload"):
        c1, c2 = st.columns([1, 2])
        period_date = c1.date_input("Payroll period", value=date.today().replace(day=1))
        uploaded = c2.file_uploader("Attendance file (XLSX or CSV)", type=["xlsx", "csv"])
        submitted = st.form_submit_button("Read and reconcile data", type="primary")
    if submitted and uploaded:
        try:
            frame = read_timesheet(uploaded, uploaded.name); period = period_date.strftime("%Y-%m"); inferred = infer_period(frame)
            template_frame = repository.active_templates(period)
            if template_frame.empty:
                st.error("No salary allocation is effective for the selected period."); return
            issues = reconcile_employee_ids(frame, template_frame) + attendance_quality_issues(frame)
            st.session_state["pending_month"] = {"period": period, "frame": frame, "issues": issues, "filename": uploaded.name}
            if inferred and inferred != period: st.warning(f"The file contains dates for {period_label(inferred)}, which differs from the selected period {period_label(period)}.")
        except Exception as exc: st.error(f"Unable to read the attendance file: {translate_text(str(exc))}")
    pending = st.session_state.get("pending_month")
    if not pending:
        st.info("The source file is never modified. The system stores normalized data only after confirmation."); return
    frame, issues = pending["frame"], pending["issues"]
    critical = sum(item["severity"] == "Nghiêm trọng" for item in issues); warning_count = len(issues) - critical
    cols = st.columns(4); cols[0].metric("Attendance rows", f"{len(frame):,}"); cols[1].metric("Employees", f"{frame.employee_id.astype(str).nunique():,}"); cols[2].metric("Critical errors", critical); cols[3].metric("Warnings", warning_count)
    tab1, tab2, tab3 = st.tabs(["Reconciliation results", "Attendance preview", "Employee summary"])
    with tab1:
        if issues: st.dataframe(english_frame(pd.DataFrame(issues).rename(columns={"employee_id":"Employee ID","severity":"Severity","message":"Details","code":"Error code"})), hide_index=True, width="stretch")
        else: st.success("All employee IDs and names match. No exceptions require action.")
    with tab2: st.dataframe(english_frame(frame.head(200)), hide_index=True, width="stretch")
    with tab3: st.dataframe(attendance_preview(frame), hide_index=True, width="stretch")
    if critical: st.error("Correct employee ID or name errors in the source file before saving the payroll period.")
    elif st.button("Confirm and save payroll period", type="primary"):
        try:
            repository.save_month(pending["period"], frame, issues, pending["filename"], user["username"])
            st.session_state.pop("pending_month", None); st.success("Payroll period saved. The dashboard and reports are now updated."); st.rerun()
        except ValueError as exc: st.error(translate_text(str(exc)))


def render_approval(repository, user, period):
    header("Review & Approval", "Resolve exceptions, validate totals, and lock the period after approval.", "Internal control")
    periods = repository.period_frame()
    if periods.empty or period not in periods.period.values:
        empty("No payroll data for this period", "Upload an attendance file before approval."); return
    current = periods[periods.period == period].iloc[0]; frame = repository.summary_frame(period); issues = repository.exception_frame(period); unresolved = issues[~issues.resolved] if not issues.empty else issues
    cols = st.columns(4); cols[0].metric("Status", STATUS_LABELS.get(current.status, current.status)); cols[1].metric("Total payable", money(total(frame, "final_payable"))); cols[2].metric("Unresolved exceptions", len(unresolved)); cols[3].metric("Attendance rows", f"{int(current.row_count):,}")
    if not issues.empty:
        st.subheader("Exception list")
        st.dataframe(english_frame(issues.rename(columns={"id":"ID","employee_id":"Employee ID","severity":"Severity","message":"Details","resolved":"Resolved","resolution_note":"Resolution note"})), hide_index=True, width="stretch")
        if not unresolved.empty:
            with st.form("resolve_issue"):
                issue_id = st.selectbox("Select exception", unresolved.id.tolist()); note = st.text_area("Reason and resolution")
                if st.form_submit_button("Mark as resolved"):
                    if len(note.strip()) < 5: st.error("Enter a clear resolution note.")
                    else: repository.resolve_exception(int(issue_id), note.strip(), user["username"]); st.success("Resolution saved."); st.rerun()
    st.subheader("Change payroll period status")
    current_index = STATUS_ORDER.index(current.status) if current.status in STATUS_ORDER else 0
    target = st.selectbox("New status", STATUS_ORDER, index=current_index, format_func=lambda value: STATUS_LABELS.get(value, value))
    st.caption("Attendance cannot be re-imported for a locked period. Any post-lock change requires an adjustment and documented reason.")
    if st.button("Update status", type="primary"):
        try: repository.set_status(period, target, user["username"]); st.success("Payroll period status updated."); st.rerun()
        except ValueError as exc: st.error(translate_text(str(exc)))


def render_employee_payroll(repository, period):
    header("Employee Payroll", "Review payroll details by period and export an individual payslip for each employee.", "Detailed report")
    frame = repository.summary_frame(period)
    if frame.empty:
        empty("No payroll available", "The selected period has no processed data."); return
    c1, c2, c3 = st.columns(3)
    company = c1.selectbox("Company", ["All"] + sorted(frame.company.dropna().unique().tolist())); department = c2.selectbox("Department", ["All"] + sorted(frame.department.dropna().unique().tolist())); employee = c3.selectbox("Employees", ["All"] + [f"{row.employee_id} - {row.full_name}" for _, row in frame.iterrows()])
    filtered = frame.copy()
    if company != "All": filtered = filtered[filtered.company == company]
    if department != "All": filtered = filtered[filtered.department == department]
    if employee != "All": filtered = filtered[filtered.employee_id == employee.split(" - ", 1)[0]]
    display_columns = ["employee_id","full_name","company","department","gross_pay","base_hourly_rate","regular_hours","regular_pay","overtime_hours","overtime_hourly_rate","overtime_pay","final_payable","insurance_salary","bonus_pool","employee_insurance","employer_insurance","shift_count","late_count","late_minutes","early_count","early_minutes","absent_count"]
    display = filtered[[column for column in display_columns if column in filtered]].copy()
    if "tracked_minutes" in display: display["tracked_minutes"] = display.tracked_minutes / 60
    labels = {"employee_id":"Employee ID","full_name":"Full name","company":"Company","department":"Department","gross_pay":"Standard monthly salary","base_hourly_rate":"Hourly rate","regular_hours":"Regular hours","regular_pay":"Regular pay","overtime_hours":"Overtime hours","overtime_hourly_rate":"Overtime hourly rate","overtime_pay":"Overtime pay","final_payable":"Total payable","insurance_salary":"Base salary","bonus_pool":"Total bonus","employee_insurance":"Employee insurance","employer_insurance":"Employer insurance","shift_count":"Shifts","late_count":"Late occurrences","late_minutes":"Late minutes","early_count":"Early occurrences","early_minutes":"Early departure minutes","absent_count":"Absent"}
    display = display.rename(columns=labels)
    for column in ["Standard monthly salary","Hourly rate","Regular pay","Overtime hourly rate","Overtime pay","Total payable","Base salary","Total bonus","Employee insurance","Employer insurance"]:
        if column in display: display[column] = display[column].map(money)
    st.dataframe(display, hide_index=True, width="stretch")
    excel_rows = filtered.to_dict("records")
    st.download_button("Download payroll Excel", payroll_excel(excel_rows), f"bang_luong_{period}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    selected_id = st.selectbox("Export individual payslip", filtered.employee_id.tolist()); selected_row = filtered[filtered.employee_id == selected_id].iloc[0].to_dict()
    st.download_button("Download payslip PDF", payslip_pdf(selected_row, period), f"phieu_luong_{selected_id}_{period}.pdf", "application/pdf")


def render_history(repository):
    header("History & Comparison", "Track payroll cost and attendance changes across periods.", "Trend analysis")
    all_data = repository.summary_frame()
    if all_data.empty:
        empty("Insufficient historical data", "Trends and comparisons will appear after multiple periods have been processed."); return
    monthly = all_data.groupby("period", as_index=False).agg(Tổng_cần_trả=("final_payable","sum"), Lương_phân_bổ=("gross_pay","sum"), Tiền_tăng_ca=("overtime_pay","sum"), Giờ_tăng_ca=("overtime_hours","sum"), Giờ_thường=("regular_hours","sum"), Nhân_viên=("employee_id","nunique")).sort_values("period")
    fig = go.Figure(); fig.add_trace(go.Scatter(x=monthly.period, y=monthly["Tổng_cần_trả"], mode="lines+markers", name="Total payable", line=dict(color="#176B5B",width=3))); fig.add_trace(go.Bar(x=monthly.period, y=monthly["Tiền_tăng_ca"], name="Overtime pay", marker_color="#D97706", opacity=.8)); polish_chart(fig, "Monthly total payroll and overtime trend")
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    display = monthly.rename(columns={"period":"Period","Tổng_cần_trả":"Total payable","Lương_phân_bổ":"Allocated salary","Tiền_tăng_ca":"Overtime pay","Giờ_tăng_ca":"Overtime hours","Giờ_thường":"Regular hours","Nhân_viên":"Employees"})
    for column in ["Total payable","Allocated salary","Overtime pay"]: display[column] = display[column].map(money)
    st.dataframe(display, hide_index=True, width="stretch")
    if len(monthly) < 2: st.info("Only one period is available. Comparisons will appear automatically when the next period is added.")


def render_template(repository, user):
    header("Salary Allocation", "Maintain the salary baseline reused each month and update it only when policy changes.", "Business configuration")
    history = repository.template_history()
    if not history.empty: st.dataframe(english_frame(history), hide_index=True, width="stretch")
    with st.form("template_upload"):
        c1, c2 = st.columns([1, 2]); effective = c1.date_input("Effective from", value=date.today().replace(day=1)); uploaded = c2.file_uploader("Salary allocation file (XLSX)", type=["xlsx"]); submitted = st.form_submit_button("Read salary allocation", type="primary")
    if submitted and uploaded:
        try: st.session_state["pending_template"] = {"frame": read_authoritative_payroll(uploaded), "effective": effective.strftime("%Y-%m")}
        except Exception as exc: st.error(f"Unable to read the salary allocation file: {translate_text(str(exc))}")
    pending = st.session_state.get("pending_template")
    if pending:
        frame = pending["frame"]; cols = st.columns(4); cols[0].metric("Employees", len(frame)); cols[1].metric("Total salary", money(total(frame,"gross_pay"))); cols[2].metric("Employee insurance", money(total(frame,"employee_insurance"))); cols[3].metric("Employer insurance", money(total(frame,"employer_insurance")))
        st.dataframe(frame, hide_index=True, width="stretch"); st.warning("Once confirmed, the new configuration takes effect from the selected month. Previous history is preserved.")
        if st.button("Confirm salary allocation update", type="primary"):
            repository.save_payroll_template(frame, pending["effective"], user["username"]); st.session_state.pop("pending_template", None); st.success("Salary allocation updated."); st.rerun()


def render_admin(repository, user):
    header("System Administration", "Manage accounts, verify data connectivity, and review the activity log.", "Security configuration")
    tab1, tab2, tab3 = st.tabs(["Accounts", "Audit log", "System status"])
    with tab1:
        users = repository.user_frame()
        if not users.empty: st.dataframe(users.rename(columns={"username":"Username","display_name":"Full name","role":"Role","active":"Active","created_at":"Created at"}), hide_index=True, width="stretch")
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3); username = c1.text_input("New username"); display_name = c2.text_input("Full name"); role = c3.selectbox("Role", ["viewer", "admin"], format_func=lambda x: "Viewer" if x == "viewer" else "Administrator"); password = st.text_input("Temporary password", type="password")
            if st.form_submit_button("Create or update account"):
                if len(username.strip()) < 3 or len(display_name.strip()) < 2 or len(password) < 10: st.error("The username, full name, or password does not meet requirements. Passwords must contain at least 10 characters.")
                else: repository.save_user(username.strip(), display_name.strip(), hash_password(password), role, user["username"]); st.success("Account saved."); st.rerun()
    with tab2: st.dataframe(english_frame(repository.audit_frame().rename(columns={"event_time":"Time","actor":"Actor","action":"Action","entity_type":"Entity","entity_id":"ID","details":"Details"})), hide_index=True, width="stretch")
    with tab3:
        database_type = "Cloud PostgreSQL" if repository.database_url.startswith("postgres") else "Local SQLite"; st.metric("Data store", database_type)
        if database_type == "Local SQLite": st.warning("This mode is suitable for local Mac use. Configure DATABASE_URL before production deployment so history persists across server restarts.")
        else: st.success("The application is using persistent storage suitable for web deployment.")


def attendance_quality_issues(frame):
    issues = []
    for employee_id, rows in frame.groupby(frame.employee_id.astype(str)):
        explicit = rows.get("needs_review", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.strip(); statuses = rows.get("attendance_status", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.lower(); count = int((explicit.ne("") | statuses.ne("bình thường")).sum())
        if count: issues.append({"code":"ATTENDANCE_REVIEW","severity":"Warnings","row":None,"employee_id":employee_id,"message":f"There are {count} late, early, absent, or review-required shifts."})
    return issues


def attendance_preview(frame):
    data = []
    for employee_id, rows in frame.groupby(frame.employee_id.astype(str)):
        statuses = rows.get("attendance_status", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.lower()
        tracked = pd.to_numeric(rows.get("tracked_minutes", pd.Series(index=rows.index, dtype=float)), errors="coerce").fillna(0).sum()
        data.append({"Employee ID":employee_id,"Full name":rows.full_name.dropna().iloc[0] if rows.full_name.notna().any() else "","Shifts":len(rows),"Normal":int(statuses.eq("bình thường").sum()),"Late":int(statuses.str.contains("muộn").sum()),"Early departure":int(statuses.str.contains("về sớm").sum()),"Absences":int(statuses.str.contains("vắng mặt").sum()),"Total hours":round(tracked/60,1)})
    return pd.DataFrame(data)


def infer_period(frame):
    if "work_date" not in frame or frame.work_date.dropna().empty: return None
    return pd.to_datetime(frame.work_date.dropna().iloc[0]).strftime("%Y-%m")


def header(title, subtitle, kicker):
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True); st.title(title); st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def dashboard_hero(period, status, updated_at):
    st.markdown(
        f'<section class="dashboard-hero"><div class="hero-copy"><div class="hero-eyebrow">HHP + SBC · OPERATIONS CENTER</div><h1>Payroll &amp; people</h1><p>Payroll costs, worked hours, and action items in one unified view.</p><div class="hero-meta"><span class="hero-tag">{period_label(period)}</span><span class="hero-tag">{STATUS_LABELS.get(status, status)}</span><span class="hero-tag">Updated {updated_at}</span></div></div></section>',
        unsafe_allow_html=True,
    )


def empty(title, message): st.markdown(f'<div class="empty-state"><b>{title}</b><br>{message}</div>', unsafe_allow_html=True)


DISPLAY_TRANSLATIONS = {
    **STATUS_LABELS,
    "Nghiêm trọng": "Critical",
    "Cảnh báo": "Warning",
    "bình thường": "normal",
    "Bình thường": "Normal",
    "muộn": "late",
    "về sớm": "early departure",
    "vắng mặt": "absent",
    "Mã nhân viên": "Employee ID",
    "Họ và tên": "Full name",
    "Bộ phận": "Department",
    "Hiệu lực từ": "Effective from",
    "Hiệu lực đến": "Effective to",
    "Đang áp dụng": "Active",
    "Người cập nhật": "Updated by",
    "Lưu tài khoản": "Save account",
    "Cập nhật phân bổ lương chuẩn": "Update salary allocation",
    "Nhập chấm công tháng": "Import monthly attendance",
    "Xử lý ngoại lệ": "Resolve exception",
    "Đổi trạng thái": "Change status",
    "Thiết lập": "Setup",
}


def translate_text(value):
    if not isinstance(value, str):
        return value
    translated = value
    phrases = {
        "Không thể lưu khi còn lỗi ID hoặc tên nghiêm trọng": "Cannot save while critical employee ID or name errors remain",
        "Chưa có phân bổ lương chuẩn có hiệu lực cho kỳ này": "No salary allocation is effective for this period",
        "Kỳ lương đã khóa; không thể nhập lại chấm công": "The payroll period is locked; attendance cannot be re-imported",
        "Kỳ lương chưa có dữ liệu": "The payroll period has no data",
        "Trạng thái không hợp lệ": "Invalid status",
        "lỗi nghiêm trọng chưa xử lý": "unresolved critical errors remain",
        "Thiếu cột bắt buộc": "Missing required column",
        "Thiếu mã nhân viên": "Missing employee ID",
        "Mã nhân viên chưa có trong danh mục": "Employee ID is not in the roster",
        "Dòng chấm công bị trùng": "Duplicate attendance row",
        "Thiếu giờ vào hoặc giờ ra": "Missing clock-in or clock-out time",
        "Tăng ca chưa được phê duyệt và sẽ không được trả": "Overtime is not approved and will not be paid",
        "ID có trong chấm công nhưng không có trong bảng lương chính thức": "The attendance employee ID is missing from the official payroll",
        "ID có trong bảng lương nhưng không có chấm công tháng này": "The payroll employee ID has no attendance this month",
        "Tên theo ID không khớp": "The name does not match the employee ID",
        "ca muộn, về sớm, vắng mặt hoặc cần kiểm tra": "late, early, absent, or review-required shifts",
    }
    for source, target in phrases.items():
        translated = translated.replace(source, target)
    return DISPLAY_TRANSLATIONS.get(translated, translated)


def english_frame(frame):
    translated = frame.copy()
    translated = translated.rename(columns={column: DISPLAY_TRANSLATIONS.get(column, column) for column in translated.columns})
    for column in translated.select_dtypes(include="object").columns:
        translated[column] = translated[column].map(translate_text)
    return translated


def total(frame, column): return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum()) if column in frame else 0.0


def money(value): return f"VND {float(value or 0):,.0f}"


def compact_money(value):
    value = float(value or 0)
    if abs(value) >= 1_000_000:
        return f"VND {value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"VND {value / 1_000:.0f}K"
    return f"VND {value:,.0f}"


def employee_chart_label(row):
    words = str(row.get("full_name", "")).split()
    short_name = " ".join(words[-2:]) if words else "Unknown"
    return f"{str(row.get('employee_id', '')).zfill(2)} · {short_name}"


def hours(value):
    formatted = f"{float(value or 0):,.1f}"
    return f"{formatted} hours"


def period_label(period):
    try: year, month = str(period).split("-"); return f"Month {month}/{year}"
    except ValueError: return str(period)


def format_datetime(value):
    if value is None or pd.isna(value): return "Unknown"
    if isinstance(value, str): value = datetime.fromisoformat(value)
    return value.strftime("%b %d, %Y %H:%M")


def previous_available_period(periods, period):
    if periods.empty: return None
    ordered = sorted(periods.period.tolist())
    if period not in ordered: return None
    index = ordered.index(period); return ordered[index - 1] if index > 0 else None


def percentage_delta(current, previous):
    if previous in (None, 0): return None
    return f"{(current - previous) / previous:+.1%} vs. previous month"


def polish_chart(fig, title, show_legend=True, height=350):
    fig.update_layout(title=dict(text=title, font=dict(size=15, color="#20231F")), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", margin=dict(l=20,r=20,t=58,b=20), height=height, font=dict(family="Arial", color="#626A5F"), legend=dict(orientation="h", y=1.08, x=1, xanchor="right", yanchor="bottom"), showlegend=show_legend, hoverlabel=dict(bgcolor="#20231F",font_color="#FFFFFF"))
    fig.update_xaxes(showgrid=True, gridcolor="#EBEEE8", zeroline=False, title=None, tickformat=","); fig.update_yaxes(showgrid=False, zeroline=False, title=None, automargin=True)


if __name__ == "__main__": main()
