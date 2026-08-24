# Báo cáo khảo sát dữ liệu ngày 22/08/2026

## Tệp hiện có

| Tệp | Cấu trúc | Phát hiện chính |
|---|---|---|
| `PHÂN BỔ LƯƠNG T07-2026.xlsx` | 2 sheet, 16 cột, 17 nhân viên | Hai sheet gần như bản sao; sheet 1 có 22 dòng, sheet 2 có 23 dòng do một dòng trống. |
| `máy chấm công tháng 7.pdf` | 10 trang | Báo cáo chi tiết theo ID máy, tên, bộ phận, ngày, ca sáng/chiều, trạng thái, giờ vào/ra và phút theo dõi. |
| `~$PHÂN BỔ LƯƠNG T07-2026.xlsx` | Tệp khóa Excel | Không phải dữ liệu nghiệp vụ; không xử lý. |

Không có CSV, danh mục nhân viên độc lập, bảng mã ghép, dữ liệu ngân hàng, hồ sơ thuế hoặc thêm hai tháng lịch sử.

## Cấu trúc bảng lương

Các cột chính gồm công ty, họ tên, chức vụ/bộ phận, tổng lương, lương cơ bản đóng bảo hiểm và TNCN, thưởng KPI, thưởng theo doanh số, tiền ăn, điện thoại, xăng xe, chuyên cần, bảo hiểm công ty và bảo hiểm nhân viên.

Có 17 người: 10 thuộc HHP và 7 thuộc SBC. File không có mã nhân viên, ngày hiệu lực mức lương, lương thực nhận, thuế TNCN, số tài khoản, người phụ thuộc hay trạng thái phê duyệt.

## Quy tắc có thể suy ra

- Bảo hiểm phía công ty = lương cơ bản × 21,5%.
- Bảo hiểm phía nhân viên = lương cơ bản × 10,5%.
- Tổng bảo hiểm = hai khoản trên.
- Tổng thưởng cần phân bổ = tổng lương - lương cơ bản - tiền ăn - điện thoại - xăng xe. Cột chuyên cần không được trừ trong công thức này.
- Thưởng theo doanh số = tổng thưởng cần phân bổ - thưởng KPI cá nhân.

Các quy tắc trên chỉ là mô tả công thức trong workbook, chưa chứng minh được chính sách doanh nghiệp hoặc tính đúng pháp lý.

## Chênh lệch và chất lượng dữ liệu

- Hai sheet không thống nhất: Lê Vĩ Hùng có tổng lương 15.000.000 đồng ở sheet đầu nhưng 9.000.000 đồng ở sheet sau; xăng xe tương ứng 2.000.000 và 200.000 đồng.
- Lê Hồng Vương có thưởng KPI 1.000.000 đồng ở sheet đầu nhưng 2.500.000 đồng ở sheet sau.
- Tên `TRẦN XUÂN PHƯỚC` trong Excel xuất hiện là `TRAN XUAN PHUOC` trong PDF; ghép bằng tên có rủi ro.
- PDF chứa trường hợp thiếu chấm vào/ra, vắng mặt, muộn và thời lượng 0 phút. Ví dụ Trương Anh Mẫn thiếu giờ ra ở một số ca ngày 10, 11, 14 và 16/07/2026.
- PDF dùng ID máy chấm công; Excel không có ID tương ứng. Cần bảng ánh xạ ID máy → mã nhân viên trước khi tự động đối chiếu.
- Chỉ có một tháng nên chưa thể đạt yêu cầu đối chiếu tối thiểu ba tháng hoặc phân tích xu hướng 12 tháng.

## Cập nhật ID ngày 23/08/2026

- File `Chấm Công 07-2026.xlsx` có 540 dòng chi tiết và 10 ID duy nhất: 1, 2, 3, 4, 5, 7, 8, 9, 10, 11.
- Sheet `Sheet1` của file phân bổ lương có đúng 10 ID này.
- Không có ID chỉ xuất hiện ở một file; tên khớp 10/10 sau khi chuẩn hóa dấu. `TRAN XUAN PHUOC` trong chấm công khớp ID 11 `TRẦN XUÂN PHƯỚC` trong bảng lương.
- `Sheet1` được xác nhận là nguồn lương chính thức cho nhóm có chấm công. `Sheet1 (2)` là danh sách cũ 17 người với hệ số thứ tự khác và không được dùng để ghép.
- Các số lương, thưởng, phụ cấp và bảo hiểm từ `Sheet1` được nhập nguyên trạng; ứng dụng không tính lại.

## Kết luận nhập liệu

Hai tệp nguồn vẫn ở nguyên vị trí và không bị sửa. Khi người dùng tải cả hai file trong ứng dụng, hệ thống chỉ lưu bản ghi chuẩn hóa vào database cục bộ sau khi ID/tên đối chiếu không còn lỗi nghiêm trọng.
