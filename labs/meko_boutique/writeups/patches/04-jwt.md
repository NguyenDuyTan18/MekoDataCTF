# Bản vá 04 · JWT `alg=none` — Ưu đãi hội viên

**Lỗ hổng:** `is_vip()` chấp nhận token `alg=none` (không chữ ký) khi chưa vá ⇒ rèn token
`rank=c-nocturne` để vào khu hội viên, đọc `vip_offers.code` (flag). Chi tiết khai thác:
[../04-jwt.md](../04-jwt.md).

**Nguyên tắc vá:** **không bao giờ tin `alg` do client khai**. Chỉ chấp nhận thuật toán chữ ký
đã cố định (HS256) và **xác minh chữ ký HMAC** bằng khóa bí mật phía server.

## Cách A — bật `patches.json`

```json
{"jwt": true}
```

Bật khóa `jwt` làm nhánh `alg=none` luôn False (nhờ `and not patched("jwt")` trong
[`app.py`](../../sandbox/app/app.py) · `is_vip`), chỉ còn HS256 ký đúng.

## Cách B — vá thẳng mã nguồn

Trong `is_vip` (≈ dòng 483–484), bỏ hẳn nhánh `alg=none`, chỉ giữ HS256 có chữ ký hợp lệ:

```diff
-        valid = ((header.get("alg") == "none" and sig == "" and not patched("jwt"))
-                 or (header.get("alg") == "HS256" and hmac.compare_digest(expected, sig)))
+        valid = header.get("alg") == "HS256" and hmac.compare_digest(expected, sig)
```

## Vì sao an toàn

- Token rèn có `alg=none`, chữ ký rỗng ⇒ không khớp điều kiện `alg=="HS256"` ⇒ **bị từ chối**.
- `expected = HMAC-SHA256(jwt_secret, header.body)`; kẻ tấn công không biết `jwt_secret` nên
  không tạo được chữ ký hợp lệ cho claims họ chọn.
- `hmac.compare_digest` so sánh **thời gian hằng**, tránh rò rỉ qua timing side-channel.
- Các ràng buộc còn lại (`exp` tương lai, `sub == session["uid"]`) vẫn giữ — phòng thủ chiều sâu.

## Sai lầm thường gặp (làm DOWN hoặc vẫn thủng)

- ❌ **Chặn chuỗi `"none"`** (vd từ chối nếu `alg=="none"`) nhưng vẫn để nhánh chấp nhận khác lỏng:
  có thể bị lách bằng `None`, `nOnE`, hoặc biến thể khác. Cách chắc chắn là **chỉ cho phép HS256
  ký đúng**, mặc định từ chối mọi thứ khác.
- ❌ **Từ chối mọi token / chặn cả `/member/*`:** checker JWT cấp hạng `c-nocturne` qua
  `/staff/vip/members` rồi đăng nhập lại để lấy **token HS256 thật** và đọc ưu đãi ⇒ nếu chặn
  hết thì service **MUMBLE/DOWN**.
- ❌ **So sánh chữ ký bằng `==`** thay vì `compare_digest`: rủi ro timing; dùng hàm so sánh hằng thời.

## Kiểm chứng

- ✅ Tấn công thất bại: `python ../exploits/jwt.py <url>` ⇒ `/member/benefits` trả **403**,
  **0 flag**.
- ✅ Luồng hợp lệ UP: hội viên được nhân viên cấp hạng (token HS256 thật) vẫn vào `/member/benefits`
  và đọc `/member/offers/<id>`; checker JWT vẫn **UP**.
