# Bản vá 01 · SQL Injection — Tìm bộ sưu tập

**Lỗ hổng:** `q` được ghép chuỗi vào câu SQL `... WHERE title LIKE '%<q>%'` ở `/collections/search`,
cho phép `UNION SELECT` kéo `collection_notes.note` (flag). Chi tiết khai thác:
[../01-sqli.md](../01-sqli.md).

**Nguyên tắc vá:** tách **mã lệnh** khỏi **dữ liệu** — dùng truy vấn **tham số hóa** (placeholder
`?`), để chuỗi nhập chỉ còn là giá trị, không thể đổi cấu trúc truy vấn.

## Cách A — bật `patches.json`

```json
{"sqli": true}
```

Bật khóa `sqli` sẽ chạy nhánh đã tham số hóa sẵn trong
[`app.py`](../../sandbox/app/app.py) (`collection_search`):

```python
sql = "SELECT id,title,description FROM collections WHERE title LIKE ?"
rows = db.execute(sql, ("%" + q + "%",)).fetchall()
```

## Cách B — vá thẳng mã nguồn

Trong `collection_search` (≈ dòng 219–225), bỏ nhánh nối chuỗi, **luôn** tham số hóa:

```diff
     with connect(catalog_path) as db:
-        if patched("sqli"):
-            sql = "SELECT id,title,description FROM collections WHERE title LIKE ?"
-            rows = db.execute(sql, ("%" + q + "%",)).fetchall()
-        else:
-            sql = "SELECT id,title,description FROM collections WHERE title LIKE '%" + q + "%'"
-            rows = db.execute(sql).fetchall()
+        rows = db.execute(
+            "SELECT id,title,description FROM collections WHERE title LIKE ?",
+            ("%" + q + "%",)).fetchall()
     return page("Tìm bộ sưu tập", collections=rows, q=q, searched=True)
```

## Vì sao an toàn

- `?` là **bound parameter**: driver `sqlite3` gửi câu lệnh và dữ liệu tách nhau; `%`, `'`,
  `UNION`, `--` trong `q` chỉ là ký tự trong chuỗi tìm, không được phân tích thành cú pháp SQL.
- Ký tự `%` và `_` do người dùng nhập vẫn là wildcard của `LIKE` — chấp nhận được cho ô tìm kiếm
  và **không** tạo lỗ hổng (không phải SQLi).

## Sai lầm thường gặp (làm DOWN hoặc vẫn thủng)

- ❌ **Lọc/đen danh sách ký tự** (`'`, `UNION`, `--`): dễ bị vượt (biến thể hoa/thường, nội tuyến
  bình luận...) và làm hỏng tìm kiếm hợp lệ có dấu nháy ⇒ có thể khiến checker MUMBLE.
- ❌ **Vô hiệu hóa ô tìm kiếm / luôn trả rỗng:** checker đi qua `/collections/search` với tên bộ
  sưu tập thật và mong có kết quả ⇒ service **MUMBLE/DOWN**.
- ❌ **Chỉ escape một tầng** rồi vẫn nối chuỗi: vẫn thủng. Chỉ tham số hóa mới chắc chắn.

## Kiểm chứng

- ✅ Tấn công thất bại: payload `zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -`
  trả **0 flag** (`python ../exploits/sqli.py <url>`).
- ✅ Luồng hợp lệ UP: tìm theo một từ trong tiêu đề bộ sưu tập thật vẫn ra đúng kết quả; checker
  SQLi (tìm kiếm hợp lệ + đọc lại ghi chú của chính chủ) vẫn **UP**.
