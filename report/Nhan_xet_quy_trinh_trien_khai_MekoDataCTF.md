# Nhận xét quy trình triển khai MekoDataCTF

Tài liệu được nhận xét: bản PowerPoint 11 slide do người dùng cung cấp. Bản bổ sung gồm 25 slide, giữ thiết kế Đại học Cần Thơ và sơ đồ 12 bước, mở rộng nội dung theo thao tác triển khai. Đây là nhận xét tài liệu và đề xuất quy trình, không phải biên bản nghiệm thu hệ thống đang chạy.

## Những điểm đã tốt

- Sơ đồ slide 3 bao quát từ chốt đội, chuẩn bị bài, tạo môi trường đến tích hợp và mở thi.
- Có phân biệt pool/sandbox với số VM đội, tránh nhầm quy mô cấp phát.
- Có tách quyền ban tổ chức và thí sinh, phân biệt token Training với token đội.
- Slide 8 đã có nhánh nghiệm thu đạt/chưa đạt và yêu cầu kiểm tra toàn bộ luồng.
- Có phân loại tái sử dụng và phân biệt bật lại một hệ thống đã cài với chuẩn bị môi trường mới.

## Phần còn thiếu hoặc cần làm rõ

| Nội dung | Hiện trạng trong bản gốc | Bổ sung/điều chỉnh |
|---|---|---|
| Phạm vi và điều kiện đầu vào | Sơ đồ bắt đầu từ chốt đội | Xác nhận cloud/Portal đã có, quyền cấp phát, image, tài nguyên và công cụ máy vận hành |
| Cài website lần đầu | Chỉ có thao tác bật lại ở slide 10 | Cài thành phần phụ thuộc, thiết lập tài khoản/địa chỉ, khởi tạo lần đầu, thử truy cập từ máy thí sinh |
| Cài ForcAD lần đầu | Chưa có slide riêng | Chuẩn bị gói engine, cấu hình, khởi tạo, khởi động và kiểm tra dashboard/API |
| Một ô quy trình có một slide chi tiết | Slide 4 gộp bước 1–3, slide 5 gộp bước 4–7; các bước sau còn phân tán | Tách 12 slide tương ứng 12 ô, giữ số bước thống nhất |
| Thao tác và điều kiện hoàn thành | Nhiều mô tả mới dừng ở tên công việc | Mỗi slide có đầu vào, bốn thao tác và điều kiện hoàn thành cụ thể |
| Cấu hình ForcAD/collector | Slide 6 chủ yếu mô tả luồng kết nối | Nêu việc chọn bài, kiểm tra task/đội, chọn môi trường collector và thử phản hồi checker |
| Ghép đội/đồng bộ token | Chưa có slide thao tác riêng | Đối chiếu tên kỹ thuật, IP/VM và trạng thái đồng bộ của từng đội |
| Training | Slide 7 trình bày gán pool trước Training Instance | Làm rõ tạo/chọn Definition, tạo Instance rồi gán pool/thời gian; thử bằng tài khoản thí sinh |
| Nghiệm thu cuối | Thi thử ở bước 10 trước Training bước 11 dễ bị hiểu là đã nghiệm thu xong | Phân biệt thi thử kỹ thuật với kiểm tra quyền/luồng sử dụng cuối sau khi cấp Training |
| Mở thi | Có nhắc dữ liệu sạch nhưng chưa tách lớp trạng thái | Lưu thi thử, chuẩn bị dữ liệu đầu, kiểm tra các lịch và quan sát tick đầu |
| Vận hành trong khi thi | Chưa có slide riêng | Theo dõi tick/checker/điểm, phân loại lỗi, ghi nhận sự cố và kiểm tra trước khi tiếp tục |
| Kết thúc và phục hồi | Chưa có slide riêng | Chốt nhận flag, lưu kết quả/log/dữ liệu, thu hồi quyền và khôi phục cho lượt tiếp |

Lưu ý về Training: trong mô hình cloud tiêu chuẩn, một Training Run nhận một sandbox. Nếu một sandbox chứa nhiều VM đội thì cần chốt cách tổ chức quyền/run trước, tránh vô tình cấp cho mỗi đội một bản sao toàn bộ sân đấu. Việc dùng tài khoản Portal chung không tự tạo ranh giới quyền theo đội.

## Đối chiếu ô tổng thể và slide chi tiết trong bản bổ sung

Sơ đồ tổng thể nằm ở slide 7. Mỗi ô có đúng một slide chi tiết:

| Ô | Nội dung | Slide chi tiết |
|---:|---|---:|
| 1 | Chốt đội | 8 |
| 2 | Soạn gói bài | 9 |
| 3 | Soạn cấu hình môi trường | 10 |
| 4 | Git và Sandbox Definition | 11 |
| 5 | Tạo pool | 12 |
| 6 | Allocate môi trường | 13 |
| 7 | Lấy truy cập và tách quyền | 14 |
| 8 | Cấu hình ForcAD và collector | 15 |
| 9 | Ghép đội và đồng bộ token | 16 |
| 10 | Thi thử và kiểm tra chấm điểm | 17 |
| 11 | Training và quyền thí sinh | 18 |
| 12 | Mở thi chính thức | 19 |

Các slide hỗ trợ: 3–5 cho điều kiện/cài nền tảng lần đầu; 6 cho kết nối các thành phần; 20–22 cho giám sát, kết thúc và khôi phục; 23–24 cho tái sử dụng và bật lại. Slide 1–2 và 25 là trang bìa, nội dung và cảm ơn.

## Cách trình bày tránh đi vào mã nguồn

Mỗi slide chi tiết trả lời: cần chuẩn bị gì, thao tác trên hệ thống nào, thực hiện theo thứ tự nào và căn cứ nào để chuyển bước. Nội dung không giải thích hàm, lớp, thuật toán lập trình, đường dẫn mã nguồn hoặc đưa đoạn lệnh lên slide.

Khi có minh chứng triển khai thực, nên bổ sung ảnh Portal/dashboard gắn đúng bước: Definition và revision, cấu hình pool, trạng thái allocate/provisioning, quyền VM, kết quả checker, đồng bộ đội và bảng điểm thi thử. Che token, mật khẩu, key và dữ liệu cá nhân trước khi dùng ảnh. Bản bổ sung hiện dùng hướng dẫn thao tác và giữ sơ đồ gốc, không dựng ảnh giao diện hoặc số đo giả.

Trước bảo vệ cần điền các thông tin thực tế: phiên bản gói, quy mô đội/VM, tài nguyên, cấu hình lịch/timeout và kết quả nghiệm thu. Không tự gọi cấu hình là “tối thiểu” hoặc khẳng định hiệu năng khi chưa đo.

## Căn cứ đối chiếu

- Bản PowerPoint gốc, đặc biệt slide 3–10.
- docs/QUY-TRINH-CAI-DAT-TONG-QUAT-BAO-CAO.md và docs/HUONG-DAN-KHOI-DONG.md trong dự án.
- [CyberRangeCZ Pool](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/).
- [CyberRangeCZ Training Instance](https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-instance/).
- [CyberRangeCZ Training Overview](https://docs.platform.cyberrange.cz/user-guide-advanced/trainings/trainings-overview/).
- [CyberRangeCZ Sandbox Access](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/).
