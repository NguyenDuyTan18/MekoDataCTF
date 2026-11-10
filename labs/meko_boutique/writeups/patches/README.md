# Writeup bản vá chi tiết · Meko Boutique

> ⚠️ **NỘI BỘ (giảng viên/đội phòng thủ).** Hướng dẫn vá từng lỗ hổng theo hướng phòng thủ.

Khác với [../PATCHES.md](../PATCHES.md) (bảng tóm tắt + cách bật `patches.json`), các file ở đây
đi **sâu từng lỗ hổng**: nguyên tắc vá, **hai cách vá** (bật cờ sẵn có *hoặc* sửa thẳng mã nguồn),
phân tích vì sao an toàn, **các sai lầm làm service DOWN**, và cách kiểm chứng.

| # | Lỗ hổng | Writeup vá | Khóa `patches.json` |
|---|---------|-----------|---------------------|
| 1 | SQL Injection | [01-sqli.md](01-sqli.md) | `sqli` |
| 2 | IDOR | [02-idor.md](02-idor.md) | `idor` |
| 3 | Path Traversal (upload) | [03-upload.md](03-upload.md) | `upload` |
| 4 | JWT `alg=none` | [04-jwt.md](04-jwt.md) | `jwt` |
| 5 | Lộ bản backup | [05-backup.md](05-backup.md) | `backup` |

## Hai cách vá — chọn một

**Cách A · Bật `patches.json` (khuyến nghị khi thi).** Nhanh, không chạm mã nguồn, bền qua
restart. Mỗi khóa bật một nhánh code an toàn đã viết sẵn trong
[`sandbox/app/app.py`](../../sandbox/app/app.py).

```bash
sudo install -o meko-web -g meko-web -m 0600 /dev/stdin /var/lib/meko-boutique/patches.json <<'EOF'
{"sqli": true, "idor": true, "upload": true, "jwt": true, "backup": true}
EOF
sudo systemctl restart meko-boutique
```

**Cách B · Vá thẳng mã nguồn.** Dành cho đội muốn tự kiểm soát bản vá (hoặc khi luật yêu cầu
sửa code). Mỗi writeup có **diff cụ thể** cho `app.py`. Sau khi sửa:

```bash
sudo systemctl restart meko-boutique
```

> Cả hai cách đều phải **restart** service mới có hiệu lực.

## Nguyên tắc chung (áp dụng mọi lỗ hổng)

1. **Chặn đúng đường tấn công, giữ nguyên luồng hợp lệ.** Checker liên tục đi qua chức năng
   bình thường; vá làm hỏng chức năng ⇒ service **DOWN** ⇒ mất điểm SLA/phòng thủ nhiều hơn là
   bị mất vài flag.
2. **Dùng cơ chế đúng, không chắp vá bề mặt.** Tham số hóa thay vì lọc ký tự; kiểm tra quyền sở
   hữu thay vì giấu link; xác thực chữ ký thay vì chặn chuỗi `alg`; kiểm tra phiên thay vì gỡ route.
3. **Luôn kiểm chứng hai chiều:** (a) khai thác phải **thất bại**, (b) luồng checker hợp lệ phải
   **vẫn UP**. Mỗi writeup liệt kê cả hai.

## Kiểm chứng nhanh toàn bộ

```bash
cd ../exploits
python exploit_all.py http://127.0.0.1      # kỳ vọng: 0 flag cho cả 5
```

Kết quả đã kiểm chứng (local, bật cả 5 khóa): cả 5 khai thác trả **0 flag**, mọi luồng hợp lệ
vẫn 200 — xem bảng trong [../README.md](../README.md#đã-kiểm-chứng).
