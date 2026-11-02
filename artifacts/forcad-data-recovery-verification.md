# Kiểm chứng sửa lỗi dữ liệu ForcAD — 2026-11-02

Nguyên nhân: 5 script trong docker_config dùng CRLF, khiến container báo `/bin/bash: -\r: invalid option`; API trả HTTP 502.

Đã chuyển 5 script sang LF và thêm `.gitattributes` giới hạn shell script trong docker_config dùng LF. Build và khởi động Compose thành công. Initializer kết thúc mã 0. Đăng nhập admin bằng cấu hình hiện tại thành công.

Đã thêm team01–team04 từ labs/round1/lab.json qua Admin API và chuẩn bị Round 1 qua endpoint chính thức. Hai đội và hai task mẫu được chuyển inactive bởi thao tác chuẩn bị; không xóa chúng. Không bắt đầu cuộc thi.

Bằng chứng: `/api/client/teams/` HTTP 200, đúng 4 đội; `/api/client/tasks/` HTTP 200, đúng 3 task IDOR/SQLI/UPLOAD. Admin API xác nhận running=false.

## Tự đánh giá theo agent-self-evaluation

| Tiêu chí | Điểm | Bằng chứng / cải thiện |
|---|---|---|
| Chính xác | 4/5 | Đã kiểm API thực tế và trạng thái container; chưa kiểm trực quan trình duyệt. |
| Đầy đủ | 4/5 | Khắc phục dữ liệu đội/task; kết nối SSH/agent CyberRange vẫn cần kiểm riêng. |
| Rõ ràng | 4/5 | Phản hồi chỉ rõ dữ liệu hiện có và bước refresh; cần kết quả phía người dùng để xác nhận giao diện. |
| Khả năng thực hiện | 5/5 | Đã sửa và xác minh trên hệ thống đang chạy, không chỉ đưa hướng dẫn. |
| Ngắn gọn | 4/5 | Phản hồi cuối ngắn; có nhiều cập nhật trong quá trình xử lý để giải thích lỗi. |

Trung bình: 4.2/5. Không có tiêu chí <=2. Cải thiện tiếp theo: kiểm trực quan trang admin sau refresh và xác minh SSH/collector trước khi bắt đầu thi.

Tự kiểm: người dùng có thể xác minh độc lập bằng cách refresh trang admin. Không tuyên bố đã nối CyberRange hay đã có điểm thi. Kết luận: bàn giao kết quả hiện tại.
