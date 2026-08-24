from __future__ import annotations

import base64
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.services.auth import hash_password, logout, require_authentication
from app.services.exporter import payroll_excel, payslip_pdf
from app.services.importer import read_authoritative_payroll, read_timesheet, reconcile_employee_ids
from app.services.repository import PayrollRepository


STATUS_ORDER = ["Bản nháp", "Đang kiểm tra", "Chờ phê duyệt", "Đã phê duyệt", "Đã khóa", "Đã thanh toán"]
ADMIN_PAGES = ["Xử lý chấm công tháng", "Kiểm tra và phê duyệt", "Phân bổ lương chuẩn", "Quản trị hệ thống"]
PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}
ROOT = Path(__file__).parents[1]
HERO_ASSET = ROOT / "app" / "assets" / "payroll-operations-hero.png"


def main():
    st.set_page_config(page_title="Quản trị lương", page_icon="₫", layout="wide", initial_sidebar_state="expanded")
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
        st.markdown('<div class="side-brand"><div class="brand-mark">₫</div><div><b>LƯƠNG 360</b><small>HHP + SBC</small></div></div>', unsafe_allow_html=True)
        st.divider()
        all_pages = ["Tổng quan điều hành", "Xử lý chấm công tháng", "Kiểm tra và phê duyệt", "Bảng lương nhân viên", "Lịch sử và so sánh", "Phân bổ lương chuẩn", "Quản trị hệ thống"]
        pages = all_pages if user["role"] == "admin" else [item for item in all_pages if item not in ADMIN_PAGES]
        page = st.radio("Điều hướng", pages, label_visibility="collapsed")
        st.divider()
        selected_period = st.selectbox("Kỳ đang xem", period_options, format_func=period_label)
        st.caption(f"Đăng nhập: {user['display_name']}")
        role_label = "Quản trị viên" if user["role"] == "admin" else "Người xem"
        st.caption(f"Vai trò: {role_label}")
        if st.button("Đăng xuất", width="stretch"):
            logout()
    return page, selected_period


def render_page(repository, user, page, period):
    if page == "Tổng quan điều hành": render_dashboard(repository, period)
    elif page == "Xử lý chấm công tháng": render_monthly_import(repository, user)
    elif page == "Kiểm tra và phê duyệt": render_approval(repository, user, period)
    elif page == "Bảng lương nhân viên": render_employee_payroll(repository, period)
    elif page == "Lịch sử và so sánh": render_history(repository)
    elif page == "Phân bổ lương chuẩn": render_template(repository, user)
    else: render_admin(repository, user)


