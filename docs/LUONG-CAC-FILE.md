# Luồng đi qua các file

Tài liệu này cho biết mỗi thao tác đi qua những file nào, từ trình duyệt đến VM. Ví dụ dùng lab Meko Boutique. Cách chạy từng lệnh xem [HUONG-DAN-KHOI-DONG.md](HUONG-DAN-KHOI-DONG.md).

Viết tắt đường dẫn:

| Viết tắt | Đường dẫn |
|---|---|
| `WEB/` | `platform/MekoDataCTF_Website/` |
| `FAD/` | `platform/ForcAD-demo/` |
| `LAB/` | `labs/meko_boutique/` |

## 1. Bức tranh chung

```text
Đội thi ── trình duyệt ──► Website :3000 (WEB/)
                               │  HTTP
BTC ───── trình duyệt ──► Nginx :18080 (FAD/, Docker)
                               │
             ┌─────────────────┼──────────────────┐
         client-api        admin-api         http-receiver
          (đọc dữ liệu)   (điều khiển round)   (nhận flag)
             └─────────────────┼──────────────────┘
                     PostgreSQL + Redis
                               ▲
                            ticker ── chạy tick, gọi checker
                               │  file JSON trong FAD/checkers/meko_boutique/rpc/
                               ▼
                     collect_checker.py (Windows)
                               │  SSH
                               ▼
                     VM checker: agent.py
                               │  HTTP trong LAN lab
                               ▼
                     Web của từng đội (10.90.0.11–13)
```

Website không kết nối thẳng tới database ForcAD. Mọi dữ liệu đi qua API của nginx.

## 2. Website khởi động

```text
npm start
└─ WEB/app.js
   ├─ WEB/.env                     cấu hình cổng, khóa phiên, FORCAD_URL
   ├─ WEB/config/database.js       mở SQLite data/mekodata.db, chạy config/schema.sql
   ├─ WEB/middlewares/             i18n.js → locals.js → csrf.js
   ├─ WEB/routes/                  scoreboard.js, index.js, auth.js, team.js, admin.js
   └─ WEB/services/forcadSync.js   start(): đồng bộ token khi khởi động và mỗi 60 giây
```

`locals.js` xác định người dùng và đội của phiên. `middlewares/auth.js` → `sessionTeam()` trả về đội đó cho các route.

## 3. Đội xem scoreboard

**Tải trang:**

```text
GET /scoreboard
└─ WEB/routes/scoreboard.js → sessionTeam(), Team.forcadCandidates()
   └─ WEB/views/scoreboard.ejs (layout:false)
      ├─ public/arena-ui/dashboard.css, scoreboard.css
      ├─ public/arena-ui/arena3d/main.js
      │  ├─ màn hình rộng từ 900 px và có WebGL2 → arena3d/scene.js, ships.js, vendor/three/
      │  └─ trường hợp còn lại → arena-ui/arena.js (bản 2D)
      ├─ public/js/scoreboard-ui.js
      └─ public/js/arena.js
```

**Dữ liệu trực tiếp:**

```text
FAD/backend/services/api/views.py        /tick-status/, /teams/, /arena/
   │  round1.scores(), round1.state() trong FAD/backend/lib/storage/competition.py
   ▼
WEB/services/arenaService.js             load(): gom 3 API, cache 1,5 giây, lọc trường công khai
   ▼
WEB/routes/scoreboard.js                 /scoreboard/stream (SSE), /scoreboard/state (dự phòng)
   ▼
public/js/arena.js                       vẽ bảng điểm, đồng hồ; phát sự kiện 'arena-state'
   ▼
public/js/scoreboard-ui.js               nhật ký, trạng thái service; phát 'crypto-range:state'
   ▼
public/arena-ui/arena3d/scene.js         tàu bắn, bật khiên
```

## 4. Đăng nhập đội và đồng bộ token

**Đăng nhập:**

```text
POST /login hoặc /login/token
└─ WEB/routes/auth.js → WEB/controllers/authController.js
   └─ WEB/models/User.js hoặc Team.findByToken()
```

**Đồng bộ token sang ForcAD:**

```text
Khởi động, mỗi 60 giây, hoặc khi đội thay đổi
(WEB/controllers/teamController.js, adminController.js gọi requestSync())
└─ WEB/services/forcadSync.js → syncTokens()
   ├─ đọc mật khẩu admin từ FAD/config.yml nếu .env không khai
   ├─ POST /api/admin/login/
   ├─ GET  /api/admin/teams/
   ├─ ghép đội bằng Team.forcadCandidates(): tên khai riêng → slug → tên gốc
   └─ PUT  /api/admin/teams/<id>/    ghi token website sang ForcAD
```

`npm run sync:forcad` chạy cùng logic qua `WEB/scripts/sync-forcad-tokens.js`. Chỉ khi thêm `--apply` mới ghi.

## 5. Đội nộp flag

```text
public/js/scoreboard-ui.js                    form gửi flag kèm CSRF, không gửi token
└─ POST /scoreboard/submit
   └─ WEB/routes/scoreboard.js                lấy token từ đội của phiên
      └─ PUT /flags/ (X-Team-Token)
         └─ FAD/backend/services/http_receiver/views.py    token → team_id
            └─ FAD/backend/lib/flags/judge.py
               └─ FAD/backend/lib/storage/attacks.py       handle_attack(): kiểm tra flag
                  └─ FAD/backend/lib/storage/competition.py     record_attack(): +1 đội tấn công, −1 đội mất flag
```

