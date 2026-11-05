"""Kiểm thử chức năng và năm thử thách của Meko Boutique (chạy local, không chạm pool)."""
import base64
import io
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sandbox" / "app"))
import app as shop  # noqa: E402

CHECKER_KEY = "test-checker-key"
STAFF_PASSWORD = "staff-secret-pw"


def build(tmp_path, patched=None):
    data = tmp_path / "data"
    cfg = {
        "DATA_DIR": data,
        "TEAM_ID": "team1",
        "TICK_SECONDS": 3600,
        "STAFF_PASSWORD": STAFF_PASSWORD,
        "CHECKER_KEY": CHECKER_KEY,
    }
    application = shop.create_app(cfg)
    application.config["TESTING"] = True
    if patched:
        (data / "patches.json").write_text(json.dumps(patched), encoding="utf-8")
        application = shop.create_app(cfg)
        application.config["TESTING"] = True
    return application


def flag(app, task):
    state = json.loads(Path(app.config["STATE_FILE"]).read_text(encoding="utf-8"))
    return state["flags"][task]


def register_login(client, username="alice", password="PasswordAlice1"):
    client.post("/register", data={"username": username, "password": password,
                                    "name": "Alice", "email": "a@example.test"})
    client.post("/login", data={"username": username, "password": password})
    with client.session_transaction() as sess:
        return sess["uid"]


def set_cookie(client, name, value):
    try:
        client.set_cookie(name, value)
    except TypeError:  # Werkzeug cũ
        client.set_cookie("localhost", name, value)


def test_health_and_browse(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    r = c.get("/health")
    assert r.status_code == 200 and r.json["status"] == "ok" and r.json["team"] == "team1"
    assert c.get("/").status_code == 200
    assert c.get("/product/1").status_code == 200
    assert c.get("/collections").status_code == 200
    assert "Meko Boutique" in c.get("/").get_data(as_text=True)
    # Giao diện mua sắm không rò rỉ flag.
    assert "FLAG{" not in c.get("/").get_data(as_text=True)
    assert "FLAG{" not in c.get("/collections").get_data(as_text=True)


def test_register_login_order_flow(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    register_login(c)
    c.post("/cart/add/1", data={"quantity": "2"})
    assert c.get("/cart").status_code == 200
    r = c.post("/checkout", data={"coupon": "MEKO10"}, follow_redirects=True)
    assert r.status_code == 200 and "Hóa đơn" in r.get_data(as_text=True)


def test_sqli_unpatched_then_patched(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    payload = "zzz%' UNION SELECT 1, secret, '' FROM collection_notes --"
    body = c.get("/collections/search", query_string={"q": payload}).get_data(as_text=True)
    assert flag(app, "sqli") in body

    appp = build(tmp_path / "p", patched={"sqli": True})
    cp = appp.test_client()
    body = cp.get("/collections/search", query_string={"q": payload}).get_data(as_text=True)
    assert flag(appp, "sqli") not in body
    # Chức năng tìm kiếm hợp lệ vẫn hoạt động sau khi vá.
    assert "Nàng thơ" in cp.get("/collections/search", query_string={"q": "Nàng"}).get_data(as_text=True)


def test_idor_unpatched_then_patched(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    register_login(c)
    body = c.get("/account/orders/9001/invoice").get_data(as_text=True)
    assert flag(app, "idor") in body

    appp = build(tmp_path / "p", patched={"idor": True})
    cp = appp.test_client()
    register_login(cp)
    assert cp.get("/account/orders/9001/invoice").status_code == 403


def test_upload_unpatched_patched_and_containment(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    register_login(c)

    def upload(manifest):
        data = {"manifest": (io.BytesIO(json.dumps(manifest).encode()), "outfit.json")}
        return c.post("/outfits/new", data=data, content_type="multipart/form-data")

    r = upload({"name": "Phối thu", "preview_file": "../private-lookbook.txt"})
    assert r.status_code == 200 and flag(app, "upload") in r.get_data(as_text=True)
    # Bản xem trước hợp lệ trong thư mục designs.
    assert upload({"name": "ok", "preview_file": "lookbook.txt"}).status_code == 200
    # Không thể thoát ra hệ thống host dù chưa vá.
    assert upload({"name": "x", "preview_file": "../../../../../../etc/passwd"}).status_code == 400

    appp = build(tmp_path / "p", patched={"upload": True})
    cp = appp.test_client()
    register_login(cp)
    data = {"manifest": (io.BytesIO(json.dumps({"preview_file": "../private-lookbook.txt"}).encode()), "o.json")}
    assert cp.post("/outfits/new", data=data, content_type="multipart/form-data").status_code == 400


def test_jwt_unpatched_then_patched(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    uid = register_login(c)
    assert c.get("/member/benefits").status_code == 403  # hạng basic chưa đủ

    def forge(uid):
        head = shop.b64(b'{"alg":"none","typ":"JWT"}')
        body = shop.b64(json.dumps({"sub": str(uid), "rank": "c-nocturne",
                                    "exp": int(time.time()) + 3600}).encode())
        return head + "." + body + "."

    set_cookie(c, "meko_member", forge(uid))
    r = c.get("/member/benefits")
    assert r.status_code == 200 and flag(app, "jwt") in r.get_data(as_text=True)

    appp = build(tmp_path / "p", patched={"jwt": True})
    cp = appp.test_client()
    uid2 = register_login(cp)
    set_cookie(cp, "meko_member", forge(uid2))
    assert cp.get("/member/benefits").status_code == 403


def test_backup_unpatched_then_patched(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    r = c.get("/exports/operations.sql")
    assert r.status_code == 200 and flag(app, "backup") in r.get_data(as_text=True)
    assert "Disallow: /exports/" in c.get("/robots.txt").get_data(as_text=True)

    appp = build(tmp_path / "p", patched={"backup": True})
    assert appp.test_client().get("/exports/operations.sql").status_code == 404


def test_staff_and_checker_api(tmp_path):
    app = build(tmp_path)
    c = app.test_client()
    assert c.get("/staff").status_code == 302  # chưa đăng nhập -> chuyển hướng
    c.post("/staff/login", data={"password": STAFF_PASSWORD})
    assert c.get("/staff").status_code == 200

    # Checker API yêu cầu khóa.
    assert c.get("/api/checker/flag/sqli").status_code == 403
    r = c.get("/api/checker/flag/sqli", headers={"X-Checker-Key": CHECKER_KEY})
    assert r.status_code == 200 and r.json["flag"] == flag(app, "sqli")
    new = "FLAG{" + "a" * 32 + "}"
    r = c.put("/api/checker/flag/sqli", headers={"X-Checker-Key": CHECKER_KEY}, json={"flag": new})
    assert r.status_code == 200 and r.json["flag"] == new


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
