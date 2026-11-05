"""Kiểm thử chức năng thông thường: dữ liệu được lưu, chủ sở hữu đọc lại được, restart không mất."""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sandbox" / "app"))
import app as shop  # noqa: E402

STAFF_PASSWORD = "staff-secret-pw"


def build(tmp_path):
    application = shop.create_app({"DATA_DIR": tmp_path / "data", "TEAM_ID": "team1",
                                   "STAFF_PASSWORD": STAFF_PASSWORD})
    application.config["TESTING"] = True
    return application


def login(client, username="alice", password="PasswordAlice1"):
    client.post("/register", data={"username": username, "password": password,
                                    "name": username, "email": "a@example.test"})
    assert client.post("/login", data={"username": username, "password": password}).status_code == 302


def staff(app):
    client = app.test_client()
    assert client.post("/staff/login", data={"password": STAFF_PASSWORD}).status_code == 302
    return client


def body(response):
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_health_has_team_and_old_endpoints_are_gone(tmp_path):
    client = build(tmp_path).test_client()
    assert client.get("/health").json == {"status": "ok", "service": "meko-boutique", "team": "team1"}
    assert client.get("/api/collection").status_code == 404
    assert client.get("/api/checker/flag/idor").status_code == 404


def test_state_has_only_session_secrets(tmp_path):
    app = build(tmp_path)
    state = json.loads(Path(app.config["STATE_FILE"]).read_text(encoding="utf-8"))
    assert set(state) == {"team", "secret", "jwt_secret"}


def test_owner_reads_each_order_memo(tmp_path):
    client = build(tmp_path).test_client()
    login(client)
    urls = []
    for memo in ("giao buoi sang", "giao buoi chieu"):
        client.post("/cart/add/1", data={"quantity": "1"})
        urls.append(client.post("/checkout", data={"memo": memo}).headers["Location"])
    assert "giao buoi sang" in body(client.get(urls[0]))
    assert "giao buoi chieu" in body(client.get(urls[1]))


def test_owner_reads_each_collection_note(tmp_path):
    client = build(tmp_path).test_client()
    login(client)
    urls = [client.post("/account/notes", data={"collection_id": "1", "note": note}).headers["Location"]
            for note in ("ghi chu mot", "ghi chu hai")]
    assert "ghi chu mot" in body(client.get(urls[0]))
    assert "ghi chu hai" in body(client.get(urls[1]))
    assert "/account/notes/" in body(client.get("/account/notes"))
    assert client.post("/account/notes", data={"collection_id": "999", "note": "x"}).status_code == 400


def test_collection_search_uses_catalog(tmp_path):
    client = build(tmp_path).test_client()
    assert "Nàng thơ" in body(client.get("/collections"))
    assert "Nàng thơ" in body(client.get("/collections/search", query_string={"q": "Nàng"}))


def test_outfit_note_is_private_to_owner_and_kept_out_of_designs(tmp_path):
    app = build(tmp_path)
    client = app.test_client()
    login(client)
    manifest = {"name": "Phoi thu", "preview_file": "lookbook.txt", "stylist_note": "ghi chu stylist"}
    response = client.post("/outfits/new", content_type="multipart/form-data",
                           data={"manifest": (io.BytesIO(json.dumps(manifest).encode()), "o.json")})
    page = body(response)
    token = page.split('href="/outfits/')[1].split('"')[0]
    assert "ghi chu stylist" in body(client.get("/outfits/" + token))
    designs = tmp_path / "data" / "simulation" / "designs"
    assert not any("ghi chu stylist" in path.read_text(encoding="utf-8") for path in designs.iterdir())

    other = app.test_client()
    login(other, "bobby")
    assert other.get("/outfits/" + token).status_code == 403
    assert other.get("/outfits/" + "0" * 32).status_code == 404


def test_staff_grants_vip_and_member_reads_offer(tmp_path):
    app = build(tmp_path)
    member = app.test_client()
    login(member)
    assert member.get("/member/benefits").status_code == 403

    desk = staff(app)
    location = desk.post("/staff/vip", data={"code": "uu-dai-thu"}).headers["Location"]
    assert "uu-dai-thu" in body(desk.get(location))
    assert desk.post("/staff/vip/members", data={"username": "alice"}).status_code == 302
    assert desk.post("/staff/vip/members", data={"username": "nobody"}).status_code == 404

    login(member)
    assert "/member/offers/" in body(member.get("/member/benefits"))
    assert "uu-dai-thu" in body(member.get("/member/offers/" + location.rsplit("/", 1)[-1]))


def test_staff_export_contains_each_reconciliation(tmp_path):
    desk = staff(build(tmp_path))
    for value in ("doi soat mot", "doi soat hai"):
        assert desk.post("/staff/reconciliation", data={"value": value}).status_code == 302
    export = body(desk.get("/exports/operations.sql"))
    assert "doi soat mot" in export and "doi soat hai" in export
    assert "RC-" in body(desk.get("/staff/reconciliation"))


def test_staff_pages_require_login(tmp_path):
    client = build(tmp_path).test_client()
    for path in ("/staff/vip", "/staff/reconciliation"):
        assert client.get(path).status_code == 302


def test_data_survives_restart(tmp_path):
    client = build(tmp_path).test_client()
    login(client)
    note_url = client.post("/account/notes", data={"collection_id": "1", "note": "con nguyen"}).headers["Location"]
    client = build(tmp_path).test_client()
    login(client)
    assert "con nguyen" in body(client.get(note_url))