def render_dashboard(repository, period):
    periods = repository.period_frame()
    frame = repository.summary_frame(period)
    if frame.empty:
        header("Tổng quan điều hành", "Theo dõi chi phí lương, tình hình chấm công và các vấn đề cần xử lý.", "Báo cáo quản trị")
        empty("Chưa có dữ liệu cho kỳ này", "Quản trị viên cần tải bảng chấm công và hoàn tất đối chiếu ID.")
        return
    period_row = periods[periods.period == period].iloc[0] if not periods.empty and period in periods.period.values else None
    status = period_row.status if period_row is not None else "Bản nháp"
    updated_at = format_datetime(period_row.updated_at) if period_row is not None else "Chưa rõ"
    dashboard_hero(period, status, updated_at)
    previous_period = previous_available_period(periods, period)
    previous = repository.summary_frame(previous_period) if previous_period else pd.DataFrame()
    total_salary = total(frame, "gross_pay")
    total_regular_pay = total(frame, "regular_pay")
    total_overtime_pay = total(frame, "overtime_pay")
    total_final = total(frame, "final_payable")
    finance_cols = st.columns(4)
    finance_cols[0].metric("Tổng thực trả", money(total_final), percentage_delta(total_final, total(previous, "final_payable") if not previous.empty else None))
    finance_cols[1].metric("Quỹ lương chuẩn", money(total_salary))
    finance_cols[2].metric("Lương giờ thường", money(total_regular_pay))
    finance_cols[3].metric("Tiền tăng ca", money(total_overtime_pay))
    operation_cols = st.columns(4)
    operation_cols[0].metric("Giờ thường", hours(total(frame, "regular_hours")))
    operation_cols[1].metric("Giờ tăng ca", hours(total(frame, "overtime_hours")))
    operation_cols[2].metric("Đi muộn", f"{int(total(frame, 'late_minutes')):,} phút".replace(",", "."))
    operation_cols[3].metric("Về sớm", f"{int(total(frame, 'early_minutes')):,} phút".replace(",", "."))
    st.markdown(
        '<div class="schedule-band"><span class="schedule-step"><strong>Ca sáng</strong> 07:30–11:30</span><span class="schedule-step"><strong>Nghỉ trưa</strong> 11:30–13:00</span><span class="schedule-step"><strong>Ca chiều</strong> 13:00–17:00</span><span class="schedule-step"><strong>Tăng ca</strong> sau 17:00 × 1,5</span><span class="schedule-step"><strong>Giờ chuẩn</strong> 192 giờ/tháng</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-label">Bức tranh vận hành</div>', unsafe_allow_html=True)
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
        st.info("Tháng này không có lượt ra sau 17:00, vì vậy giờ tăng ca và tiền tăng ca đều bằng 0.")
    review = frame[frame.review_count > 0].copy()
    if not review.empty:
        st.markdown('<div class="notice-band"><b>Cần chú ý:</b> Có nhân viên phát sinh ca muộn, về sớm, vắng mặt hoặc dữ liệu cần kiểm tra.</div>', unsafe_allow_html=True)
        display = review[["employee_id","full_name","department","late_count","late_minutes","early_count","early_minutes","absent_count","review_count"]].rename(columns={"employee_id":"Mã NV","full_name":"Họ và tên","department":"Bộ phận","late_count":"Lần muộn","late_minutes":"Phút muộn","early_count":"Lần về sớm","early_minutes":"Phút về sớm","absent_count":"Vắng mặt","review_count":"Cần kiểm tra"})
        st.dataframe(display, hide_index=True, width="stretch")
    st.markdown('<div class="section-label">Tổng hợp số tiền cần trả</div>', unsafe_allow_html=True)
    payment = frame[["employee_id","full_name","department","gross_pay","base_hourly_rate","regular_hours","regular_pay","overtime_hours","overtime_hourly_rate","overtime_pay","final_payable"]].copy()
    payment = payment.sort_values("final_payable", ascending=False).rename(columns={"employee_id":"Mã NV","full_name":"Họ và tên","department":"Bộ phận","gross_pay":"Lương tháng chuẩn","base_hourly_rate":"Đơn giá/giờ","regular_hours":"Giờ thường","regular_pay":"Lương giờ thường","overtime_hours":"Giờ tăng ca","overtime_hourly_rate":"Đơn giá OT/giờ","overtime_pay":"Tiền tăng ca","final_payable":"Tổng thực trả"})
    for column in ["Lương tháng chuẩn", "Đơn giá/giờ", "Lương giờ thường", "Đơn giá OT/giờ", "Tiền tăng ca", "Tổng thực trả"]:
        payment[column] = payment[column].map(money)
    st.dataframe(payment, hide_index=True, width="stretch")


