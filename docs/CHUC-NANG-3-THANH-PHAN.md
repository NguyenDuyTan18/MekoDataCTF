# Chức năng 3 thành phần: Website, ForcAD, CyberRange

Cập nhật 12/11/2026, đối chiếu trực tiếp với mã nguồn. Lab đang dùng: `full_rounds` (vòng 1 Web) + `full_rounds/round2` (vòng 2 Crypto), pool `pool141`.

Tài liệu trả lời cho từng chức năng: **ai bấm / gọi ở đâu → đi qua file nào → chạy từ thư mục nào**.

Viết tắt đường dẫn (tính từ gốc workspace `atk_def_platform/`):

| Viết tắt | Đường dẫn | Thành phần |
|---|---|---|
| `WEB/` | `platform/MekoDataCTF_Website/` | Website (Node.js, cổng 3000) |
| `FAD/` | `platform/ForcAD-demo/` | ForcAD (Docker, cổng 18080) |
| `BE/` | `platform/ForcAD-demo/backend/` | Backend Python của ForcAD (gắn vào container ở `/app`) |
| `LAB/` | `labs/full_rounds/` | Đề thi chạy trên CyberRange |
| `KD/` | `khoi-dong/` | Bộ bật/tắt `meko.py` + cầu nối host |

---

## 0. Bức tranh chung

```text
 ┌─────────────────────────────── MÁY CHỦ BTC (Windows/Linux) ───────────────────────────────┐
 │                                                                                            │
 │  Thí sinh ──► WEBSITE :3000  (WEB/app.js, chạy: cd WEB && npm start)                       │
 │               │  SQLite WEB/data/mekodata.db (user, đội, token)                            │
 │               │  HTTP ─────────────┐                                                       │
 │               ▼                    ▼                                                       │
 │  BTC ──────► NGINX :18080  (Docker, FAD/docker-compose.yml)                                │
 │               ├─ /             → FAD/front/dist (trang điều khiển + round-control.js)      │
 │               ├─ /api/client/  → client-api     (BE/services/api)                          │
 │               ├─ /api/admin/   → admin-api      (BE/services/admin)                        │
 │               ├─ /flags/       → http-receiver  (BE/services/http_receiver)                │
 │               └─ /api/events/  → events         (BE/services/events)                       │
 │                          PostgreSQL + Redis + RabbitMQ                                     │
 │                                   ▲                                                        │
 │               ticker (BE/services/ticker) ── gọi FAD/checkers/<bài>/<lỗ>.py                │
 │                                   │   ghi <id>.request.json vào FAD/checkers/<bài>/rpc/    │
 │                                   ▼   (thư mục FAD/checkers/ được mount chung host↔Docker) │
 │  COLLECTOR (chạy trên HOST, ngoài Docker): FAD/collect_checker.py                          │
 │                                   │   SSH -F ops/pool141/management-config                 │
 │  host_bridge :18090 (KD/host_bridge.py) ── nhận nút bấm từ admin-api, bật collector/gateway│
 │  gateway (ssh -L, KD/meko.py) ── mở cổng 20001.. ra từng dịch vụ đội                       │
 └───────────────────────────────────┼────────────────────────────────────────────────────────┘
                                     │ SSH: jump 10.32.8.175 → man → VM
 ┌──────────────────────────── CYBERRANGE (sandbox pool141, LAN 10.90.0.0/24) ────────────────┐
 │  checker 10.90.0.30   /opt/meko-checker/agent.py   (Web)                                   │
 │                       /opt/crypto-checker/agent.py (Crypto)                                │
 │        │ HTTP / TCP                                                                        │
 │        ▼                                                                                   │
 │  team1 10.90.0.11   team2 10.90.0.12   team3 10.90.0.13                                    │
 │   - Meko Boutique: Apache :80 → Flask 127.0.0.1:8080 (/opt/meko-boutique/app.py)           │
 │   - Crypto: :9011 curveball, :9012 padding_oracle, :9013 ecdsa_nonce                       │
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

Nguyên tắc:

- Website **không** đọc database ForcAD; mọi thứ đi qua HTTP của nginx `:18080`.
- ForcAD (trong Docker) **không** SSH được ra CyberRange; việc đó do **collector trên host** làm, hai bên trao đổi qua file JSON trong `FAD/checkers/<bài>/rpc/`.
- Máy checker trong sandbox **không** chủ động gửi gì ra ngoài; host SSH vào, đưa yêu cầu qua stdin, đọc kết quả ở stdout.

### 0.1 Chạy từ đâu (bảng tra nhanh)

| Việc | Thư mục đứng | Lệnh / file khởi chạy |
|---|---|---|
| Bật website | `WEB/` | `npm start` → `node app.js` |
| Tạo tài khoản admin website | `WEB/` | `npm run seed` → `scripts/seed.js` |
| Đồng bộ token tay | `WEB/` | `npm run sync:forcad [-- --apply]` → `scripts/sync-forcad-tokens.js` |
| Xuất danh sách đội ra lab.json | `WEB/` | `npm run export:lab -- --write full_rounds` → `scripts/export-lab-teams.js` |
| Bật toàn bộ ForcAD | gốc workspace | `python khoi-dong/meko.py server` (= `docker compose up -d` + `setup_round1.py`) |
| Bật bộ cờ + collector | gốc workspace | `python khoi-dong/meko.py flag` |
| Chỉ collector | gốc workspace | `python khoi-dong/meko.py collector start` |
| Gateway | gốc workspace | `python khoi-dong/meko.py gateway start` |
| Thử checker | gốc workspace | `python khoi-dong/meko.py check` |
| Mở/dừng round bằng lệnh | gốc workspace | `python khoi-dong/meko.py round start` → `FAD/switch_round.py` |
| Cầu nối cho nút web | gốc workspace | `python khoi-dong/meko.py bridge install` → `KD/host_bridge.py` |
| Dựng sandbox | CyberRangeCZ (Git) | `LAB/topology.yml` + `LAB/provisioning/playbook.yml` |

Windows có thể bấm đúp `KD/meko.bat`, Linux dùng `KD/meko.sh`. Cấu hình duy nhất cần sửa: `KD/cau-hinh.conf` (`LABS`, `POOL`, `TEST_IP`, `WEB`, `GATEWAY_BIND`).

---

## 1. WEBSITE (`WEB/`)

### 1.1 Khởi động

```text
cd platform/MekoDataCTF_Website && npm start
└─ WEB/app.js
   ├─ WEB/.env                       PORT, SESSION_SECRET, FORCAD_URL, FORCAD_ADMIN_*, FORCAD_SYNC_INTERVAL
   ├─ WEB/config/database.js         mở SQLite data/mekodata.db, chạy config/schema.sql
   │                                 (bảng users, teams, members, settings, contents)
   ├─ session lưu trong SQLite       (better-sqlite3-session-store)
   ├─ middlewares: i18n.js → locals.js (gắn req.user) → csrf.js
   ├─ routes:
   │    /            routes/scoreboard.js   (scoreboard, nộp flag)
   │    /            routes/index.js        (trang chủ)
   │    /            routes/auth.js         (đăng nhập/đăng ký)
   │    /team        routes/team.js
   │    /admin       routes/admin.js
   └─ app.listen(0.0.0.0:3000) → in IP LAN (helpers/lanAddress.js)
      └─ services/forcadSync.js start()  đồng bộ token lúc khởi động + mỗi 60 giây
