# Công thức, giả định và nội dung cần xác nhận

## Công thức đang áp dụng

Các khoản lương, thưởng, phụ cấp và bảo hiểm được đọc nguyên trạng từ bảng phân bổ lương đã xác nhận; hệ thống không tính lại các khoản này.

- Giờ chuẩn mỗi ngày = 8 giờ.
- Giờ thường mỗi ngày = thời gian chấm công giao với hai khung 07:30–11:30 và 13:00–17:00.
- Khoảng 11:30–13:00 là nghỉ trưa, không tính vào giờ làm; thời gian đến trước 07:30 cũng không được tính.
- Giờ tăng ca = thời gian làm việc thực tế sau 17:00.
- Tổng giờ chuẩn tháng = 48 giờ/tuần × 4 tuần = 192 giờ.
- Đơn giá giờ = tổng lương tháng đã xác nhận của từng nhân viên / 192 giờ.
- Đơn giá tăng ca = đơn giá giờ × 1,5.
- Tiền tăng ca = tổng giờ tăng ca × đơn giá tăng ca.
- Lương giờ thường = tổng giờ thường thực tế × đơn giá giờ.
- Tổng thực trả = lương giờ thường + tiền tăng ca.

Số lần và số phút đi muộn, về sớm, vắng mặt chỉ phục vụ theo dõi quản lý. Hệ thống chưa tự động trừ lương theo các chỉ số này.

## Chưa xác minh, cần quyết định trước khi dùng thật

Mã nhân viên và sheet nguồn đã được xác nhận ngày 23/08/2026: dùng ID trong `Chấm Công 07-2026.xlsx` và `Sheet1` của `PHÂN BỔ LƯƠNG T07-2026.xlsx`. Các số lương, thưởng, phụ cấp và bảo hiểm trong sheet này không được tính lại.

1. Lịch làm việc: hiện file thể hiện thứ Hai đến thứ Bảy, hai ca 07:30-11:30 và 13:00-17:00; cần xác nhận đây có phải lịch chuẩn cho mọi người không.
2. Cách làm tròn phút công, dung sai đi muộn/về sớm và cách xử lý quẹt thiếu.
3. Cách phân loại tăng ca ngày nghỉ hoặc ngày lễ nếu doanh nghiệp muốn áp dụng hệ số khác 1,5.
4. Hai tháng lịch sử bổ sung để đạt đối chiếu tối thiểu ba tháng.

Các quy tắc tính lương chưa xác minh không chặn kỳ sử dụng bảng phân bổ lương đã xác nhận, vì engine không được áp dụng cho kỳ đó. Lỗi ID hoặc tên không khớp vẫn chặn nhập và phê duyệt.