def render_cost_chart(frame):
    costs = frame.sort_values("final_payable").copy()
    costs["_chart_name"] = costs.apply(employee_chart_label, axis=1)
    st.caption("Xanh rêu: lương giờ thường • Hổ phách: tiền tăng ca")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=costs._chart_name, x=costs.regular_pay, name="Lương giờ thường", orientation="h", marker_color="#405F4A", customdata=costs.full_name, hovertemplate="%{customdata}<br>Lương giờ thường: %{x:,.0f} ₫<extra></extra>"))
    fig.add_trace(go.Bar(y=costs._chart_name, x=costs.overtime_pay, name="Tiền tăng ca", orientation="h", marker_color="#D2A642", customdata=costs.full_name, hovertemplate="%{customdata}<br>Tiền tăng ca: %{x:,.0f} ₫<extra></extra>"))
    fig.add_trace(go.Scatter(y=costs._chart_name, x=costs.final_payable, mode="text", text=costs.final_payable.map(compact_money), textposition="middle right", showlegend=False, hoverinfo="skip"))
    fig.update_layout(barmode="stack")
    polish_chart(fig, "Chi phí lương theo nhân viên", show_legend=False, height=430)
    fig.update_layout(margin=dict(l=102, r=58, t=55, b=16))
    fig.update_xaxes(showticklabels=False)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_hours_chart(frame):
    working = frame.sort_values("regular_hours").copy()
    working["_chart_name"] = working.apply(employee_chart_label, axis=1)
    st.caption("Xanh chanh: đạt chuẩn • Xám xanh: cần theo dõi")
    fig = go.Figure()
    for name, mask, color in [
        ("Đạt hoặc vượt chuẩn", working.regular_hours >= 192, "#AFCF45"),
        ("Dưới 192 giờ", working.regular_hours < 192, "#74877C"),
    ]:
        values = working.regular_hours.where(mask, 0)
        labels = [f"{value:.1f}g" if active else "" for value, active in zip(working.regular_hours, mask)]
        fig.add_trace(go.Bar(y=working._chart_name, x=values, name=name, orientation="h", marker_color=color, text=labels, textposition="outside", cliponaxis=False, customdata=working.full_name, hovertemplate="%{customdata}<br>%{x:.2f} giờ<extra></extra>"))
    fig.add_vline(x=192, line_width=2, line_dash="dot", line_color="#20231F")
    fig.update_layout(barmode="stack")
    polish_chart(fig, "Giờ công so với chuẩn 192 giờ", show_legend=False, height=430)
    fig.update_layout(margin=dict(l=102, r=48, t=55, b=26), xaxis_range=[0, max(210, float(working.regular_hours.max()) * 1.12)])
    fig.update_xaxes(tickvals=[0, 96, 192], ticktext=["0", "96", "192 giờ"], tickangle=0)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_attendance_health(frame):
    reviewed = int(total(frame, "review_count"))
    shifts = int(total(frame, "shift_count"))
    clean = max(0, shifts - reviewed)
    quality = clean / shifts if shifts else 0
    st.caption("Tổng quan chất lượng dữ liệu chấm công")
    fig = go.Figure(go.Pie(values=[clean, reviewed], labels=["Ổn định", "Cần kiểm tra"], hole=.72, sort=False, marker_colors=["#AFCF45", "#D2A642"], textinfo="none", hovertemplate="%{label}: %{value} ca<extra></extra>"))
    fig.add_annotation(text=f"<b>{quality:.0%}</b><br><span style='font-size:11px'>ca ổn định</span>", showarrow=False, font=dict(size=21, color="#20231F"))
    polish_chart(fig, "Sức khỏe chấm công", show_legend=True, height=390)
    fig.update_layout(margin=dict(l=22, r=22, t=62, b=28), legend=dict(orientation="h", y=-.02, x=.5, xanchor="center"))
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_discipline_chart(frame):
    discipline = frame.copy()
    discipline["Phút đi muộn"] = discipline.get("late_minutes", 0)
    discipline["Phút về sớm"] = discipline.get("early_minutes", 0)
    discipline = discipline.assign(_total=discipline["Phút đi muộn"] + discipline["Phút về sớm"]).sort_values("_total")
    discipline["_chart_name"] = discipline.apply(employee_chart_label, axis=1)
    st.caption("Hổ phách: đi muộn • Xám xanh: về sớm")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=discipline._chart_name, x=discipline["Phút đi muộn"], name="Đi muộn", orientation="h", marker_color="#D2A642", customdata=discipline.full_name, hovertemplate="%{customdata}<br>Đi muộn: %{x:,.0f} phút<extra></extra>"))
    fig.add_trace(go.Bar(y=discipline._chart_name, x=discipline["Phút về sớm"], name="Về sớm", orientation="h", marker_color="#74877C", customdata=discipline.full_name, hovertemplate="%{customdata}<br>Về sớm: %{x:,.0f} phút<extra></extra>"))
    fig.update_layout(barmode="group")
    polish_chart(fig, "Điểm cần chú ý theo nhân viên", show_legend=False, height=390)
    fig.update_layout(margin=dict(l=102, r=26, t=55, b=26))
    fig.update_xaxes(tickangle=0, nticks=5)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def render_monthly_import(repository, user):
    header("Xử lý chấm công tháng", "Mỗi tháng chỉ cần chọn kỳ, tải file chấm công và kiểm tra kết quả đối chiếu.", "Quy trình hằng tháng")
    if repository.template_history().empty:
        st.warning("Chưa có phân bổ lương chuẩn. Hãy nhập file phân bổ lương trước khi xử lý chấm công.")
        return
    with st.form("monthly_upload"):
        c1, c2 = st.columns([1, 2])
        period_date = c1.date_input("Kỳ lương", value=date.today().replace(day=1))
        uploaded = c2.file_uploader("Bảng chấm công XLSX hoặc CSV", type=["xlsx", "csv"])
        submitted = st.form_submit_button("Đọc và đối chiếu dữ liệu", type="primary")
    if submitted and uploaded:
        try:
            frame = read_timesheet(uploaded, uploaded.name); period = period_date.strftime("%Y-%m"); inferred = infer_period(frame)
            template_frame = repository.active_templates(period)
            if template_frame.empty:
                st.error("Không có phân bổ lương chuẩn có hiệu lực cho kỳ đã chọn."); return
            issues = reconcile_employee_ids(frame, template_frame) + attendance_quality_issues(frame)
            st.session_state["pending_month"] = {"period": period, "frame": frame, "issues": issues, "filename": uploaded.name}
            if inferred and inferred != period: st.warning(f"Ngày trong file thuộc kỳ {period_label(inferred)}, khác kỳ đang chọn {period_label(period)}.")
        except Exception as exc: st.error(f"Không thể đọc file chấm công: {exc}")
    pending = st.session_state.get("pending_month")
    if not pending:
        st.info("File nguồn không bị thay đổi. Hệ thống chỉ lưu dữ liệu chuẩn hóa sau khi bạn xác nhận."); return
    frame, issues = pending["frame"], pending["issues"]
    critical = sum(item["severity"] == "Nghiêm trọng" for item in issues); warning_count = len(issues) - critical
    cols = st.columns(4); cols[0].metric("Dòng chấm công", f"{len(frame):,}"); cols[1].metric("Nhân viên", f"{frame.employee_id.astype(str).nunique():,}"); cols[2].metric("Lỗi nghiêm trọng", critical); cols[3].metric("Cảnh báo", warning_count)
    tab1, tab2, tab3 = st.tabs(["Kết quả đối chiếu", "Xem trước chấm công", "Tóm tắt nhân viên"])
    with tab1:
        if issues: st.dataframe(pd.DataFrame(issues).rename(columns={"employee_id":"Mã NV","severity":"Mức độ","message":"Nội dung","code":"Mã lỗi"}), hide_index=True, width="stretch")
        else: st.success("ID và tên khớp hoàn toàn. Không có ngoại lệ cần xử lý.")
    with tab2: st.dataframe(frame.head(200), hide_index=True, width="stretch")
    with tab3: st.dataframe(attendance_preview(frame), hide_index=True, width="stretch")
    if critical: st.error("Cần sửa lỗi ID hoặc tên trong file nguồn trước khi lưu kỳ lương.")
    elif st.button("Xác nhận lưu kỳ lương", type="primary"):
        try:
            repository.save_month(pending["period"], frame, issues, pending["filename"], user["username"])
            st.session_state.pop("pending_month", None); st.success("Đã lưu kỳ lương. Dashboard và báo cáo đã được cập nhật."); st.rerun()
        except ValueError as exc: st.error(str(exc))


