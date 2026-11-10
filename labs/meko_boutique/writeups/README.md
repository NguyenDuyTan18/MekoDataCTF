# Writeups khai thác & bản vá · Meko Boutique

> ⚠️ **TÀI LIỆU NỘI BỘ (giảng viên/tác giả lab).** Chứa lời giải đầy đủ cho cả 5 lỗ hổng.
> **Không phát cho thí sinh.** Chỉ dùng trên các VM trong phạm vi lab cô lập.

Mỗi đội vận hành một bản cửa hàng thời trang (`/opt/meko-boutique`, source ở
[`sandbox/app/app.py`](../sandbox/app/app.py)). Có **5 nhóm lỗ hổng**; hệ thống chấm
(ForcAD) liên tục cắm flag mới qua chức năng thường của cửa hàng, nên mỗi tick có nhiều
flag còn hiệu lực. Nhiệm vụ đội: **khai thác** cửa hàng đội khác để lấy flag, đồng thời
**vá** cửa hàng của mình mà vẫn giữ chức năng hợp lệ (checker vẫn phải UP).

- Định dạng flag: `MekoDataCTF{<30 ký tự A-Z0-9>}`
- Địa chỉ mục tiêu: `http://10.90.0.11/` (team1), `http://10.90.0.12/` (team2), `http://10.90.0.13/` (team3)

## Mục lục

| # | Lỗ hổng | Writeup | Khu vực | Cần đăng nhập? | Flag nằm ở |
|---|---------|---------|---------|----------------|------------|
| 1 | SQL Injection (UNION) | [01-sqli.md](01-sqli.md) | Tìm bộ sưu tập | Không | `collection_notes.note` |
| 2 | IDOR | [02-idor.md](02-idor.md) | Hóa đơn đơn hàng | Có (tài khoản bất kỳ) | `orders.memo` |
| 3 | Path Traversal (upload) | [03-upload.md](03-upload.md) | Studio phối đồ | Có | `simulation/private/<token>.json` |
| 4 | JWT `alg=none` | [04-jwt.md](04-jwt.md) | Ưu đãi hội viên | Có | `vip_offers.code` |
| 5 | Lộ bản backup | [05-backup.md](05-backup.md) | Bản xuất vận hành | Không | `reconciliation_notes.value` |

Bản vá: [PATCHES.md](PATCHES.md) (tóm tắt + cách bật) · [patches/](patches/) (writeup vá chi tiết
từng lỗ hổng: vá mã nguồn, vì sao an toàn, sai lầm làm DOWN, kiểm chứng).

## Phương pháp (áp dụng cho mọi lỗ hổng)

Mỗi writeup đi theo 5 bước:

1. **Nhận dạng** — dấu hiệu quan sát được từ ngoài (black-box) để nghi ngờ lỗ hổng.
2. **Phân tích mã nguồn** — đoạn code lỗi (`file:line`) và vì sao khai thác được.
3. **Khai thác thủ công** — các bước bằng `curl`/trình duyệt để lấy flag bằng tay.
4. **Script tự động** — script Python trong [`exploits/`](exploits/) lấy flag hàng loạt.
5. **Bản vá** — cách vá đúng (không phá chức năng) và cách tự kiểm chứng.

## Chạy script khai thác

Script chỉ dùng **thư viện chuẩn Python 3** (chạy ngay trên Kali, không cần cài gói).

```bash
cd exploits

# Từng lỗ hổng, một mục tiêu:
python sqli.py   http://10.90.0.12
python idor.py   http://10.90.0.12
python jwt.py    http://10.90.0.12
python backup.py http://10.90.0.12
python upload.py http://10.90.0.12            # xem ghi chú riêng về Upload

# Cả 5 lỗ hổng, nhiều mục tiêu một lượt:
python exploit_all.py http://10.90.0.11 http://10.90.0.12 http://10.90.0.13
```

Mỗi script in ra các flag `MekoDataCTF{...}` thu được. Nộp flag lên bảng điểm nền tảng.

## Đã kiểm chứng

Toàn bộ 5 script được chạy thử end-to-end trên một bản app cục bộ, cắm flag bằng chính
checker (`sandbox/checker/meko_checker.py`):

| Lỗ hổng | Chưa vá | Sau khi bật `patches.json` |
|---------|---------|----------------------------|
| SQLi    | lấy được flag | 0 flag (truy vấn tham số hóa) |
| IDOR    | lấy được flag | 0 flag (403 khi khác chủ đơn) |
| Upload  | traversal đọc tệp private (200) | traversal bị chặn (400), preview hợp lệ vẫn 200 |
| JWT     | lấy được flag | 0 flag (`/member/*` trả 403) |
| Backup  | lấy được flag | 0 flag (`/exports/operations.sql` trả 404 cho khách) |

Sau khi vá, các chức năng hợp lệ (health, preview lookbook, mua hàng, xem hóa đơn của
chính mình...) vẫn hoạt động, nên checker vẫn chấm UP.
