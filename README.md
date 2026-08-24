# Quản trị lương HHP + SBC

Ứng dụng web nội bộ bằng tiếng Việt dành cho kế toán và cấp quản lý. Phân bổ lương được thiết lập theo ngày hiệu lực; hằng tháng người vận hành chỉ cần tải bảng chấm công, kiểm tra ngoại lệ và phê duyệt kỳ lương.

## Chức năng chính

- Dashboard điều hành: tổng tiền cần trả, giờ thường, giờ tăng ca, tiền tăng ca và tình hình đi muộn/về sớm.
- Phân bổ lương chuẩn dùng lại qua nhiều tháng và giữ lịch sử thay đổi.
- Nhập bảng chấm công XLSX/CSV, ghép bằng mã nhân viên và kiểm tra tên.
- Danh sách ngoại lệ, lý do xử lý, trạng thái phê duyệt và khóa kỳ.
- Bảng lương chi tiết, xuất Excel và phiếu lương PDF từng nhân viên.
- Lịch sử và so sánh chi phí giữa các tháng.
- Đăng nhập, vai trò quản trị viên/người xem và nhật ký hoạt động.
- SQLite cho máy Mac; PostgreSQL cho bản web dài hạn.

## Chạy trên macOS

```bash
chmod +x scripts/run.command
./scripts/run.command
```

Mở `http://localhost:8501`. Lần đầu sử dụng, ứng dụng yêu cầu tạo tài khoản quản trị; mật khẩu được lưu dưới dạng PBKDF2-SHA256, không lưu văn bản thuần.

## Quy trình hằng tháng

1. Quản trị viên đăng nhập và chọn `Xử lý chấm công tháng`.
2. Chọn kỳ, tải file chấm công và bấm `Đọc và đối chiếu dữ liệu`.
3. Kiểm tra ID, tên, số dòng và các ca cần kiểm tra.
4. Bấm `Xác nhận lưu kỳ lương`.
5. Xử lý ngoại lệ trong `Kiểm tra và phê duyệt`.
6. Chuyển trạng thái sang `Đã phê duyệt` rồi `Đã khóa`.
7. Sếp vào `Tổng quan điều hành`; kế toán xuất báo cáo tại `Bảng lương nhân viên`.

Chỉ vào `Phân bổ lương chuẩn` khi có thay đổi mức lương, thưởng, phụ cấp hoặc bảo hiểm. Cấu hình cũ không bị ghi đè.

Ứng dụng giữ nguyên tổng lương tháng đã xác nhận làm cơ sở tính đơn giá. Đơn giá giờ của từng người bằng tổng lương tháng chia 192 giờ. Giờ thường được tính trong hai ca 07:30–11:30 và 13:00–17:00; thời gian nghỉ trưa 11:30–13:00 không được tính. Phần làm việc sau 17:00 là tăng ca và được trả theo đơn giá giờ nhân 1,5. Đi muộn, về sớm và vắng mặt được hiển thị để quản lý.

## Publish an toàn

GitHub chỉ lưu mã nguồn. Các file XLSX/CSV/PDF, database, file xuất và secrets đều bị `.gitignore` loại khỏi repository.

Kiến trúc khuyến nghị:

- GitHub repository riêng tư: lưu mã nguồn và chạy kiểm thử tự động.
- Streamlit Community Cloud: cung cấp URL riêng cho ứng dụng và tự triển khai lại khi mã nguồn thay đổi.
- PostgreSQL/Supabase: lưu dữ liệu lâu dài qua biến bí mật `DATABASE_URL`.
- Streamlit secrets: giữ chuỗi kết nối ngoài GitHub.

Không dùng SQLite trên Streamlit Community Cloud cho dữ liệu cần lưu lâu dài vì filesystem của máy chủ có thể bị tạo lại khi reboot hoặc redeploy.

Xem [hướng dẫn triển khai](docs/TRIEN_KHAI_GITHUB_STREAMLIT.md) và mẫu [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example).

## Kiểm thử

```bash
.venv/bin/python -m pytest -q
```

GitHub Actions tự chạy kiểm thử sau mỗi lần push lên nhánh `main`.
