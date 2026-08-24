# Triển khai GitHub và Streamlit Community Cloud

## Kiến trúc

GitHub là nơi lưu mã nguồn, không phải nơi lưu dữ liệu lương. Streamlit Community Cloud đọc mã nguồn từ repository và cung cấp URL website. PostgreSQL/Supabase giữ dữ liệu nghiệp vụ để lịch sử không mất khi ứng dụng khởi động lại.

Nguồn tham khảo:

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app

## 1. Tạo repository riêng tư

Tạo repository mới trên GitHub ở chế độ `Private`. Không tải các file dữ liệu thật lên giao diện GitHub. Kiểm tra `git status` trước mỗi lần push; không được thấy `.xlsx`, `.csv`, `.pdf`, `.sqlite3`, `.env` hoặc `secrets.toml`.

## 2. Tạo PostgreSQL

Tạo một database PostgreSQL/Supabase dành riêng cho ứng dụng. Bật SSL, dùng mật khẩu mạnh và giới hạn người có quyền truy cập. Lấy chuỗi kết nối theo mẫu:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Không ghi chuỗi này vào source code hoặc commit lên GitHub.

## 3. Kết nối Streamlit với GitHub

Đăng nhập https://share.streamlit.io bằng GitHub, cấp quyền cho repository riêng tư và chọn `Create app`. Cấu hình:

- Repository: repository vừa tạo.
- Branch: `main`.
- Main file path: `streamlit_app.py`.
- Python: 3.12.

Trong `Advanced settings > Secrets`, nhập:

```toml
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
SESSION_SECRET = "CHUOI_NGAU_NHIEN_DAI"
```

## 4. Quyền xem

Giữ ứng dụng ở chế độ riêng tư và mời email của sếp làm viewer. Trong ứng dụng, tạo tài khoản `Người xem` cho sếp; tài khoản này chỉ thấy dashboard, bảng lương và lịch sử, không thể nhập hoặc sửa dữ liệu.

## 5. Khởi tạo dữ liệu

1. Đăng nhập lần đầu và tạo tài khoản quản trị.
2. Vào `Phân bổ lương chuẩn`, tải file phân bổ hiện hành và chọn tháng hiệu lực.
3. Vào `Xử lý chấm công tháng`, tải bảng chấm công.
4. Kiểm tra dashboard và tạo tài khoản người xem cho sếp.

## 6. Cập nhật ứng dụng

Mỗi lần push mã nguồn lên nhánh `main`, GitHub Actions chạy kiểm thử. Streamlit Community Cloud tự triển khai lại sau khi mã nguồn được cập nhật. Dữ liệu trong PostgreSQL không bị thay đổi bởi việc deploy code.

## Kiểm tra trước khi dùng thật

- Repository và website đều ở chế độ riêng tư.
- `DATABASE_URL` chỉ tồn tại trong Streamlit Secrets.
- Sếp dùng vai trò người xem.
- Có sao lưu định kỳ cho PostgreSQL.
- Không có file dữ liệu thật trong GitHub.
- Thử khởi động lại ứng dụng và xác nhận lịch sử tháng vẫn còn.