```

Phân quyền nằm ở `WEB/middlewares/auth.js`:

| Hàm | Ai qua được |
|---|---|
| `requireGuest` | Chưa đăng nhập (đã đăng nhập thì chuyển `/team` hoặc `/admin`) |
| `requireContestant` | Thí sinh (role `contestant`) |
| `requireCaptain` | Thí sinh là đội trưởng (`sessionTeam(req).role === 'captain'`) |
| `requireAdmin` | Role `admin` (tạo bằng `npm run seed`) |
| `sessionTeam(req)` | Trả `{team, role}` của thí sinh đang đăng nhập |

### 1.2 Sơ đồ chức năng theo vai trò

```text
 KHÁCH ──────────┬─ Xem trang chủ, đếm ngược ............ GET  /                 homeController.index
                 ├─ Xem scoreboard (không nộp flag) .... GET  /scoreboard       routes/scoreboard.js
                 ├─ Đăng ký tài khoản .................. POST /register         authController.register
                 └─ Đăng nhập .......................... POST /login            authController.login

 THÍ SINH ───────┬─ (mọi chức năng của khách)
 (chưa có đội)   ├─ Bổ sung hồ sơ (họ tên, MSSV) ....... POST /team/profile     teamController.saveProfile
                 ├─ Tạo đội (thành đội trưởng) ......... POST /team/create      teamController.create
                 ├─ Vào đội bằng mã mời ................ POST /team/join        teamController.join
                 └─ Đăng xuất .......................... POST /logout           authController.logout

 THÀNH VIÊN ─────┬─ Xem đội ............................ GET  /team             teamController.show
                 ├─ Rời đội ............................ POST /team/leave       teamController.leave
                 └─ NỘP FLAG ........................... POST /scoreboard/submit  → ForcAD /flags/

 ĐỘI TRƯỞNG ─────┬─ (mọi chức năng thành viên)
                 ├─ Sửa thông tin đội .................. GET/POST /team/edit, /team   teamController.edit/save
                 ├─ Xóa thành viên ..................... POST /team/members/:id/remove
                 └─ Giải tán đội ....................... POST /team/disband

 ADMIN WEBSITE ──┬─ Dashboard thống kê ................. GET  /admin            adminController.dashboard
                 ├─ Sửa nội dung trang chủ ............. GET/POST /admin/contents
                 ├─ Lịch thi, mở/đóng đăng ký .......... GET/POST /admin/schedule
                 ├─ Danh sách / chi tiết đội ........... GET  /admin/teams, /admin/teams/:id
                 ├─ Xóa đội ............................ POST /admin/teams/:id/delete
                 ├─ Cấp lại token đội .................. POST /admin/teams/:id/token   → requestSync()
                 ├─ Đặt "tên đội trên ForcAD" .......... POST /admin/teams/:id/forcad  → requestSync()
                 └─ Xuất Excel / CSV ................... GET  /admin/export.xlsx | .csv  services/exportService.js
