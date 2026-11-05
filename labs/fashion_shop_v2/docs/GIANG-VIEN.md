# Hướng dẫn giảng viên · Fashion Shop V2

Tài liệu nội bộ: chứa vị trí flag, tình huống khai thác và cách bật bản vá. Không phát cùng tài liệu thí sinh.

## Tình huống và flag

Mỗi đội có state riêng tại `/var/lib/meko-boutique/state.json`; flag dạng `FLAG{32-hex}` đổi sau mỗi tick (mặc định 120 giây). State, khóa phiên và bí mật JWT giữ nguyên qua restart. Dữ liệu challenge giả lập trong SQLite và tệp thiết kế được đồng bộ theo tick.

| Nhóm | Câu chuyện nghiệp vụ | Flag đặt ở runtime | Kiểm tra lab | Bản vá |
|---|---|---|---|---|
| SQL Injection | Nhân viên tạo bộ lọc từ tên bộ sưu tập | `collection_notes.secret` trong `shop.sqlite3` | GET `/collections/search?q=...`; UNION SELECT trong cùng truy vấn bộ sưu tập | `patches.json`: `sqli=true`; query có placeholder tham số |
| IDOR | Hóa đơn thử nghiệm của khách hàng khác dùng ID đoán được | `orders.memo` của đơn giả lập 9001 | Tạo tài khoản rồi mở `/account/orders/9001/invoice` | `idor=true`; so sánh `orders.user_id` với người dùng đăng nhập |
| Upload | Preview JSON của bộ phối trỏ ra ngoài thư mục thiết kế nhưng chỉ trong dữ liệu mô phỏng | `/var/lib/meko-boutique/simulation/private-collection.txt` | Đăng nhập, POST JSON `preview_file=../private-collection.txt` tới `/outfits/new` | `upload=true`; chỉ cho phép resolve trong `simulation/designs` |
| JWT | Cổng ưu đãi tin claim `rank` do token trình duyệt cung cấp | `state.json` → `flags.jwt`, hiện ở `/member/benefits` | Đăng nhập, thay cookie `meko_member` bằng JWT `alg=none`, claim `sub` đúng user và `rank=c-nocturne` | `jwt=true`; chỉ HS256 với chữ ký hợp lệ, kiểm tra `sub`, `exp` |
| Backup | Bản đối soát vận hành bị xuất qua HTTP công khai | Nội dung response `/exports/operations.sql` | GET trực tiếp đường dẫn export | `backup=true`; gỡ export khỏi web và yêu cầu xác thực/quyền vận hành |

**Upload containment:** mọi đường dẫn được resolve và kiểm tra nằm dưới `/var/lib/meko-boutique/simulation`. Không có route mở file tùy ý và không thực thi file upload; payload không thể đọc file hệ thống host.

## Đặt bản vá

Tạo `/var/lib/meko-boutique/patches.json` với owner `meko-web:meko-web`, mode `0600`, sau đó restart:

```json
{"sqli":true,"idor":true,"upload":true,"jwt":true,"backup":true}
```

Local: đặt file trong thư mục `MEKO_DATA`. Bản vá ở ngoài source và tồn tại qua thay đổi tick/restart. `patches.json` được đọc lúc khởi tạo tiến trình; cần restart sau khi sửa.

## Quy trình khai thác để tái hiện

1. SQLi: dùng dấu nháy để kiểm tra truy vấn bộ sưu tập, sau đó UNION lấy `secret` từ `collection_notes`.
2. IDOR: đăng ký/đăng nhập tài khoản A, đổi số đơn trong đường dẫn hóa đơn sang `9001`; ghi chú giao nhận chứa flag.
3. Upload: upload JSON có trường `preview_file` là `../private-collection.txt`; preview trả nội dung bản thiết kế giả lập.
4. JWT: giữ cookie session đăng nhập; tạo token header `{"alg":"none"}`, payload `{"sub":"<ID tài khoản>","rank":"c-nocturne","exp":<thời gian tương lai>}` và chữ ký rỗng; đặt vào cookie `meko_member`.
5. Backup: đọc `/exports/operations.sql`; flag nằm trong dòng INSERT giả lập.

Các bước chỉ nhằm kiểm tra sandbox độc lập. Khi vá, xác nhận chức năng mua hợp lệ vẫn chạy.

## Checker và tích hợp chấm

`sandbox/checker/check.py URL --key KEY --team team1` kiểm tra `/health`. `--task TASK` đọc flag, còn `--put FLAG` ghi flag hiện hành qua `GET/PUT /api/checker/flag/<task>`. API yêu cầu `X-Checker-Key`; provisioning tạo khóa bền vững tại `/etc/meko-boutique/checker.env`, quyền root 0600. Lấy key qua SSH quản trị, không gửi cho thí sinh.

Checker CLI/API là adapter local. Chưa tích hợp định dạng service-checker, SLA, scoring engine, token cấp phát flag hoặc API của CyberRange/ForcAD. Cần ánh xạ giao diện put/get của nền tảng lớp trước khi chấm tự động.
