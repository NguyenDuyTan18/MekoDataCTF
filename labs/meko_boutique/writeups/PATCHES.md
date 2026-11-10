# Bản vá · Meko Boutique

Mỗi đội vá trên VM của mình tại `/opt/meko-boutique`. Mục tiêu: **chặn khai thác mà vẫn giữ
chức năng hợp lệ**, vì hệ thống chấm (checker) liên tục kiểm tra các luồng bình thường — vá sai
làm hỏng chức năng sẽ khiến service **DOWN** và mất điểm SLA/phòng thủ.

## Cơ chế bản vá: `patches.json`

App đọc một tệp `patches.json` trong thư mục dữ liệu (`/var/lib/meko-boutique`) lúc **khởi tạo
tiến trình**. Mỗi khóa bật một nhánh code an toàn đã có sẵn trong
[`sandbox/app/app.py`](../sandbox/app/app.py) qua hàm `patched(task)`:

```json
{"sqli": true, "idor": true, "upload": true, "jwt": true, "backup": true}
```

- Bản vá nằm **ngoài** mã nguồn, **bền vững qua restart** (dữ liệu giữ trong `/var/lib/meko-boutique`).
- Phải **restart** service sau khi sửa `patches.json` thì mới có hiệu lực.

### Bật trên VM đội (production)

```bash
sudo install -o meko-web -g meko-web -m 0600 /dev/stdin /var/lib/meko-boutique/patches.json <<'EOF'
{"sqli": true, "idor": true, "upload": true, "jwt": true, "backup": true}
EOF
sudo systemctl restart meko-boutique
```

### Bật khi chạy thử cục bộ (dev)

Đặt `patches.json` vào thư mục trỏ bởi biến môi trường `MEKO_DATA`, rồi khởi động lại tiến trình app.

> Có thể bật **từng lỗ hổng một** (vd chỉ `{"idor": true}`) để vá dần và kiểm thử riêng từng cái.

## Tóm tắt từng bản vá

| Lỗ hổng | Khóa | Nhánh an toàn được bật | Hành vi sau vá |
|---------|------|------------------------|----------------|
| SQLi    | `sqli`   | Truy vấn tham số hóa `WHERE title LIKE ?` | Chuỗi nhập chỉ là dữ liệu; UNION vô hiệu |
| IDOR    | `idor`   | So `orders.user_id` với `session["uid"]` | Khác chủ đơn ⇒ **403** |
| Upload  | `upload` | Bắt buộc `target.is_relative_to(simulation/designs)` | `preview_file` thoát `designs/` ⇒ **400** |
| JWT     | `jwt`    | Nhánh `alg=none` luôn False; chỉ nhận HS256 ký đúng | Token rèn ⇒ `/member/*` **403** |
| Backup  | `backup` | Yêu cầu phiên nhân viên cho `/exports/operations.sql` | Khách ⇒ **404**; nhân viên vẫn tải được |

Chi tiết từng lỗ hổng và mã nguồn liên quan: xem các writeup khai thác
[01-sqli](01-sqli.md) · [02-idor](02-idor.md) · [03-upload](03-upload.md) ·
[04-jwt](04-jwt.md) · [05-backup](05-backup.md).

**Writeup vá chi tiết** (vá thẳng mã nguồn + diff, vì sao an toàn, sai lầm làm service DOWN, kiểm
chứng từng cái): [patches/](patches/) —
[01](patches/01-sqli.md) · [02](patches/02-idor.md) · [03](patches/03-upload.md) ·
[04](patches/04-jwt.md) · [05](patches/05-backup.md).

## Kiểm chứng sau khi vá (checklist)

Sau khi bật `patches.json` và restart, chạy lại bộ khai thác — kỳ vọng **0 flag**:

```bash
cd exploits
python exploit_all.py http://127.0.0.1    # hoặc địa chỉ service của bạn
```

Đồng thời xác nhận **chức năng hợp lệ vẫn chạy** (nếu không, checker DOWN):

- `GET /health` → 200, JSON `status=ok`.
- Đăng ký → đăng nhập → thêm giỏ → `/checkout` → xem **hóa đơn của chính mình** → 200.
- Tìm bộ sưu tập theo tên thật → trả đúng kết quả.
- Upload manifest hợp lệ (`preview_file: "lookbook.txt"`) → 200, hiện preview.
- Nhân viên `/staff/login` → tải `/exports/operations.sql` → 200.
- Hội viên được cấp hạng (token HS256 thật) → vào `/member/benefits` → 200.

> **Kết quả đã kiểm chứng (local):** bật cả 5 khóa ⇒ cả 5 khai thác trả 0 flag, trong khi mọi
> luồng hợp lệ ở trên vẫn 200. Xem bảng trong [README.md](README.md#đã-kiểm-chứng).

## Lưu ý vận hành

- `patches.json` nên thuộc `meko-web:meko-web`, mode `0600`.
- Vá là **cấu hình cộng với nhánh code có sẵn**, không cần sửa trực tiếp `app.py`. Nếu muốn tự
  viết bản vá riêng trong mã nguồn, giữ nguyên tinh thần: **chặn đúng đường tấn công, không phá
  luồng hợp lệ mà checker kiểm tra**.
- Mật khẩu nhân viên website của từng đội nằm ở `/etc/meko-boutique/staff.env` trên VM đội
  (dùng cho `/staff/login`, cần cho việc kiểm thử luồng Backup/JWT sau vá).
