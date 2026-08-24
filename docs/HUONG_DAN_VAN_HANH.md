# Hướng dẫn vận hành và bảo vệ dữ liệu

## Cài đặt và chạy

Yêu cầu macOS có Python 3.12. Chạy `./scripts/run.command`; lần đầu cần kết nối Internet để cài các thư viện miễn phí. Database cục bộ được tạo tại `data/database/payroll.sqlite3`. Bản web dùng PostgreSQL qua `DATABASE_URL`.

## Vận hành lâu dài

Phân bổ lương được nhập một lần tại `Phân bổ lương chuẩn` và tiếp tục có hiệu lực cho các tháng sau. Khi có thay đổi, nhập file mới kèm tháng bắt đầu hiệu lực; hệ thống giữ cấu hình cũ để báo cáo lịch sử không bị thay đổi.

Mỗi tháng chỉ tải file chấm công tại `Xử lý chấm công tháng`. Dashboard được tạo từ số tiền trong phân bổ lương chuẩn và kết quả chấm công của kỳ tương ứng.

## Cập nhật nhân viên và mức lương

Vào `1. Nhân viên`, nhập mã duy nhất, thông tin cá nhân và đơn giá có ngày hiệu lực. Khi tăng lương, giữ nguyên mã nhân viên và thêm mức mới với ngày hiệu lực mới. Không sửa mức cũ để tránh làm sai lịch sử.

## Chuẩn file chấm công

File XLSX/CSV tối thiểu phải có `Mã nhân viên` và `Ngày làm việc`. Nên có `Giờ làm bình thường`, các cột tăng ca, `Giờ ban đêm`, nghỉ hưởng lương/không lương và `Trạng thái phê duyệt tăng ca`. Mã phải khớp danh mục; không dùng họ tên để ghép.

PDF máy chấm công hiện tại chưa được nhập trực tiếp vì thiếu bảng ánh xạ ID máy sang mã nhân viên. Hãy xuất XLSX/CSV từ máy chấm công hoặc bổ sung bảng ánh xạ đã xác nhận.

## Xử lý lỗi

- `MISSING_EMPLOYEE_ID`: bổ sung mã ở dòng được nêu.
- `UNKNOWN_EMPLOYEE`: thêm nhân viên hoặc sửa mã sai.
- `DUPLICATE`: xác định bản ghi đúng; không đánh dấu xử lý nếu chưa loại dòng trùng khỏi nguồn nhập mới.
- `MISSING_PUNCH`: đối chiếu đơn từ/ghi nhận quản lý và bổ sung giờ hợp lệ.
- `OT_NOT_APPROVED`: quản lý duyệt tăng ca; hệ thống không trả khoản này khi chưa duyệt.
- `NO_RATE`: thêm đơn giá có hiệu lực bao phủ ngày làm việc.

Mỗi ngoại lệ phải có lý do xử lý. Không phê duyệt khi còn lỗi nghiêm trọng.

## Cập nhật pháp luật

Sửa `config/payroll_rules.json`: thêm bản ghi mới có ngày bắt đầu hiệu lực, nguồn, đường dẫn, ngày kiểm tra và trạng thái. Không sửa bản ghi lịch sử đang dùng cho kỳ đã khóa. Một chuyên viên kế toán hoặc pháp lý Việt Nam cần xác nhận trước khi đổi sang `Đã xác minh`.

## Sao lưu và khôi phục

Thoát ứng dụng trước khi sao lưu. Sao chép toàn bộ `data/database/` sang ổ được mã hóa, kèm ngày sao lưu. Khôi phục bằng cách đóng ứng dụng, giữ một bản của database hiện tại, rồi đặt bản sao lưu trở lại đúng đường dẫn. Không ghi đè nếu chưa có bản dự phòng.

## Bảo mật

Không chia sẻ thư mục `data/database/` hoặc `exports/` qua kênh công cộng. Chỉ gửi phiếu lương đúng người nhận. Tệp thật đã được `.gitignore`; tuyệt đối không thêm cưỡng bức bằng `git add -f`.