def render_approval(repository, user, period):
    header("Kiểm tra và phê duyệt", "Xử lý ngoại lệ, kiểm tra tổng số liệu và khóa kỳ sau khi phê duyệt.", "Kiểm soát nội bộ")
    periods = repository.period_frame()
    if periods.empty or period not in periods.period.values:
        empty("Kỳ lương chưa có dữ liệu", "Hãy nhập bảng chấm công trước khi phê duyệt."); return
    current = periods[periods.period == period].iloc[0]; frame = repository.summary_frame(period); issues = repository.exception_frame(period); unresolved = issues[~issues.resolved] if not issues.empty else issues
    cols = st.columns(4); cols[0].metric("Trạng thái", current.status); cols[1].metric("Tổng thực trả", money(total(frame, "final_payable"))); cols[2].metric("Ngoại lệ chưa xử lý", len(unresolved)); cols[3].metric("Dòng chấm công", f"{int(current.row_count):,}")
    if not issues.empty:
        st.subheader("Danh sách ngoại lệ")
        st.dataframe(issues.rename(columns={"id":"ID","employee_id":"Mã NV","severity":"Mức độ","message":"Nội dung","resolved":"Đã xử lý","resolution_note":"Lý do xử lý"}), hide_index=True, width="stretch")
        if not unresolved.empty:
            with st.form("resolve_issue"):
                issue_id = st.selectbox("Chọn ngoại lệ", unresolved.id.tolist()); note = st.text_area("Lý do và cách xử lý")
                if st.form_submit_button("Đánh dấu đã xử lý"):
                    if len(note.strip()) < 5: st.error("Cần ghi lý do xử lý rõ ràng.")
                    else: repository.resolve_exception(int(issue_id), note.strip(), user["username"]); st.success("Đã lưu cách xử lý."); st.rerun()
    st.subheader("Chuyển trạng thái kỳ lương")
    current_index = STATUS_ORDER.index(current.status) if current.status in STATUS_ORDER else 0
    target = st.selectbox("Trạng thái mới", STATUS_ORDER, index=current_index)
    st.caption("Kỳ đã khóa không thể nhập lại chấm công. Mọi thay đổi sau khóa phải có điều chỉnh và lý do.")
    if st.button("Cập nhật trạng thái", type="primary"):
        try: repository.set_status(period, target, user["username"]); st.success("Đã cập nhật trạng thái kỳ lương."); st.rerun()
        except ValueError as exc: st.error(str(exc))


