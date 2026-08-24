# Từ điển dữ liệu

## Nhân viên

`employee_id` là khóa chính; `full_name` họ tên; `company` công ty; `department` bộ phận; `job_title` chức danh; `employment_status` trạng thái; `start_date`, `end_date` ngày vào/nghỉ; `standard_schedule` lịch chuẩn; `hours_per_day`, `hours_per_week` giờ chuẩn; `insurance_salary` căn cứ bảo hiểm; ba cờ bảo hiểm; `tax_id`; `tax_residency`; `dependents`; `bank_account`; `bank_name`; `notes`.

## Chấm công chuẩn hóa

`employee_id`, `work_date`, `check_in`, `check_out`, `break_minutes`, `regular_hours`, `ot_weekday_hours`, `ot_weekend_hours`, `ot_holiday_hours`, `night_hours`, `night_ot_hours`, `paid_leave_hours`, `unpaid_leave_hours`, `late_minutes`, `early_minutes`, `ot_approved`, `adjustment_note`.

## Kết quả lương

`gross_pay` là tổng lương tháng chuẩn; `base_hourly_rate` = `gross_pay / 192`; `regular_minutes` và `regular_hours` là thời gian thực tế trong hai ca chuẩn; `overtime_minutes` và `overtime_hours` là thời gian sau 17:00; `regular_pay`, `overtime_pay` và `final_payable` lần lượt là lương giờ thường, tiền tăng ca và tổng thực trả.

## Trạng thái

Kỳ lương đi theo thứ tự: Bản nháp, Đang kiểm tra, Chờ phê duyệt, Đã phê duyệt, Đã khóa, Đã thanh toán. Khoản điều chỉnh dùng Chờ duyệt hoặc Đã duyệt. Ngoại lệ dùng mức Nghiêm trọng hoặc Cảnh báo và cờ đã xử lý.
