# Bản vá 05 · Lộ bản backup — Bản xuất vận hành

**Lỗ hổng:** `/exports/operations.sql` không yêu cầu đăng nhập khi chưa vá ⇒ bất kỳ ai tải được
bản dump chứa `reconciliation_notes.value` (flag). Chi tiết khai thác: [../05-backup.md](../05-backup.md).

**Nguyên tắc vá:** tài nguyên nhạy cảm phải có **kiểm soát truy cập**, không dựa vào "địa chỉ khó
đoán". Chỉ phiên **nhân viên** mới được tải bản xuất — **không gỡ** chức năng (nhân viên vẫn cần).

## Cách A — bật `patches.json`

```json
{"backup": true}
```

Bật khóa `backup` kích hoạt kiểm tra sẵn có trong [`app.py`](../../sandbox/app/app.py)
(`operations_export`):

```python
if session.get("staff") is not True:
    abort(404)
```

## Cách B — vá thẳng mã nguồn

Trong `operations_export` (≈ dòng 516–521), bỏ điều kiện `patched("backup")` để **luôn** yêu cầu
phiên nhân viên:

```diff
     @app.get("/exports/operations.sql")
     def operations_export():
-        if patched("backup") and session.get("staff") is not True:
+        if session.get("staff") is not True:
             abort(404)
```

> Hoặc tương đương: thêm decorator `@staff_required` cho route (sẽ redirect về `/staff/login`
> thay vì 404 — cũng chặn được khách, nhưng 404 kín đáo hơn).

## Vì sao an toàn

- `session["staff"]` chỉ được đặt `True` sau khi đăng nhập đúng mật khẩu nhân viên ở
  `/staff/login` (so bằng `hmac.compare_digest`), nằm trong cookie ký bởi server ⇒ khách không
  giả mạo được.
- Trả **404** cho khách vừa chặn truy cập vừa không xác nhận sự tồn tại của tài nguyên.
- Nhân viên (đã đăng nhập) vẫn tải được bản xuất ⇒ chức năng vận hành không mất.

## Sai lầm thường gặp (làm DOWN hoặc vẫn thủng)

- ❌ **Chỉ sửa `robots.txt`** (bỏ dòng `Disallow: /exports/`): đây là *security by obscurity* —
  route vẫn mở, ai biết URL vẫn tải được ⇒ **vẫn thủng**.
- ❌ **Xóa route / xóa tệp xuất / luôn 404:** checker Backup **đăng nhập nhân viên** rồi tải
  `/exports/operations.sql` và mong 200 ⇒ nếu chặn cả nhân viên thì service **MUMBLE/DOWN**.
- ❌ **Đổi tên đường dẫn xuất:** checker gọi đúng `/exports/operations.sql`; đổi tên làm checker
  DOWN mà vẫn không thực sự kiểm soát truy cập.

## Kiểm chứng

- ✅ Tấn công thất bại: `python ../exploits/backup.py <url>` (không đăng nhập) ⇒ **404**, **0 flag**.
- ✅ Luồng hợp lệ UP: đăng nhập `/staff/login` rồi tải `/exports/operations.sql` ⇒ 200; checker
  Backup vẫn **UP**.