def render_employee_payroll(repository, period):
    header("Bảng lương nhân viên", "Tra cứu chi tiết lương theo kỳ và xuất phiếu lương riêng cho từng nhân viên.", "Báo cáo chi tiết")
    frame = repository.summary_frame(period)
    if frame.empty:
        empty("Chưa có bảng lương", "Kỳ được chọn chưa có dữ liệu đã xử lý."); return
    c1, c2, c3 = st.columns(3)
    company = c1.selectbox("Công ty", ["Tất cả"] + sorted(frame.company.dropna().unique().tolist())); department = c2.selectbox("Bộ phận", ["Tất cả"] + sorted(frame.department.dropna().unique().tolist())); employee = c3.selectbox("Nhân viên", ["Tất cả"] + [f"{row.employee_id} - {row.full_name}" for _, row in frame.iterrows()])
    filtered = frame.copy()
    if company != "Tất cả": filtered = filtered[filtered.company == company]
    if department != "Tất cả": filtered = filtered[filtered.department == department]
    if employee != "Tất cả": filtered = filtered[filtered.employee_id == employee.split(" - ", 1)[0]]
    display_columns = ["employee_id","full_name","company","department","gross_pay","base_hourly_rate","regular_hours","regular_pay","overtime_hours","overtime_hourly_rate","overtime_pay","final_payable","insurance_salary","bonus_pool","employee_insurance","employer_insurance","shift_count","late_count","late_minutes","early_count","early_minutes","absent_count"]
    display = filtered[[column for column in display_columns if column in filtered]].copy()
    if "tracked_minutes" in display: display["tracked_minutes"] = display.tracked_minutes / 60
    labels = {"employee_id":"Mã NV","full_name":"Họ và tên","company":"Công ty","department":"Bộ phận","gross_pay":"Lương tháng chuẩn","base_hourly_rate":"Đơn giá/giờ","regular_hours":"Giờ thường","regular_pay":"Lương giờ thường","overtime_hours":"Giờ tăng ca","overtime_hourly_rate":"Đơn giá OT/giờ","overtime_pay":"Tiền tăng ca","final_payable":"Tổng thực trả","insurance_salary":"Lương cơ bản","bonus_pool":"Tổng thưởng","employee_insurance":"BH nhân viên","employer_insurance":"BH doanh nghiệp","shift_count":"Số ca","late_count":"Lần muộn","late_minutes":"Phút muộn","early_count":"Lần về sớm","early_minutes":"Phút về sớm","absent_count":"Vắng"}
    display = display.rename(columns=labels)
    for column in ["Lương tháng chuẩn","Đơn giá/giờ","Lương giờ thường","Đơn giá OT/giờ","Tiền tăng ca","Tổng thực trả","Lương cơ bản","Tổng thưởng","BH nhân viên","BH doanh nghiệp"]:
        if column in display: display[column] = display[column].map(money)
    st.dataframe(display, hide_index=True, width="stretch")
    excel_rows = filtered.to_dict("records")
    st.download_button("Tải bảng lương Excel", payroll_excel(excel_rows), f"bang_luong_{period}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    selected_id = st.selectbox("Xuất phiếu lương cá nhân", filtered.employee_id.tolist()); selected_row = filtered[filtered.employee_id == selected_id].iloc[0].to_dict()
    st.download_button("Tải phiếu lương PDF", payslip_pdf(selected_row, period), f"phieu_luong_{selected_id}_{period}.pdf", "application/pdf")


def render_history(repository):
    header("Lịch sử và so sánh", "Theo dõi biến động chi phí lương và tình hình chấm công giữa các tháng.", "Phân tích xu hướng")
    all_data = repository.summary_frame()
    if all_data.empty:
        empty("Chưa đủ dữ liệu lịch sử", "Sau khi xử lý nhiều kỳ, xu hướng và so sánh sẽ xuất hiện tại đây."); return
    monthly = all_data.groupby("period", as_index=False).agg(Tổng_cần_trả=("final_payable","sum"), Lương_phân_bổ=("gross_pay","sum"), Tiền_tăng_ca=("overtime_pay","sum"), Giờ_tăng_ca=("overtime_hours","sum"), Giờ_thường=("regular_hours","sum"), Nhân_viên=("employee_id","nunique")).sort_values("period")
    fig = go.Figure(); fig.add_trace(go.Scatter(x=monthly.period, y=monthly["Tổng_cần_trả"], mode="lines+markers", name="Tổng cần trả", line=dict(color="#176B5B",width=3))); fig.add_trace(go.Bar(x=monthly.period, y=monthly["Tiền_tăng_ca"], name="Tiền tăng ca", marker_color="#D97706", opacity=.8)); polish_chart(fig, "Xu hướng tổng chi trả và tăng ca theo tháng")
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    display = monthly.rename(columns={"period":"Kỳ","Tổng_cần_trả":"Tổng cần trả","Lương_phân_bổ":"Lương phân bổ","Tiền_tăng_ca":"Tiền tăng ca","Giờ_tăng_ca":"Giờ tăng ca","Giờ_thường":"Giờ thường","Nhân_viên":"Nhân viên"})
    for column in ["Tổng cần trả","Lương phân bổ","Tiền tăng ca"]: display[column] = display[column].map(money)
    st.dataframe(display, hide_index=True, width="stretch")
    if len(monthly) < 2: st.info("Hiện mới có một kỳ. Hệ thống sẽ tự so sánh khi có dữ liệu tháng tiếp theo.")


def render_template(repository, user):
    header("Phân bổ lương chuẩn", "Cấu hình lương nền được dùng lại mỗi tháng và chỉ cập nhật khi chính sách thay đổi.", "Thiết lập nghiệp vụ")
    history = repository.template_history()
    if not history.empty: st.dataframe(history, hide_index=True, width="stretch")
    with st.form("template_upload"):
        c1, c2 = st.columns([1, 2]); effective = c1.date_input("Hiệu lực từ tháng", value=date.today().replace(day=1)); uploaded = c2.file_uploader("File phân bổ lương XLSX", type=["xlsx"]); submitted = st.form_submit_button("Đọc file phân bổ", type="primary")
    if submitted and uploaded:
        try: st.session_state["pending_template"] = {"frame": read_authoritative_payroll(uploaded), "effective": effective.strftime("%Y-%m")}
        except Exception as exc: st.error(f"Không thể đọc file phân bổ lương: {exc}")
    pending = st.session_state.get("pending_template")
    if pending:
        frame = pending["frame"]; cols = st.columns(4); cols[0].metric("Nhân viên", len(frame)); cols[1].metric("Tổng lương", money(total(frame,"gross_pay"))); cols[2].metric("BH nhân viên", money(total(frame,"employee_insurance"))); cols[3].metric("BH doanh nghiệp", money(total(frame,"employer_insurance")))
        st.dataframe(frame, hide_index=True, width="stretch"); st.warning("Khi xác nhận, cấu hình mới sẽ có hiệu lực từ tháng đã chọn. Lịch sử cũ vẫn được giữ nguyên.")
        if st.button("Xác nhận cập nhật phân bổ lương", type="primary"):
            repository.save_payroll_template(frame, pending["effective"], user["username"]); st.session_state.pop("pending_template", None); st.success("Đã cập nhật phân bổ lương chuẩn."); st.rerun()


def render_admin(repository, user):
    header("Quản trị hệ thống", "Quản lý tài khoản, kiểm tra kết nối dữ liệu và xem nhật ký hoạt động.", "Cấu hình bảo mật")
    tab1, tab2, tab3 = st.tabs(["Tài khoản", "Nhật ký", "Trạng thái hệ thống"])
    with tab1:
        users = repository.user_frame()
        if not users.empty: st.dataframe(users.rename(columns={"username":"Tên đăng nhập","display_name":"Họ và tên","role":"Vai trò","active":"Đang hoạt động","created_at":"Ngày tạo"}), hide_index=True, width="stretch")
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3); username = c1.text_input("Tên đăng nhập mới"); display_name = c2.text_input("Họ và tên"); role = c3.selectbox("Vai trò", ["viewer", "admin"], format_func=lambda x: "Người xem" if x == "viewer" else "Quản trị viên"); password = st.text_input("Mật khẩu tạm thời", type="password")
            if st.form_submit_button("Tạo hoặc cập nhật tài khoản"):
                if len(username.strip()) < 3 or len(display_name.strip()) < 2 or len(password) < 10: st.error("Tên đăng nhập, họ tên hoặc mật khẩu chưa đạt yêu cầu. Mật khẩu cần ít nhất 10 ký tự.")
                else: repository.save_user(username.strip(), display_name.strip(), hash_password(password), role, user["username"]); st.success("Đã lưu tài khoản."); st.rerun()
    with tab2: st.dataframe(repository.audit_frame().rename(columns={"event_time":"Thời gian","actor":"Người thao tác","action":"Hành động","entity_type":"Đối tượng","entity_id":"Mã","details":"Chi tiết"}), hide_index=True, width="stretch")
    with tab3:
        database_type = "PostgreSQL đám mây" if repository.database_url.startswith("postgres") else "SQLite cục bộ"; st.metric("Kho dữ liệu", database_type)
        if database_type == "SQLite cục bộ": st.warning("Chế độ này phù hợp trên máy Mac. Trước khi publish, cần cấu hình DATABASE_URL để lịch sử không bị mất khi máy chủ khởi động lại.")
        else: st.success("Ứng dụng đang dùng kho dữ liệu bền vững phù hợp cho bản web.")


