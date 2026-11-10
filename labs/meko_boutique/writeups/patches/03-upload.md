# Bản vá 03 · Path Traversal — Studio phối đồ

**Lỗ hổng:** `preview_file` trong manifest không bị giới hạn trong `designs/` khi chưa vá ⇒ dùng
`../private/<token>.json` để đọc tệp trong vùng `simulation/` (gồm ghi chú stylist = flag). Chi
tiết khai thác: [../03-upload.md](../03-upload.md).

**Nguyên tắc vá:** với đường dẫn do người dùng kiểm soát, **resolve rồi kiểm tra nằm trong thư
mục cho phép** (canonical-path containment). Ở đây thư mục hợp lệ là `simulation/designs`.

## Cách A — bật `patches.json`

```json
{"upload": true}
```

Bật khóa `upload` kích hoạt kiểm tra containment sẵn có trong
[`app.py`](../../sandbox/app/app.py) (`outfit_new`):

```python
if not target.is_relative_to(base):     # base = .../simulation/designs
    abort(400)
```

## Cách B — vá thẳng mã nguồn

Trong `outfit_new` (≈ dòng 436–443), bỏ điều kiện `patched("upload")` để **luôn** ép
`preview_file` nằm trong `designs/`:

```diff
     base = (data / "simulation" / "designs").resolve()
     sandbox_root = (data / "simulation").resolve()
     target = (base / manifest.get("preview_file", "")).resolve()
-    if patched("upload") and not target.is_relative_to(base):
+    if not target.is_relative_to(base):
         abort(400)
     # Rào chắn cứng: dù vá hay chưa, không bao giờ cho đọc ra ngoài vùng simulation giả lập.
     if not target.is_relative_to(sandbox_root) or not target.is_file():
         abort(400)
```

> Giữ nguyên dòng rào chắn `sandbox_root` phía dưới — đó là lớp phòng thủ chiều sâu.

## Vì sao an toàn

- `.resolve()` chuẩn hóa toàn bộ `..` và symlink thành đường dẫn tuyệt đối thực tế **trước khi**
  kiểm tra ⇒ không thể lách bằng `../`, `./`, hay encoding, vì kết quả cuối cùng bị so với `base`.
- `target.is_relative_to(base)` đảm bảo tệp đọc chỉ nằm trong `simulation/designs` (vùng công
  khai). `../private/...` resolve ra ngoài `designs` ⇒ **400**.
- Preview hợp lệ `lookbook.txt` resolve thành `.../designs/lookbook.txt` ⇒ vẫn nằm trong `base` ⇒
  chạy bình thường.

## Sai lầm thường gặp (làm DOWN hoặc vẫn thủng)

- ❌ **Chặn chuỗi `".."` một cách ngây thơ** (vd `if ".." in preview_file`): dễ bị lách (ký tự
  mã hóa, đường dẫn tuyệt đối) và có thể chặn nhầm; luôn kiểm tra bằng **đường dẫn đã resolve**.
- ❌ **Gỡ chức năng upload / luôn 400:** checker Upload gửi manifest hợp lệ (`preview_file=lookbook.txt`)
  và mong 200 + preview ⇒ bị chặn ⇒ service **MUMBLE/DOWN**.
- ❌ **Kiểm tra bằng `startswith(str(base))` trên chuỗi chưa resolve:** sai, vì `..` chưa được
  rút gọn. Dùng `Path.resolve()` + `is_relative_to`.

## Kiểm chứng

- ✅ Tấn công thất bại: `python ../exploits/upload.py <url>` ⇒ self-PoC traversal trả **HTTP 400**
  (`đọc được ghi chú riêng: False`).
- ✅ Luồng hợp lệ UP: upload manifest `{"preview_file":"lookbook.txt", ...}` ⇒ 200 và hiện preview;
  checker Upload (upload hợp lệ + đọc lại ghi chú của chính chủ) vẫn **UP**.
