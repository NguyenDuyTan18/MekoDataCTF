# Hướng dẫn giảng viên · Meko Boutique

Tài liệu nội bộ: chứa câu chuyện nghiệp vụ, vị trí flag, cách khai thác và cách vá.
**Không phát kèm tài liệu thí sinh.**

## Mô hình flag

App không tự sinh hay đổi flag. Hệ thống chấm nạp flag qua chức năng thường của cửa hàng; mỗi flag
là một bản ghi riêng nên nhiều flag cùng còn hiệu lực. Dữ liệu nằm trong `/var/lib/meko-boutique`,
giữ nguyên qua restart. `state.json` chỉ còn `secret` và `jwt_secret`.

## Năm thử thách: câu chuyện, flag, khai thác, vá

| Nhóm | Câu chuyện nghiệp vụ | Flag đặt ở runtime | Khai thác trong lab | Bản vá |
|---|---|---|---|---|
| **SQLi** | Khách lưu **ghi chú riêng** cho bộ sưu tập; ô tìm bộ sưu tập nối chuỗi SQL. | `collection_notes.note` trong `catalog.sqlite3` | `GET /collections/search?q=` với payload UNION | `sqli=true`: dùng truy vấn tham số hóa (placeholder `?`) |
| **IDOR** | Khách xem **hóa đơn** của mình; số đơn đoán được. | `orders.memo` của đơn do khách đặt | Đăng nhập tài khoản khác, mở `/account/orders/<id>/invoice` | `idor=true`: so `orders.user_id` với người đang đăng nhập, khác thì `403` |
| **Upload** | **Studio phối đồ** nhận manifest JSON, có `preview_file` và `stylist_note` riêng. | `simulation/private/<token>.json` | Đăng nhập, POST JSON có `preview_file=../private/<token>.json` tới `/outfits/new` | `upload=true`: chỉ cho resolve trong `simulation/designs` |
| **JWT** | Nhân viên tạo **ưu đãi C-Nocturne** và cấp hạng; khu hội viên đọc hạng từ cookie `meko_member`. | `vip_offers.code`, hiện tại `/member/offers/<id>` | Đặt cookie `meko_member` là JWT `alg=none`, `sub=<id tài khoản>`, `rank=c-nocturne` | `jwt=true`: chỉ chấp nhận HS256 có chữ ký hợp lệ |
| **Backup** | Nhân viên lưu **bản đối soát**; bản xuất bị công khai qua HTTP (gợi ý trong `robots.txt`). | `reconciliation_notes.value`, hiện tại `/exports/operations.sql` | `GET /exports/operations.sql` không cần đăng nhập | `backup=true`: chỉ phiên nhân viên tải được, khách nhận `404` |

`catalog.sqlite3` tách khỏi `shop.sqlite3`, nên SQLi không đọc được đơn hàng, ưu đãi VIP hay bản đối soát.

### Giới hạn vùng upload (quan trọng)

Mọi đường dẫn `preview_file` đều được `resolve()` và **bắt buộc** nằm dưới
`/var/lib/meko-boutique/simulation`. Payload vượt khỏi vùng này (ví dụ `../../../../etc/passwd`)
luôn bị từ chối `400`, **kể cả khi chưa vá**. Không có route đọc tệp tùy ý và không thực thi tệp
tải lên; lỗ hổng chỉ cho đọc trong dữ liệu giả lập, không chạm hệ thống host.

## Quy trình khai thác để tái hiện

1. **SQLi:** `GET /collections/search?q=zzz%' UNION SELECT id, note, user_id FROM collection_notes --`
   — cột thứ hai hiển thị trong tiêu đề bộ sưu tập, chứa ghi chú.
2. **IDOR:** đăng nhập tài khoản A → mở `/account/orders/<id đơn của B>/invoice`; dòng
   "Ghi chú giao nhận" chứa flag.
3. **Upload:** đăng nhập → upload JSON `{"name":"x","preview_file":"../private/<token>.json"}`
   tới `/outfits/new`; bản xem trước trả nội dung tệp riêng chứa `stylist_note`.
4. **JWT:** giữ cookie phiên; tạo token:
   - header `{"alg":"none","typ":"JWT"}`, payload `{"sub":"<ID>","rank":"c-nocturne","exp":<tương lai>}`, chữ ký rỗng;
   - đặt vào cookie `meko_member` rồi mở `/member/offers/<id>`.
5. **Backup:** `GET /exports/operations.sql`; flag nằm trong các dòng `INSERT INTO reconciliation_notes`.

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
tiến trình; cần restart sau khi sửa. Bản vá nằm ngoài source và bền vững qua restart.

## Checker và tích hợp chấm

- `sandbox/checker/check.py URL --team team1` chỉ kiểm tra `/health` và danh tính đội.
- Không còn API đọc/ghi flag riêng. Checker phải đi qua chức năng thường:

| Loại | Nạp flag | Đọc lại hợp lệ |
|---|---|---|
| IDOR | `POST /checkout` với `memo` | Chủ đơn mở `/account/orders/<id>/invoice` |
| SQLi | `POST /account/notes` với `collection_id`, `note` | Chủ ghi chú mở `/account/notes/<id>` |
| Upload | `POST /outfits/new` với `stylist_note` | Chủ bộ phối mở `/outfits/<token>` |
| JWT | Staff `POST /staff/vip` với `code`, `POST /staff/vip/members` với `username` | User VIP đăng nhập lại, mở `/member/offers/<id>` |
| Backup | Staff `POST /staff/reconciliation` với `value` | Staff tải `/exports/operations.sql` |

Checker nằm trong `sandbox/checker/`: `idor.py`, `sqli.py`, `upload.py`, `jwt.py`, `backup.py` theo giao thức ForcAD, `agent.py` cho collector qua SSH. Cấu hình mẫu: `config.example.json`.

## Mật khẩu (cấu hình sẵn trong YAML)

- SSH/console tài khoản đội: `meko_team_passwords` trong `sandbox/provisioning/group_vars/all.yml`
  (mặc định `MekoTeam1@2026`, `MekoTeam2@2026`, `MekoTeam3@2026`).
- Mật khẩu nhân viên website (`/staff/login`): riêng từng đội, là `sha256("<meko_staff_secret>:<team>")`. Lấy trên VM đội tại `/etc/meko-boutique/staff.env` qua SSH quản trị.
- Tài khoản `kali` mặc định của image **bị khóa** (`password_lock`, shell `nologin`).
- Đây là mật khẩu CHỈ DÙNG cho lab cô lập — đổi trước khi dùng ngoài cloud huấn luyện riêng.