def attendance_quality_issues(frame):
    issues = []
    for employee_id, rows in frame.groupby(frame.employee_id.astype(str)):
        explicit = rows.get("needs_review", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.strip(); statuses = rows.get("attendance_status", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.lower(); count = int((explicit.ne("") | statuses.ne("bình thường")).sum())
        if count: issues.append({"code":"ATTENDANCE_REVIEW","severity":"Cảnh báo","row":None,"employee_id":employee_id,"message":f"Có {count} ca muộn, về sớm, vắng mặt hoặc cần kiểm tra."})
    return issues


def attendance_preview(frame):
    data = []
    for employee_id, rows in frame.groupby(frame.employee_id.astype(str)):
        statuses = rows.get("attendance_status", pd.Series(index=rows.index, dtype=object)).fillna("").astype(str).str.lower()
        tracked = pd.to_numeric(rows.get("tracked_minutes", pd.Series(index=rows.index, dtype=float)), errors="coerce").fillna(0).sum()
        data.append({"Mã NV":employee_id,"Họ và tên":rows.full_name.dropna().iloc[0] if rows.full_name.notna().any() else "","Số ca":len(rows),"Bình thường":int(statuses.eq("bình thường").sum()),"Muộn":int(statuses.str.contains("muộn").sum()),"Về sớm":int(statuses.str.contains("về sớm").sum()),"Vắng mặt":int(statuses.str.contains("vắng mặt").sum()),"Tổng giờ":round(tracked/60,1)})
    return pd.DataFrame(data)


def infer_period(frame):
    if "work_date" not in frame or frame.work_date.dropna().empty: return None
    return pd.to_datetime(frame.work_date.dropna().iloc[0]).strftime("%Y-%m")


def header(title, subtitle, kicker):
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True); st.title(title); st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def dashboard_hero(period, status, updated_at):
    st.markdown(
        f'<section class="dashboard-hero"><div class="hero-copy"><div class="hero-eyebrow">HHP + SBC · TRUNG TÂM ĐIỀU HÀNH</div><h1>Lương &amp; nhân sự</h1><p>Chi phí, giờ công và các điểm cần xử lý trong một góc nhìn thống nhất.</p><div class="hero-meta"><span class="hero-tag">{period_label(period)}</span><span class="hero-tag">{status}</span><span class="hero-tag">Cập nhật {updated_at}</span></div></div></section>',
        unsafe_allow_html=True,
    )


def empty(title, message): st.markdown(f'<div class="empty-state"><b>{title}</b><br>{message}</div>', unsafe_allow_html=True)


def total(frame, column): return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum()) if column in frame else 0.0


