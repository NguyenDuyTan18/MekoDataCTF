import json
from io import BytesIO
import sys
import time
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sandbox" / "app"))

import pytest

from app import create_app


@pytest.fixture
def shop(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path), "TEAM_ID": "team1", "TICK_SECONDS": 60})
    return app.test_client(), app


def register(client, username="mai"):
    return client.post("/register", data={"username": username, "password": "MatKhauThuNghiem2026!", "name": "Mai Trần", "email": "mai@example.test"})


def login(client, username="mai"):
    register(client, username)
    return client.post("/login", data={"username": username, "password": "MatKhauThuNghiem2026!"})


def test_customer_purchase_and_order_access(shop):
    client, _ = shop
    assert client.get("/").status_code == 200
    assert client.get("/search?q=áo").status_code == 200
    assert client.get("/product/1").status_code == 200
    login(client)
    assert client.post("/cart/add/1", data={"quantity": "1"}).status_code == 302
    assert client.post("/account/collection/add/1").status_code == 302
    assert "Nắng Mai".encode() in client.get("/account/collection").data
    assert client.post("/checkout", data={"coupon": "MEKO10"}).status_code == 302
    orders = client.get("/account/orders")
    assert orders.status_code == 200
    assert b"DH-" in orders.data


def test_five_challenges_and_patches(shop):
    client, app = shop
    login(client)
    flags = app.config["STATE_FILE"].read_text()
    import base64
    original = json.loads(flags)["flags"]
    payload = "%' UNION SELECT 1,secret,'x' FROM collection_notes--"
    assert original["sqli"].encode() in client.get("/collections/search", query_string={"q": payload}).data
    assert original["idor"].encode() in client.get("/account/orders/9001/invoice").data
    manifest = ("{\"preview_file\":\"../private-collection.txt\"}").encode()
    response = client.post("/outfits/new", data={"manifest": (BytesIO(manifest), "outfit.json")}, content_type="multipart/form-data")
    assert original["upload"].encode() in response.data, response.get_data(as_text=True)
    outside = b'{"preview_file":"../../../../Windows/win.ini"}'
    assert client.post("/outfits/new", data={"manifest": (BytesIO(outside), "outfit.json")}, content_type="multipart/form-data").status_code == 400
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
    with client.session_transaction() as sess: user_id = str(sess["uid"])
    token = enc(b'{"alg":"none"}') + "." + enc(json.dumps({"sub":user_id,"rank":"c-nocturne","exp":time.time()+600}).encode()) + "."
    client.set_cookie("meko_member", token)
    assert original["jwt"].encode() in client.get("/member/benefits").data
    assert original["backup"].encode() in client.get("/exports/operations.sql").data
    patch_file = app.config["DATA_DIR"] / "patches.json"
    patch_file.write_text(json.dumps({key: True for key in ("sqli", "idor", "upload", "jwt", "backup")}))
    app2 = create_app({"TESTING": True, "DATA_DIR": str(app.config["DATA_DIR"]), "TEAM_ID": "team1", "TICK_SECONDS": 60})
    client2 = app2.test_client()
    login(client2)
    client2.set_cookie("meko_member", token)
    assert client2.get("/account/orders/9001/invoice").status_code == 403
    assert client2.post("/outfits/new", data={"manifest": (BytesIO(manifest), "outfit.json")}, content_type="multipart/form-data").status_code == 400
    assert client2.get("/member/benefits").status_code == 403
    assert app2.test_client().get("/exports/operations.sql").status_code == 404


def test_tick_rotates_flags_but_survives_restart(shop):
    client, app = shop
    state = app.config["STATE_FILE"]
    data = json.loads(state.read_text())
    old = data["flags"]["sqli"]
    data["started"] = time.time() - 120
    state.write_text(json.dumps(data))
    app2 = create_app({"TESTING": True, "DATA_DIR": str(app.config["DATA_DIR"]), "TEAM_ID": "team1", "TICK_SECONDS": 60})
    rotated = json.loads(state.read_text())
    assert rotated["tick"] >= 1 and rotated["flags"]["sqli"] != old
    app3 = create_app({"TESTING": True, "DATA_DIR": str(app.config["DATA_DIR"]), "TEAM_ID": "team1", "TICK_SECONDS": 60})
    assert json.loads(app3.config["STATE_FILE"].read_text()) == rotated


def test_checker_auth_and_flag_round_trip(shop):
    client, app = shop
    key = app.config["CHECKER_KEY"]
    assert client.get("/api/checker/flag/sqli").status_code == 403
    headers = {"X-Checker-Key": key}
    value = "FLAG{" + "a" * 32 + "}"
    assert client.put("/api/checker/flag/sqli", headers=headers, json={"flag": value}).json["flag"] == value
    assert client.get("/api/checker/flag/sqli", headers=headers).json["flag"] == value


def test_staff_can_manage_products_and_orders(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path), "TEAM_ID": "team1", "STAFF_PASSWORD": "StaffDemoOnly2026!"})
    client = app.test_client()
    assert client.get("/staff").status_code == 302
    assert client.post("/staff/login", data={"password": "StaffDemoOnly2026!"}).status_code == 302
    assert client.post("/staff/products", data={"name":"Khăn lụa","category":"Phụ kiện","price":"250000"}).status_code == 302
    assert "Khăn lụa".encode() in client.get("/staff/products").data
    assert client.post("/staff/orders/9001/status", data={"status":"Đã giao"}).status_code == 302


def test_topology_names_and_team_network_are_consistent():
    topology = yaml.safe_load((Path(__file__).resolve().parents[1] / "sandbox" / "topology.yml").read_text())
    hosts = {host["name"] for host in topology["hosts"]}
    routers = {router["name"] for router in topology["routers"]}
    networks = {network["name"] for network in topology["networks"]}
    assert hosts == {"team1", "team2", "team3", "team4"}
    assert topology["groups"][0]["nodes"] == sorted(hosts)
    assert all(item["host"] in hosts and item["network"] in networks for item in topology["net_mappings"])
    assert all(item["router"] in routers and item["network"] in networks for item in topology["router_mappings"])