Kết quả trả ngược về form. Capture mới xuất hiện trên sân đấu qua luồng ở mục 3.

## 6. BTC điều khiển round

```text
FAD/front/dist/index.html → FAD/front/public/round-control.js (nút trên dashboard)
├─ Chuẩn bị Meko  → POST /api/admin/round1/prepare/
│                   └─ FAD/backend/services/admin/viewsets/round_control.py → round1.prepare()
│                      └─ FAD/backend/lib/storage/lab_profile.py  task, số tick, mẫu flag của lab
├─ Bắt đầu, Dừng  → POST /api/admin/round-control/
│                   └─ round_control.py (viewset) → FAD/backend/lib/storage/round_control.py set_enabled()
└─ Đóng và lưu    → POST /api/admin/round1/archive/ → round1.archive_competition()
```

Nút chỉ đổi trạng thái trong database. Ticker đọc trạng thái đó và chạy tick ở mục 7.

## 7. Một tick của ticker

`FAD/backend/services/ticker/__main__.py` gọi `round1.pump()` mỗi 0,5 giây. `round_schedule.py` tính thời điểm chuyển pha.

Ticker khởi động lại hoặc `pump()` gặp lỗi đều tắt round. BTC phải kiểm tra rồi bấm **Bắt đầu** để chạy tiếp.

| Pha | Việc làm | Hàm trong `competition.py` |
|---|---|---|
| `ready` | Chờ tới tick kế tiếp, rồi tăng số tick | `pump()` |
| `preparing` | Đặt round hiện tại, chuyển sang `running` | `pump()` |
| `running` | Sinh flag và đặt lên từng đội | `schedule_puts()` → `put_flag()` |
| `checking` | Kiểm tra service, đọc lại flag, chấm SLA | `verify()`, ghi `MekodataSLA` |
| `draining` | Cửa sổ nộp flag cuối sau tick cuối | `pump()` |
| `finished` | Kết thúc, tắt round | `round_control.set_enabled(False)` |

**Đường đi của mỗi lệnh `check`, `put`, `get`:**

```text
FAD/backend/lib/helpers/checkers.py        CheckerRunner chạy script checker
└─ FAD/checkers/meko_boutique/<loại>.py    idor, sqli, upload, jwt, backup
   └─ FAD/checkers/meko_boutique/common.py rpc(): ghi <id>.request.json vào rpc/, chờ tối đa 40 giây
      └─ FAD/collect_checker.py            process_rpc(): đọc request (trên Windows)
         └─ shared/labconfig.py            ssh(): dựng lệnh SSH từ LAB/lab.json
            └─ VM checker /opt/meko-checker/agent.py     (nguồn: LAB/sandbox/checker/agent.py)
               └─ forcad.py → meko_checker.py run() → idor.py, sqli.py, upload.py, jwt.py, backup.py
                  └─ HTTP tới web đội                    (nguồn: LAB/sandbox/app/app.py)
```

Kết quả đi ngược lại: agent in JSON → collector ghi `<id>.response.json` → `common.py` đọc và trả mã cho ForcAD.

| Mã | Nghĩa |
|---|---|
| 101 | UP |
| 102 | CORRUPT |
| 103 | MUMBLE |
| 104 | DOWN |
| 110 | Lỗi checker hoặc collector không phản hồi |

## 8. Cấu hình nằm ở đâu

| File | Quyết định | Ai đọc |
|---|---|---|
| `WEB/.env` | Cổng website, khóa phiên, `FORCAD_URL` | `WEB/app.js`, `arenaService.js`, `forcadSync.js` |
| `FAD/config.yml` | Tài khoản admin, cấu hình game ForcAD | `forcadSync.js`, backend ForcAD |
| `FAD/backend/lib/storage/lab_profile.py` | Task, số tick, thời lượng, mẫu flag của từng lab | `competition.py` |
| `FAD/backend/lib/storage/round_schedule.py` | Quy tắc tính thời gian tick | `competition.py` |
| `LAB/lab.json` | Đội, IP, file SSH, lệnh agent | `shared/labconfig.py`, `collect_checker.py` |
| `ops/pool139/management-config` | Alias SSH tới VM | Lệnh `ssh` do `labconfig.py` dựng |
| Biến `MEKO_LAB` | Collector phục vụ lab nào | `shared/labconfig.py` |
| `/etc/meko-checker/config.json` trên VM | URL đội, mật khẩu staff | `agent.py` |

## 9. Tìm chỗ hỏng theo triệu chứng

| Triệu chứng | Xem ở đâu |
|---|---|
| Scoreboard báo mất kết nối | Nginx và `client-api` (mục 3) |
| Đội thấy cảnh báo chưa ghép | `forcadSync.js`, tên đội (mục 4) |
| Nộp flag báo token sai | Đồng bộ token (mục 4), `http_receiver/views.py` (mục 5) |
| Bấm Bắt đầu nhưng không có tick | Log `ticker`, `round_control.py` (mục 6, 7) |
| Service báo `SSH collector unavailable` | `collect_checker.py` chưa chạy hoặc sai `MEKO_LAB` (mục 7) |
| Service báo `Sandbox agent unavailable` | SSH tới VM checker, `management-config` (mục 7) |

Tài liệu được đối chiếu với mã nguồn ngày 05/11/2026 bằng cách đọc code. Luồng scoreboard và nộp flag đã chạy thử với ForcAD giả; các luồng qua ForcAD thật chưa chạy lại trong đợt này.