def money(value): return f"{float(value or 0):,.0f} ₫".replace(",", ".")


def compact_money(value):
    value = float(value or 0)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} tr".replace(".", ",")
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f} nghìn"
    return f"{value:,.0f} ₫".replace(",", ".")


def employee_chart_label(row):
    words = str(row.get("full_name", "")).split()
    short_name = " ".join(words[-2:]) if words else "Chưa rõ"
    return f"{str(row.get('employee_id', '')).zfill(2)} · {short_name}"


def hours(value):
    formatted = f"{float(value or 0):,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted} giờ"


def period_label(period):
    try: year, month = str(period).split("-"); return f"Tháng {month}/{year}"
    except ValueError: return str(period)


def format_datetime(value):
    if value is None or pd.isna(value): return "Chưa rõ"
    if isinstance(value, str): value = datetime.fromisoformat(value)
    return value.strftime("%d/%m/%Y %H:%M")


def previous_available_period(periods, period):
    if periods.empty: return None
    ordered = sorted(periods.period.tolist())
    if period not in ordered: return None
    index = ordered.index(period); return ordered[index - 1] if index > 0 else None


def percentage_delta(current, previous):
    if previous in (None, 0): return None
    return f"{(current - previous) / previous:+.1%} so với tháng trước"


def polish_chart(fig, title, show_legend=True, height=350):
    fig.update_layout(title=dict(text=title, font=dict(size=15, color="#20231F")), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", margin=dict(l=20,r=20,t=58,b=20), height=height, font=dict(family="Arial", color="#626A5F"), legend=dict(orientation="h", y=1.08, x=1, xanchor="right", yanchor="bottom"), showlegend=show_legend, hoverlabel=dict(bgcolor="#20231F",font_color="#FFFFFF"))
    fig.update_xaxes(showgrid=True, gridcolor="#EBEEE8", zeroline=False, title=None, tickformat=","); fig.update_yaxes(showgrid=False, zeroline=False, title=None, automargin=True)


if __name__ == "__main__": main()