```

Mọi route ở trên theo mẫu: `routes/<x>.js` → `controllers/<x>Controller.js` → `models/{User,Team,Member,Setting,Content}.js` (SQLite) → `views/<x>/*.ejs`.

### 1.3 Đăng ký → tạo/vào đội

```text
Trình duyệt              WEB/routes            WEB/controllers              WEB/models (SQLite)
   │ POST /register ─────► auth.js ───────────► authController.register
   │                                               ├ Setting.isRegistrationOpen()
   │                                               ├ kiểm email, MSSV, mật khẩu ≥ 8
   │                                               └ User.create() ─────────► users
   │ POST /team/create ──► team.js ───────────► teamController.create
   │   (requireContestant)                         ├ validateTeam(), studentIdBlocked()
   │                                               ├ Team.createForCaptain() ► teams + members (sinh token đội)
   │                                               └ forcadSync.requestSync('team-saved')  ──► §1.6
   │ POST /team/join ────► team.js ───────────► teamController.join
   │   mã mời = token đội                          ├ joinBlocked() chống dò mã (giới hạn số lần sai)
   │                                               ├ Team.findByToken(joinCode)
   │                                               └ Team.join(team, user, MAX_MEMBERS) ► members
```

### 1.4 Xem scoreboard (realtime)

```text
GET /scoreboard
└─ WEB/routes/scoreboard.js  sessionTeam() → submitTeam (để khóa ô "Đội của bạn")
   └─ WEB/views/scoreboard.ejs (layout:false)
      ├─ public/arena-ui/arena3d/main.js  → WebGL2 & ≥900px: scene.js, ships.js (3D)
      │                                     ngược lại: public/arena-ui/arena.js (2D)
      ├─ public/js/arena.js               vẽ bảng điểm, đồng hồ tick
      └─ public/js/scoreboard-ui.js       nhật ký, form nộp flag

Dữ liệu:
 ForcAD client-api                        Website                               Trình duyệt
 GET /api/client/tick-status/ ─┐
 GET /api/client/arena/       ─┼──► services/arenaService.js load()
 GET /api/client/teams/       ─┘      - gom 3 API, lọc chỉ giữ trường công khai
                                      - gắn con giáp (config/zodiac.js)
                                      - cache + ETag
                                          │
                                          ├─ GET /scoreboard/stream  (SSE, đẩy khi đổi) ──► arena.js
                                          ├─ GET /scoreboard/state   (JSON dự phòng)
                                          └─ GET /scoreboard/data/{tick-status,teams,arena}
```

Phía ForcAD, 3 API đó nằm ở `BE/services/api/views.py`: `tick_status()` gọi `competition.state()`, `competition.scores()`; `public_arena_data()` trả services/captures/checks.

### 1.5 Nộp flag (chức năng chính của thí sinh)

```text
public/js/scoreboard-ui.js
  │ POST /scoreboard/submit  {flags:[...]}  + CSRF  (KHÔNG gửi token từ trình duyệt)
  ▼
WEB/routes/scoreboard.js
  ├ sessionTeam(req)  → chưa có đội: 401
  ├ kiểm 1..100 flag, mỗi flag ≤ 100 ký tự
  └ PUT http://127.0.0.1:18080/flags/   header X-Team-Token = token đội trong SQLite
        ▼ nginx
  BE/services/http_receiver/views.py
  ├ storage.teams.get_team_id_by_token(token)    sai → "Invalid team token."
  ├ storage.game.get_real_round() == -1          → "Game not started."
  └ judge.process_many(team_id, flags)           BE/lib/flags/judge.py
        └ storage/attacks.py handle_attack()     kiểm tra flag tồn tại, không phải của mình, còn hạn
              └ competition.record_attack()      BE/lib/storage/competition.py
                   ├ round đang mở + accepting()?
                   ├ flag thuộc bài đang chạy, không quá 2 tick
                   ├ INSERT StolenFlags (trùng → FLAG_ALREADY_STOLEN)
                   └ +2 nếu là đội nộp đầu tiên flag đó (first blood), +1 cho đội sau
  ◄── JSON [{msg, flag}] trả ngược về form
```

Lỗi hay gặp: HTTP 429 (nginx giới hạn 2 lần/giây/đội), 503 "Bộ nhận flag chưa kết nối được" (ForcAD tắt), token sai (chưa đồng bộ — xem §1.6).

### 1.6 Đồng bộ token website → ForcAD

Website là nơi **cấp** token đội; ForcAD phải giữ cùng token thì `/flags/` mới nhận.

```text
Khi nào chạy:
  - app.js khởi động                  forcadSync.start()
  - mỗi FORCAD_SYNC_INTERVAL giây     (mặc định 60)
  - teamController.create/save        requestSync('team-saved')
  - adminController.regenerateToken   requestSync('token-regenerated')
  - adminController.saveForcadName    requestSync('forcad-name')
  - tay: cd WEB && npm run sync:forcad -- --apply   (scripts/sync-forcad-tokens.js)

WEB/services/forcadSync.js syncTokens()
  ├ credentials(): FORCAD_ADMIN_* trong .env, trống thì đọc khối admin: trong FAD/config.yml
  ├ POST /api/admin/login/
  ├ GET  /api/admin/teams/
  ├ ghép đội: Team.forcadCandidates() = tên khai riêng → slug tên đội → tên gốc
  └ PUT  /api/admin/teams/<id>/   {token: token website}
```

Trạng thái lượt gần nhất hiện ở trang `/admin/teams/:id` (`forcadSync.statusOf()`).

---

## 2. FORCAD (`FAD/`)

### 2.1 Khởi động và các container

```text
Từ gốc workspace:  python khoi-dong/meko.py server
  └ KD/meko.py server()
     ├ docker compose -f FAD/docker-compose.yml up -d
     ├ chờ postgres (pg_isready)
     └ docker compose exec ticker python /app/scripts/setup_round1.py   (tạo bảng Mekodata*)

Mỗi container web chạy docker_config/services/entrypoint.sh → functions.sh start_${SERVICE}:
```

| Container | Code (trong `BE/`) | Lệnh chạy trong container | Việc |
|---|---|---|---|
| `nginx` | `FAD/docker_config/nginx/` | nginx | Cổng `127.0.0.1:18080`, phân luồng URL, phục vụ `FAD/front/dist` |
| `client-api` | `services/api/` | `gunicorn app:app` | API công khai `/api/client/*` |
| `admin-api` | `services/admin/` | `gunicorn app:app` | API quản trị `/api/admin/*` |
| `http-receiver` | `services/http_receiver/` | `gunicorn app:app` | Nhận flag `PUT /flags/` |
| `events` | `services/events/` | `gunicorn app:app` | Socket.IO đẩy sự kiện |
| `ticker` | `services/ticker/__main__.py` | `cd services && python3 -m ticker` | Vòng lặp tick, gọi checker |
| `celery` | `services/tasks/` | celery worker | Worker gốc ForcAD; `meko check` chạy checker trong container này |
| `initializer` | `scripts/init_db.py` | 1 lần | Tạo DB ban đầu từ `FAD/config.yml` |
| `postgres`, `redis`, `rabbitmq` | — | — | Lưu trữ / hàng đợi |

`ticker`, `client-api`, `admin-api`, `events`, `http-receiver` gắn `./backend:/app:ro` — sửa code Python trong `BE/` chỉ cần **restart container**, không cần build lại. `ticker` và `celery` gắn `./checkers:/checkers`.

### 2.2 Sơ đồ chức năng BTC trên ForcAD

Trang `http://127.0.0.1:18080/` → `FAD/front/dist/index.html` + `FAD/front/public/round-control.js`. Mọi API qua `BE/services/admin/viewsets/__init__.py`, đều gọi `check_session()` (phải đăng nhập).

```text
 BTC (admin ForcAD) ─┬─ Đăng nhập ................... POST /api/admin/login/           authentication.login
                     ├─ Xem trạng thái round ........ GET  /api/admin/round-control/    round_control.round_control_status
                     │                                    → competition.state(), profile(), slot_states()
                     ├─ Chọn bài cho Round 1/2 ...... POST /api/admin/round-control/slots/ {labs}
                     │   (Lưu cấu hình)                   → competition.configure_slots()
                     ├─ Bấm "Round 1" / "Round 2" ... POST /api/admin/round-control/slots/ {slot}
                     │                                    → competition.start_slot()
                     ├─ Bắt đầu / Tạm dừng / Tiếp ... POST /api/admin/round-control/ {running}
                     │                                    → lib/storage/round_control.set_enabled()
                     ├─ Chuẩn bị bài (cũ) ........... POST /api/admin/round1/prepare/ {lab}
                     │                                    → competition.prepare()
                     ├─ Đóng và lưu hồ sơ ........... POST /api/admin/round1/archive/   → archive_competition()
                     ├─ Tải hồ sơ JSON .............. GET  /api/admin/round1/archive/<id>/ → get_archive()
                     ├─ Chơi lại từ đầu ............. POST /api/admin/round1/restart/   → restart_competition()
                     ├─ Dựng lại từ hồ sơ ........... POST /api/admin/round1/recreate/  → recreate_from_archive()
                     ├─ Reset demo .................. POST /api/admin/round-control/reset/ → reset_health_demo()
                     ├─ Quản lý đội/task ............ /api/admin/teams/, /tasks/, /teamtasks/  (viewsets gốc ForcAD)
                     ├─ Nút "Bật bộ cờ" ............. POST /api/admin/host/flag-system/start/ ┐
                     ├─ Nút Collector bật/dừng ...... POST /api/admin/host/collector/{start,stop}/ ├─► §3.6 host_bridge
                     ├─ Nút Gateway thêm/dừng ....... POST /api/admin/host/gateway/{start,stop}/   │
                     └─ Xem trạng thái máy chủ ...... GET  /api/admin/host/status/              ┘
```

Các lệnh lifecycle (`prepare`, `archive`, `restart`, `recreate`, `slots`) chạy trong `competition.lifecycle_lock()` (advisory lock Postgres) để không đụng ticker.

Cùng các API đó có thể gọi bằng dòng lệnh: `FAD/switch_round.py` (login → round-control → archive → prepare), được `meko.py round ...` gọi.

**Nút chỉ đổi trạng thái trong database.** Việc chạy tick do `ticker` đọc trạng thái đó (§2.3).

### 2.3 Ticker — một tick chạy thế nào

File: `BE/services/ticker/__main__.py` → `main()`:

```text
round_control.set_enabled(False)      # ticker khởi động lại luôn TẮT round; BTC phải bấm Bắt đầu lại
while True:
    if competition.configured():
        with lifecycle_lock(required=False): competition.pump()
        lỗi → set_enabled(False) + ghi error "Scheduler gặp lỗi; đã dừng"
    sleep 0.5 giây
```

`competition.pump()` (BE/lib/storage/competition.py) là máy trạng thái; thời gian tính bởi `BE/lib/storage/round_schedule.py`, thông số mỗi bài ở `BE/lib/storage/lab_profile.py`:

```text
                         BTC bấm Round N / Bắt đầu
                                   │
   ┌────────┐  hết 600s   ┌──────────┐            ┌───────────┐
   │preview │ ──────────► │preparing │ ─────────► │ running   │  (~5 phút / tick)
   │xem đề  │             │tick += 1 │            │ - schedule_puts(): cắm flag mọi đội×lỗ
   └────────┘             └──────────┘            │ - run_health_probes() mỗi 30s (SLA)
        ▲                       ▲                 └─────┬─────┘
        │                       │ còn tick              │ tới check_at
   ready (chờ)◄─────────────────┴──────────┐            ▼
                                           │      ┌───────────┐
                                           └──────│ checking  │ verify(): check + get flag ≤2 tick
                                                  │           │ ghi MekodataSLA, cộng SLA
                                                  └─────┬─────┘
                                                        │ hết tick cuối
                                                  ┌───────────┐   hết hạn    ┌──────────┐
                                                  │ draining  │ ───────────► │ finished │ set_enabled(False)
                                                  │ nộp nốt   │              └──────────┘
                                                  └───────────┘
   Bấm Tạm dừng ở bất kỳ pha nào → paused (lưu remaining); Tiếp tục → dời toàn bộ lịch.
```

Thông số Full Rounds (`lab_profile.for_slot`): 10 tick × 300 giây mỗi vòng, xem đề 600 giây, `check_seconds=60`. Vòng 2 có `tick_offset=10` (tick 11–20), flag mẫu `MekoDataCTF{<hex>}` và `seed_with_tick=True`.

### 2.4 Cắm flag (PUT), kiểm tra (CHECK), đọc lại (GET)

```text
ticker: pump()
 ├─ running:  schedule_puts(teams, tasks, tick)        thread pool 12 luồng
 │              └ put_flag((team, task, tick))
 │                 ├ Flag.generate(template của bài) + seed → MekodataPlacements
 │                 ├ CheckerRunner(team, task, flag).put()   BE/lib/helpers/checkers.py (subprocess)
 │                 │      → python /checkers/full_rounds/<lỗ>.py put <ip> <locator> <flag> <vuln>
 │                 └ chỉ khi UP (101): storage.flags.add_flag() → Flags + Redis
 │                    (không UP → không có flag tick đó; thử lại sau 10s)
 ├─ running:  run_health_probes() mỗi 30s → CheckerRunner.check() → MekodataTickHealth.downs
 └─ checking: verify((team, task, tick))
                ├ CheckerRunner.check()
                ├ chưa có flag tick hiện tại → 110 "Current tick flag was not placed"
                ├ CheckerRunner(flag).get() cho flag các tick [tick-2..tick]
                └ cập nhật TeamTasks.status; SLA tick = 1 nếu mọi lỗ UP **và** không probe nào DOWN
```

Đường đi tiếp của `<lỗ>.py` ra CyberRange: xem §3.3–3.4.

Mã kết quả:

| Mã | Nghĩa |
|---|---|
| 101 | UP |
| 102 | CORRUPT (flag mất/sai) |
| 103 | MUMBLE (chức năng sai) |
| 104 | DOWN |
| 110 | Lỗi checker / collector không trả lời / agent không tới được |

### 2.5 Tính điểm

`competition.scores()` (dùng cho `/api/client/tick-status/` và scoreboard):

```text
attack  = số flag cướp được (mỗi lượt StolenFlags) + số lần first-blood   → đội đầu tiên +2, đội sau +1
defense = số flag của mình đã HẾT HẠN mà không ai cướp (protected) + tổng SLA
total   = attack + defense            (điểm thô, không chuẩn hóa)
```

Ghi điểm tấn công ngay lúc nộp: `competition.record_attack()` (§1.5). Ghi SLA ở pha `checking` (§2.4).

### 2.6 API công khai (client-api, `BE/services/api/views.py`)

| URL | Hàm | Dùng bởi |
|---|---|---|
| `/api/client/tick-status/` | `tick_status()` | Website arenaService, `FAD/front/public/tick-display.js` |
| `/api/client/arena/` | `public_arena_data()` | Website arenaService, `FAD/front/public/arena.js` |
| `/api/client/teams/` | `get_teams()` | Website arenaService |
| `/api/client/tasks/`, `/config/`, `/attack_data/`, `/teams/<id>/`, `/ctftime/` | gốc ForcAD | Trang ForcAD, công cụ đội thi |

---

## 3. CYBERRANGE (`LAB/`, `ops/pool141/`, collector, gateway)

### 3.1 Topology sandbox

`LAB/topology.yml` (Sandbox Definition của CyberRangeCZ):

```text
                    WAN meko-wan 100.90.0.0/24
                               │
                        gateway 10.90.0.1 (router)
                               │
          ───────────── meko-lan 10.90.0.0/24 ─────────────
           │              │              │               │
       team1 .11      team2 .12      team3 .13      checker .30
       (Kali)         (Kali)         (Kali)         (Debian 12)
```

Đội tấn công chéo nhau qua LAN; checker chỉ làm theo yêu cầu từ ForcAD.

### 3.2 Dựng sandbox (provisioning)

```text
CyberRangeCZ đọc repo Git chứa NỘI DUNG của labs/full_rounds/
 ├─ topology.yml                    → tạo VM, mạng
 ├─ provisioning/playbook.yml       → Ansible chạy tự động
 │   ├ play 1 (team1..3): cài Apache + Flask
 │   │    chép LAB/app/ → /opt/meko-boutique/, service meko-boutique.service,
 │   │    Apache :80 → 127.0.0.1:8080, sudoers cho đội restart dịch vụ sau khi vá
 │   ├ play 2 (team1..3): kiểm tra HTTP chéo đội /health
 │   ├ play 3 (checker): chép LAB/checker/*.py → /opt/meko-checker/,
 │   │    config templates/checker-config.json.j2 → /etc/meko-checker/config.json,
 │   │    chạy thử agent → yêu cầu mọi đội UP
 │   └ provisioning/round2.yml: dịch vụ Crypto (meko-crypto.service, cổng 9011–9013)
 │        + /opt/crypto-checker/agent.py (nguồn LAB/round2/crypto_ad/)
 ├─ provisioning/group_vars/all.yml mật khẩu đội, staff secret, địa chỉ
 └─ training-definition.json        upload vào Linear Training Definitions
Chạy tay: ansible-playbook -i inventory.yml provisioning/playbook.yml  (đứng ở LAB/)
```

Sau khi pool chạy, tải **SSH Management Access** về `ops/pool141/management-config` (alias `checker`, `team1..3`, đi qua `10.32.8.175` → `man`).

### 3.3 COLLECTOR — gọi thế nào, từ đâu, tới file nào

**Vai trò:** cầu nối giữa checker ForcAD (trong Docker) và agent trên VM checker (trong sandbox). Không có collector → mọi PUT trả `110 "SSH collector unavailable"` → **không có flag**.

**Chạy ở đâu:** trên **host** (không trong Docker), từ **gốc workspace**. Chỉ chạy một bản (có khóa thư mục; bản thứ hai báo `Cannot acquire collector lock`).

**3 cách bật — cùng ra một lệnh:**

```text
(a) CLI:   python khoi-dong/meko.py collector start      → KD/meko.py collector_start()
(b) CLI:   python khoi-dong/meko.py flag                 → docker compose up bộ cờ + collector_start()
(c) Web:   /admin ForcAD nút "Bật bộ cờ"/"Collector"
           round-control.js → POST /api/admin/host/collector/start/
           → BE/services/admin/viewsets/host_bridge.py host_action()
           → http://host.docker.internal:18090 (X-Bridge-Token = BE/.host-bridge-token)
           → KD/host_bridge.py start_collector()

Cả ba sinh tiến trình nền:
  env MEKO_LAB=full_rounds  MEKO_SSH_CONFIG=<gốc>/ops/pool141/management-config
  python platform/ForcAD-demo/collect_checker.py --rpc-only --labs full_rounds,full_rounds/round2
  log: khoi-dong/logs/
(Giá trị LABS/POOL lấy từ KD/cau-hinh.conf qua KD/cau_hinh.py.)
```

**Luồng một yêu cầu (ví dụ PUT lỗ `sqli` cho team2):**

```text
[Docker: ticker]
 competition.put_flag()
  └ CheckerRunner.put()                         BE/lib/helpers/checkers.py
     └ subprocess: python /checkers/full_rounds/sqli.py put 10.90.0.12 <locator> <flag> 1
        (sqli.py = bản chép của FAD/checkers/_template/task.py; tên file = tên lỗ)
        └ FAD/checkers/_shared/forcad_rpc.py main('sqli', root=checkers/full_rounds/rpc)
           └ rpc(): ghi  checkers/full_rounds/rpc/<uuid>.request.json
                         {id, expires=now+40s, payload:{task,action,ip,key,locator,flag}}
                    chờ  <uuid>.response.json tối đa 40 giây (quá → 110 "SSH collector unavailable")
                                 │  (thư mục FAD/checkers/ mount chung host ↔ container)
[Host: collector]                ▼
 FAD/collect_checker.py main() vòng lặp 0,5s quét checkers/<bài>/rpc/*.request.json
  └ process_rpc(path, lab)
     ├ kiểm id 32 hex, còn hạn ≤45s, ip ∈ lab.json teams, task ∈ lab.json tasks
     ├ shared/labconfig.py ssh(): ssh -F ops/pool141/management-config -o BatchMode=yes checker
     │     "sudo -n /usr/bin/python3 /opt/meko-checker/agent.py --config /etc/meko-checker/config.json"
     │     stdin = payload JSON, timeout agent_timeout=35s   (agent_command lấy từ LAB/lab.json)
     └ ghi <uuid>.response.json {status, public, private}   (lỗi SSH → 110 "Sandbox agent unavailable")
                                 │ SSH: 10.32.8.175 → man → checker
[VM checker 10.90.0.30]          ▼
 /opt/meko-checker/agent.py       (nguồn LAB/checker/agent.py)  đọc stdin
  └ forcad.py execute(config, request)
     └ meko_checker.py run() → lớp kiểm tra của lỗ: sqli.py / idor.py / upload.py / jwt.py / backup.py
        └ HTTP tới http://10.90.0.12/  (Meko Boutique của team2, nguồn LAB/app/app.py)
  └ in JSON kết quả ra stdout  ──► ngược lại collector → response.json → forcad_rpc → exit code
```

Vòng 2 Crypto giống hệt, khác ở: thư mục `checkers/full_rounds_crypto/`, `LAB/round2/lab.json` (agent `/opt/crypto-checker/agent.py`), dịch vụ TCP cổng 9011–9013.

**Liên kết lab ↔ thư mục checker:** `"name"` trong `lab.json` = tên thư mục `FAD/checkers/<name>/` = `prefix` trong `lab_profile.py`. Thêm lỗ mới: chép `_template/task.py` thành `<tên lỗ>.py`, thêm vào `tasks` của `lab.json` và `lab_profile.py`.

### 3.4 Agent và ứng dụng đề trên VM

| File nguồn | Cài tới (VM) | Việc |
|---|---|---|
| `LAB/checker/agent.py` | checker: `/opt/meko-checker/agent.py` | Đọc 1 yêu cầu JSON stdin, in kết quả stdout |
| `LAB/checker/forcad.py` | như trên | `execute()` chọn lỗ + hành động |
| `LAB/checker/meko_checker.py` | như trên | Client HTTP, logic check/put/get chung |
| `LAB/checker/{idor,sqli,upload,jwt,backup}.py` | như trên | Cắm/đọc flag theo từng lỗ |
| `LAB/round2/crypto_ad/agent.py`, `protocol.py` | checker: `/opt/crypto-checker/` | Agent vòng 2 |
| `LAB/app/app.py` (+ templates, static, data) | team: `/opt/meko-boutique/` | Web Meko Boutique, 5 lỗ hổng |
| `LAB/round2/crypto_ad/service.py` | team: dịch vụ `meko-crypto` | 3 dịch vụ Crypto |

### 3.5 GATEWAY trung gian

Mở mỗi dịch vụ của đội ra một cổng trên máy BTC để xem/kiểm tra từ LAN mà không vào sandbox.

```text
Bật:  python khoi-dong/meko.py gateway start     hoặc nút "Thêm gateway trung gian" (/admin → host_bridge)
  └ KD/meko.py gateway_start()
     ├ KD/cau_hinh.py gateway_plan(): đội × service_ports từ lab.json mọi bài trong LABS
     │     cổng cấp tuần tự từ 20001  (full_rounds [80], round2 [9011,9012,9013])
     └ ssh -F ops/pool141/management-config -N -L <bind>:20001:10.90.0.11:80 -L ... checker
        bind = GATEWAY_BIND trong cau-hinh.conf (trống = IP LAN của máy)
        PID lưu để dừng; log khoi-dong/logs/gateway.log
Xem bảng cổng: python khoi-dong/meko.py gateway status   hoặc khung trên /admin
```

### 3.6 Cầu nối host (cho các nút trên web)

```text
round-control.js (trình duyệt BTC)
  └ POST /api/admin/host/<action>/        BE/services/admin/viewsets/host_bridge.py
       kiểm session + Origin, action ∈ {flag-system/start, collector/start|stop, gateway/start|stop}
  └ HTTP host.docker.internal:18090        KD/host_bridge.py (chỉ nghe 127.0.0.1)
       kiểm X-Bridge-Token
       ├ flag-system/start → docker compose up postgres redis rabbitmq celery ticker http-receiver
       │                     + start_collector()
       ├ collector/*       → start_collector() / stop_collector()
       ├ gateway/*         → meko.gateway_start() / gateway_stop()
       └ GET /status       → container, collector, SSH tới checker (kiểm định kỳ), gateway
Bật cầu nối: python khoi-dong/meko.py bridge install   (một lần, tự chạy khi đăng nhập)
```

Cầu nối **không** bật được Docker/nginx từ đầu — việc đó dùng `meko.py server`.

---

## 4. Một buổi thi từ đầu đến cuối

```text
 TRƯỚC THI
  [BTC]      CyberRangeCZ: tạo pool từ LAB/ → tải SSH config → ops/pool141/management-config
  [BTC]      sửa khoi-dong/cau-hinh.conf (LABS, POOL)
  [BTC]      cd WEB && npm run seed && npm start                    → website :3000
  [Thí sinh] /register → /team/create hoặc /team/join               → token đội trong SQLite
  [BTC]      python khoi-dong/meko.py server                        → ForcAD :18080
             (forcadSync tự đẩy token website → ForcAD mỗi 60s)
  [BTC]      python khoi-dong/meko.py flag                          → bộ cờ + collector
  [BTC]      python khoi-dong/meko.py check                         → mọi checker phải DAT 101
 TRONG THI
  [BTC]      /admin ForcAD → Điều khiển round → chọn bài → Lưu → Round 1
  [ticker]   preview 10 phút → tick 1..10: put → probe → check/get → SLA
  [Thí sinh] tấn công VM đội khác (10.90.0.1x), vá dịch vụ của mình
  [Thí sinh] /scoreboard → nộp flag → +2/+1
  [Mọi người] /scoreboard xem điểm, tàu bắn, khiên (SSE)
  [BTC]      Round 2 (Crypto, tick 11..20) → kết thúc
 SAU THI
  [BTC]      Đóng và lưu hồ sơ → tải round1-archive-*.json; /admin/export.xlsx website
```

## 5. Tìm chỗ hỏng theo triệu chứng

| Triệu chứng | Nguyên nhân thường gặp | Xem |
|---|---|---|
| Scoreboard "Scoreboard temporarily unavailable" | ForcAD/nginx/client-api tắt | §1.4, `docker compose ps` |
| Nộp flag báo "Invalid team token." | Token chưa đồng bộ, tên đội không ghép được | §1.6, `/admin/teams/:id` |
| Nộp flag báo "Game not started." | Chưa mở round | §2.2 |
| Nộp flag HTTP 500 | Container http-receiver chạy image cũ | `docker compose up -d --build` |
| Bấm Round nhưng không có tick | ticker lỗi/khởi động lại tự tắt round | `docker compose logs ticker`, §2.3 |
| Service `110 SSH collector unavailable` | Collector chưa chạy | §3.3, `meko.py collector status` |
| Service `110 Sandbox agent unavailable` | SSH tới checker lỗi, sai pool | `ops/pool141/management-config`, `meko.py status` |
| `110 Current tick flag was not placed` | PUT tick này không UP | log collector, `meko.py check` |
| Nút "Bật bộ cờ" báo cầu nối chưa chạy | host_bridge tắt | `meko.py bridge install` |
| Gateway tắt ngay sau khi bật | SSH tới pool lỗi | `khoi-dong/logs/gateway.log` |
