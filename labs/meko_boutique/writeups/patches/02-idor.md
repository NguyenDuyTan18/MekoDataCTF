# Bản vá 02 · IDOR — Hóa đơn đơn hàng

**Lỗ hổng:** `/account/orders/<id>/invoice` tra đơn theo id đoán được, chưa vá thì **không kiểm
tra chủ sở hữu** ⇒ đọc hóa đơn người khác, lấy `orders.memo` (flag). Chi tiết khai thác:
[../02-idor.md](../02-idor.md).

**Nguyên tắc vá:** mọi truy cập theo đối tượng phải **kiểm tra quyền sở hữu** (authorization),
không chỉ kiểm tra đã đăng nhập (authentication). So chủ đơn với người đang đăng nhập.

## Cách A — bật `patches.json`

```json
{"idor": true}
```

Bật khóa `idor` kích hoạt kiểm tra sẵn có trong [`app.py`](../../sandbox/app/app.py) (`invoice`):

```python
if order["user_id"] != session["uid"]:
    abort(403)
```

## Cách B — vá thẳng mã nguồn

Trong `invoice` (≈ dòng 400–405), bỏ điều kiện `patched("idor")` để **luôn** kiểm tra chủ sở hữu:

```diff
         order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
         if not order:
             abort(404)
-        if patched("idor") and order["user_id"] != session["uid"]:
+        if order["user_id"] != session["uid"]:
             abort(403)
```

## Vì sao an toàn

- Dù `order_id` đoán được, server chỉ trả hóa đơn khi `order.user_id == session["uid"]` ⇒ người
  dùng chỉ xem được đơn **của chính mình**.
- `session["uid"]` do server đặt lúc đăng nhập (trong cookie ký bởi `secret`), client không sửa
  được ⇒ không giả mạo được chủ đơn.
- Trả **403** (thay vì 404) là chấp nhận được ở đây; nếu muốn tránh lộ "đơn có tồn tại", có thể
  trả 404 cho cả hai trường hợp — không bắt buộc cho lab này.

## Sai lầm thường gặp (làm DOWN hoặc vẫn thủng)

- ❌ **Chỉ giấu link "Xem hóa đơn" trên UI** mà route vẫn mở: kẻ tấn công gọi thẳng URL vẫn đọc
  được ⇒ vẫn thủng.
- ❌ **Chặn toàn bộ `/invoice`** hoặc bắt buộc quyền nhân viên: checker IDOR đặt đơn rồi mở lại
  hóa đơn **của chính tài khoản đó** ⇒ bị chặn ⇒ service **MUMBLE/DOWN**.
- ❌ **Lọc theo dải id** (vd chặn id < 9000): sai hoàn toàn — chủ đơn hợp lệ cũng có id bất kỳ,
  và kẻ tấn công vẫn đọc được đơn trong dải cho phép.

## Kiểm chứng

- ✅ Tấn công thất bại: `python ../exploits/idor.py <url>` quét id ⇒ **0 flag** (mỗi đơn người
  khác trả 403).
- ✅ Luồng hợp lệ UP: đăng nhập → đặt hàng → mở **hóa đơn của mình** ⇒ 200; checker IDOR vẫn **UP**.
