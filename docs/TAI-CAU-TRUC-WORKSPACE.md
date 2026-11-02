# Tái cấu trúc workspace: thay đổi, luồng gọi và cách chạy

Tài liệu ghi lại đợt sắp xếp lại workspace ngày 01/11/2026. Nội dung gồm: những gì đã xóa và di chuyển, các file gọi nhau ra sao, và cách chạy từng file.

---

## 1. Tóm tắt thay đổi

### 1.1 Đã xóa

| Thư mục | Lý do |
|---|---|
| `MekoDataCTF-review/` | Giống hệt `checker-update/idor-c-main/` (so bằng mã băm từng file). |
| `mekodata-publish/` | Bản Sandbox Definition cũ: `playbook.yml` thiếu `become_user: web-checker`. Bản phát hành vẫn còn ở `artifacts/releases/mekodata-publish.tar`. |
| `checker-update/idor-c-main/.publish-MekoDataCTF/` | Bản cũ hơn nữa: checker chưa lưu lịch sử SQLite, chu kỳ 30 giây. |
| `.ua/tmp/`, `.ua/intermediate/`, `platform/MekoDataCTF_Website/.ua/.trash-*` | Dữ liệu tạm của Understand-Anything (đã nằm trong `.gitignore`). |

Các bản đã xóa vẫn lấy lại được từ lịch sử git, ví dụ: `git show HEAD:mekodata-publish/README.md`.

Không đụng tới: các file `.dump`, `collector*.log`, `config_backup_*.yml`, `cloudflared.exe` trong ForcAD.

### 1.2 Đã di chuyển

| Đường dẫn cũ | Đường dẫn mới | Vai trò |
|---|---|---|
| `ForcAD-demo/` | `platform/ForcAD-demo/` | Dùng chung |
| `MekoDataCTF_Website/` | `platform/MekoDataCTF_Website/` | Dùng chung |
| `checker-update/idor-c-main/` | `labs/round1/sandbox/` | Riêng lab |
| `round1-lab/` | `labs/round1/service/` | Riêng lab |
| `service-checker/` | `shared/service-checker/` | Dùng chung |

Tên thư mục `ForcAD-demo` được giữ nguyên, nên Docker Compose project vẫn tên `forcad-demo`. Container (`forcad-demo-ticker-1`, `forcad-demo-postgres-1`…) giữ nguyên tên. Dữ liệu Postgres ở `docker_volumes/` di chuyển theo thư mục.

### 1.3 File mới

| File | Nội dung |
|---|---|
| `labs/round1/lab.json` | **Nguồn cấu hình duy nhất** của lab: đội, IP, host SSH, task, file SSH. |
| `shared/labconfig.py` | Đọc `lab.json` và dựng lệnh SSH chung. |
| `labs/_template/` | `lab.json` mẫu và hướng dẫn tạo lab mới. |
| `docs/TAI-CAU-TRUC-WORKSPACE.md` | Tài liệu này. |

### 1.4 Code đã sửa

| File | Trước | Sau |
|---|---|---|
| `labs/round1/service/deploy.py` | `range(1, 5)`, `10.80.0.{10+i}`, `ssh -F pool101-management-config` | Duyệt `LAB['teams']`, gọi `labconfig.ssh(...)` |
| `labs/round1/service/recycle.py` | `HOSTS`, `TEAM_IPS` viết cứng | Lấy từ `deploy.LAB` |
| `labs/round1/service/run_tests.py` | `root.parent / 'ForcAD-demo'` | `root.parents[2] / 'platform' / 'ForcAD-demo'` |
| `platform/ForcAD-demo/collect_checker.py` | `team01–04`, `checkers/round1/rpc`, `ssh -F pool101-management-config` | Đọc từ `lab.json`; **kiểm tra IP/task theo `lab.json`** trước khi gửi qua SSH |
| `platform/ForcAD-demo/checkers/round1/common.py` | `ROOT = /checkers/round1/rpc`; whitelist IP `10.80.0.11–14` | `ROOT = <thư mục của file>/rpc`; chỉ kiểm tra định dạng IPv4. Whitelist chuyển sang collector. |
| `front/public/round-control.js`, `front/dist/round-control.js` | Gợi ý `python round1-lab/recycle.py` | `python labs/round1/service/recycle.py` |
| `.claude/launch.json`, `.understandignore`, README, `adjust_settings.md`, `docs/` | Đường dẫn cũ | Đường dẫn mới |

**Lỗi cũ đã được sửa:** trước đây cả 3 script gọi `ssh -F pool101-management-config` với thư mục làm việc là gốc workspace, nhưng file này không có trong repo (file thật nằm ở `ops/pool101/management-config`). Giờ đường dẫn lấy từ `lab.json` và là đường dẫn tuyệt đối.

**Hành vi được giữ nguyên:** checker ForcAD gửi IP lạ vẫn nhận mã `110`. Trước đây `common.py` từ chối ngay; giờ collector từ chối và trả `110 Sandbox agent unavailable`. Đã thử với `10.80.0.99`.

---

## 2. Cây thư mục

```
atk_def_platform/
├── platform/                         # Dùng chung, không sửa khi thêm lab
│   ├── ForcAD-demo/
│   │   ├── docker-compose.yml        # mount ./checkers → /checkers trong container
│   │   ├── backend/                  # ForcAD + vòng đời Round 1 (lib/storage/round1.py)
│   │   ├── front/                    # Dashboard (Vite) → front/dist do nginx phục vụ
│   │   ├── checkers/
│   │   │   ├── round1/               # common.py, health.py, idor.py, sqli.py, upload.py, rpc/
│   │   │   └── mekodata_bridge/      # request.json, latest.json, responses/
│   │   └── collect_checker.py        # chạy trên Windows, cầu nối sang VM checker
│   └── MekoDataCTF_Website/          # Website đăng ký đội (Node.js, SQLite)
├── labs/
│   ├── _template/                    # lab.json mẫu + README
│   └── round1/
│       ├── lab.json
│       ├── sandbox/                  # CyberRange: topology.yml, provisioning/, app/, checker/
│       └── service/                  # webservice.py, agent.py, deploy.py, recycle.py, test
├── shared/
│   ├── labconfig.py
│   └── service-checker/
├── ops/pool101/                      # 🔒 management-config, known-hosts
├── tools/  models/  docs/  assets/  artifacts/
└── adjust_settings.md
```

---

## 3. Các file gọi nhau như thế nào

### 3.1 Cấu hình

```
labs/round1/lab.json
        │  đọc bởi
        ▼
shared/labconfig.py ── load(), ssh()
        │
        ├── labs/round1/service/deploy.py      (labconfig.load(thư mục lab cha))
        │       └── labs/round1/service/recycle.py   (import deploy → dùng deploy.LAB)
        └── platform/ForcAD-demo/collect_checker.py  (labconfig.load() → $MEKO_LAB, mặc định round1)
```

Script nạp `labconfig` bằng cách thêm `<gốc workspace>/shared` vào `sys.path`, nên chạy từ thư mục nào cũng được.

### 3.2 Một lượt kiểm tra (tick) của ForcAD

```
ForcAD (Docker, container celery/ticker)
  └─ chạy /checkers/round1/idor.py  check|put|get  <ip> [...]
        └─ common.rpc(): ghi checkers/round1/rpc/<id>.request.json
                │  (thư mục mount chung giữa container và Windows)
                ▼
Windows: collect_checker.py (vòng lặp 0,5 giây)
  ├─ process_rpc(): kiểm tra id, hạn, IP ∈ lab.json, task ∈ lab.json
  │     └─ ssh -F ops/pool101/management-config checker
  │            sudo python3 /opt/round1/agent.py --config /etc/round1/agent.json
  │                 └─ agent.py gọi HTTP tới webservice.py trên attackerN (10.80.0.11–14)
  │     └─ ghi <id>.response.json  → common.rpc() đọc → trả mã 101/102/103/104/110 cho ForcAD
  └─ process_request(): khi có checkers/mekodata_bridge/request.json
        └─ ssh … checker  sudo -u web-checker python3 /opt/web-checker/web_health.py --json --database …
        └─ ghi mekodata_bridge/responses/<id>.json và latest.json
```

### 3.3 Cài đặt và tái tạo lab

```
deploy.py --apply
  ├─ đọc/tạo labs/round1/service/.secrets/teams.json (token admin web theo IP)
  ├─ với mỗi team trong lab.json: install(host) → SSH → ghi /opt/round1/webservice.py, /etc/round1/web.json,
  │                                                  drop-in systemd attacker-http@<host>
  └─ install(checker_host) → /opt/round1/agent.py, /etc/round1/agent.json

recycle.py --archive-id <UUID>
  ├─ đăng nhập Admin API ForcAD (http://127.0.0.1:18080), xác minh hồ sơ đã lưu
  ├─ deploy.install(..., reset_storage=True) cho từng team → xóa /var/lib/round1-web
  ├─ cài lại agent, health check từng IP qua agent
  └─ POST /api/admin/round1/recreate/ → ForcAD reset tick/điểm/flag
```

### 3.4 Sandbox CyberRange

CyberRange đọc `labs/round1/sandbox/topology.yml` để tạo VM và mạng, rồi chạy `provisioning/playbook.yml` bằng Ansible. Playbook chép file theo đường dẫn tương đối (`{{ playbook_dir }}/../app/…`, `../checker/…`), nên phải giữ nguyên cấu trúc bên trong `sandbox/`. Repo Git của Sandbox Definition phải lấy **nội dung** thư mục này làm gốc.

---

## 4. Cách chạy từng file

Các lệnh dưới đây chạy trong PowerShell tại gốc workspace `atk_def_platform/`, trừ khi ghi khác.

### 4.1 Cấu hình chung

| File | Cách dùng |
|---|---|
| `labs/round1/lab.json` | Không chạy. Sửa để đổi đội/IP/task/file SSH. Các trường: `name` (trùng tên thư mục `checkers/<name>/`), `ssh_config`, `checker_host`, `tasks`, `teams[{name, host, ip}]`. |
| `shared/labconfig.py` | Không chạy trực tiếp. `load(lab=None)` trả về dict cấu hình (thêm `dir`, `ssh_config` tuyệt đối). `ssh(config, host, remote)` trả về argv `ssh -F … -o BatchMode=yes -o ConnectTimeout=8 host remote`. |

Biến môi trường:

```powershell
$env:MEKO_LAB = 'round1'                          # lab collector dùng (mặc định round1)
$env:MEKO_SSH_CONFIG = 'ops/pool101/management-config'  # ghi đè ssh_config, tương đối gốc workspace hoặc tuyệt đối
```

Kiểm tra nhanh cấu hình đọc được:

```powershell
cd labs/round1/service; python -c "import deploy; print(deploy.LAB)"; cd ../../..
```

### 4.2 ForcAD (`platform/ForcAD-demo/`)

```powershell
cd platform/ForcAD-demo
docker compose up -d                       # khởi động; dashboard http://127.0.0.1:18080
docker compose build <dịch vụ>; docker compose up -d --no-deps <dịch vụ>   # sau khi sửa backend
cd front; npm run build; cd ..; docker compose up -d --no-deps nginx       # sau khi sửa giao diện
```

| File | Cách chạy | Ghi chú |
|---|---|---|
| `collect_checker.py` | `python platform/ForcAD-demo/collect_checker.py` | Chạy **một** tiến trình trên Windows, ngoài Docker. Không tự chạy lại sau khi khởi động máy. `--once`: xử lý một lượt rồi thoát. |
| `checkers/round1/<task>.py` | Do ForcAD gọi trong container: `<task>.py check <ip>` hoặc `<task>.py put/get <ip> <flag_id> <flag> <vuln>` | Thử tay: `python platform/ForcAD-demo/checkers/round1/idor.py check 10.80.0.11` (cần collector đang chạy, nếu không sẽ trả 110 sau 40 giây). |
| `checkers/round1/common.py` | Không chạy trực tiếp | Mỗi file task chỉ gọi `main('<task>')`. |
| `*.bat` | Mở scoreboard | Nút Bắt đầu/Dừng đã chuyển lên dashboard. |

### 4.3 Lab Round 1 (`labs/round1/service/`)

| File | Chạy ở đâu | Lệnh |
|---|---|---|
| `deploy.py` | Windows | `python labs/round1/service/deploy.py --apply` (không có `--apply` thì chỉ in mô tả) |
| `recycle.py` | Windows | `python labs/round1/service/recycle.py --archive-id <UUID> [--api http://127.0.0.1:18080]`. Lệnh sẽ hỏi tài khoản admin ForcAD và yêu cầu gõ `RECREATE`. |
| `run_tests.py` | Windows, Docker đang chạy | `python labs/round1/service/run_tests.py`. Tạo DB/Redis tạm trong mạng `forcad-demo`, chạy `test_round1` trong image `forcad-demo-ticker`, rồi xóa tài nguyên tạm. |
| `test_round1.py` | Trong container (qua `run_tests.py`) | Chạy trực tiếp trên Windows sẽ báo `PermissionError` khi dọn file SQLite tạm. Đây là giới hạn khóa file của Windows. |
| `webservice.py` | VM attackerN (systemd) | `python3 /opt/round1/webservice.py --config /etc/round1/web.json --host 0.0.0.0 --port 80` |
| `agent.py` | VM checker | `python3 /opt/round1/agent.py --config /etc/round1/agent.json`, nhận một lệnh JSON qua stdin |
| `.secrets/teams.json` | 🔒 | Do `deploy.py` tạo. **Không xóa**: `recycle.py` từ chối chạy nếu thiếu file này. |

### 4.4 Sandbox (`labs/round1/sandbox/`)

| File | Ai dùng |
|---|---|
| `topology.yml`, `training-definition.json` | CyberRange |
| `provisioning/playbook.yml`, `group_vars/all.yml` 🔒, `files/*` | Ansible khi provisioning |
| `app/portal.py`, `app/attacker_http.py` | Chạy trên VM qua `servicedesk.service`, `attacker-http@.service` |
| `checker/web_health.py`, `web_targets.json` | Chạy trên VM checker qua `web-checker.service` (60 giây/lượt). Collector gọi thêm khi ForcAD yêu cầu. |
| `tests/` | `cd labs/round1/sandbox; python -m unittest discover -s tests -v` (cần `pip install -r requirements-dev.txt` để có PyYAML) |

### 4.5 Service checker độc lập (`shared/service-checker/`)

```powershell
cd shared/service-checker
python -m unittest test_web_health
$env:PORTAL_SOURCE = (Resolve-Path ../../labs/round1/sandbox/app/portal.py); python -m unittest test_checker
```

Chạy thật trên máy có đường tới `lab-lan` (Linux): đặt mật khẩu `CHECKER_TEAM01_PASSWORD` … `CHECKER_TEAM04_PASSWORD` dưới dạng nhập ẩn, rồi `python3 checker.py --config config.teams.json`. Xem `shared/service-checker/README.md`.

### 4.6 Website (`platform/MekoDataCTF_Website/`)

```powershell
cd platform/MekoDataCTF_Website
npm install
npm start               # hoặc npm run dev; cổng mặc định 3000 (biến PORT)
npm run seed            # dữ liệu mẫu
npm run sync:forcad     # xem trước đồng bộ token (website đang chạy đã tự đồng bộ; thêm -- --apply để ghi ngay)
```

Cấu hình trong `.env` (mẫu: `.env.example`): `PORT`, `NODE_ENV`, `SESSION_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, và tùy chọn `DB_FILE`. `.claude/launch.json` đã trỏ sang `platform/MekoDataCTF_Website/app.js`.

---

## 5. Tạo lab mới

Xem [labs/_template/README.md](../labs/_template/README.md). Tóm tắt những gì phải sửa:

| Thành phần | Có phải sửa không |
|---|---|
| `platform/ForcAD-demo/collect_checker.py`, `shared/labconfig.py`, `checkers/<lab>/common.py`, `deploy.py`/`recycle.py` | **Không**: chỉ đọc `lab.json` |
| `labs/<lab>/lab.json` | Có |
| `sandbox/topology.yml`, `group_vars/all.yml`, `checker/web_targets.json` | Có: CyberRange/Ansible đọc trực tiếp |
| `service/webservice.py`, `agent.py` | Có: đây là nội dung bài lab |
| `backend/lib/storage/round1.py`, `round_control.py` | ⚠️ **Hiện vẫn viết cứng** `/checkers/round1/`, task `idor/sqli/upload` và 4 IP `10.80.0.11–14`. Lab mới khác những giá trị này thì phải sửa backend và build lại container. |

Bước tiếp theo nên làm nếu cần tạo nhiều lab: mount `labs/` vào container (chỉ đọc) và cho `round1.py` đọc `lab.json`, để backend cũng không cần sửa.

---

## 5b. Quy ước tên đội: website ↔ ForcAD ↔ máy ảo

Thêm ngày 02/11/2026. Một đội có **một khóa tên** dùng ở mọi nơi:

```
Tên đội đăng ký (website)  "Hà Nội #1"
        │  Team.forcadNameOf(team) = "Tên đội trên ForcAD" (nếu BTC khai) hoặc Team.slugOf(tên đội)
        ▼
khóa  "ha-noi-1"  ──►  đội ForcAD tên "ha-noi-1" (token = token website, qua sync:forcad)
                  ──►  labs/<lab>/lab.json  teams[].name = host = "ha-noi-1"  (qua export:lab)
                  ──►  tên VM trong sandbox/topology.yml, alias SSH trong ops/pool101/management-config
```

| File | Thay đổi |
|---|---|
| `platform/MekoDataCTF_Website/models/Team.js` | Thêm `slugOf(name)` và `forcadCandidates(team)`. `forcadNameOf` mặc định trả về slug thay cho tên gốc. |
| `routes/scoreboard.js`, `views/scoreboard.ejs`, `public/js/world.js`, `public/css/world.css` | Form nộp flag: "Đội của bạn" **khóa** theo đội đăng nhập, khớp với danh sách đội ForcAD theo thứ tự tên khai riêng → slug → tên gốc. "Đội mục tiêu" chỉ liệt kê các đội ForcAD khác. Nếu không khớp, hiện cảnh báo đỏ kèm tên đội ForcAD cần tạo. Cảnh báo chỉ hiện khi đã có dữ liệu thật từ ForcAD. |
| `scripts/sync-forcad-tokens.js`, `services/forcadSync.js` | Ghép đội theo cùng thứ tự trên. Đội ForcAD cũ đặt theo tên gốc vẫn ghép được. Đồng bộ tự động xem [DONG-BO-TOKEN-FORCAD.md](DONG-BO-TOKEN-FORCAD.md). |
| `scripts/export-lab-teams.js` (mới), `npm run export:lab` | In hoặc ghi `teams` của `lab.json` từ danh sách đăng ký. Báo lỗi nếu tên rỗng sau khi bỏ ký tự đặc biệt, không hợp lệ làm hostname, hoặc hai đội trùng slug. |
| `controllers/adminController.js`, `views/admin/team.ejs`, `locales/*.json` | Ô "Tên đội trên ForcAD" gợi ý slug mặc định, kèm giải thích đây cũng là tên VM. |
| `shared/labconfig.py` | `host` mặc định bằng `name`. Lab round1 vẫn khai `host: attacker1…` nên không đổi hành vi. |

Cách chạy:

```powershell
cd platform/MekoDataCTF_Website
npm run export:lab                                   # xem trước danh sách teams
npm run export:lab -- --write round2 --start 11      # ghi vào labs/round2/lab.json
$env:FORCAD_ADMIN_PASSWORD = '...'; npm run sync:forcad            # xem kế hoạch ghép + đồng bộ token
npm run sync:forcad -- --apply                                    # ghi token sang ForcAD
```

Lab round1 hiện tại: đội ForcAD vẫn là `team01–04`. Để form khóa đúng đội, BTC khai "Tên đội trên ForcAD" = `team01`… cho từng đội website; website tự đồng bộ token ngay sau khi lưu.

Từ 02/11/2026 token được **đồng bộ tự động**: khi website khởi động, định kỳ 60 giây, sau mỗi thay đổi đội trên website, và cuối `recycle.py`. Chi tiết: [DONG-BO-TOKEN-FORCAD.md](DONG-BO-TOKEN-FORCAD.md).

Phần **chưa tự động hóa**: tạo đội trên ForcAD theo `lab.json`, đặt tên VM trong `topology.yml`, alias trong file SSH. Backend `round1.py` vẫn viết cứng 4 IP (xem mục 5).

---

## 5c. Nút "Bắt đầu lại từ tick 0" trên dashboard ForcAD

Thêm ngày 02/11/2026. Nút nằm trong khung "Điều khiển round" (`front/public/round-control.js`, chép sang `front/dist/`).

| Chế độ | Nút hiện khi | Bấm thì |
|---|---|---|
| Round 1 | Round đang dừng, đã chạy ít nhất 1 tick (`paused`, `finished`, hoặc `ready` với tick > 0), chưa đóng hồ sơ | `POST /api/admin/round1/restart/` (`{"confirm":"RESTART ROUND1"}`), rồi `POST /api/admin/round-control/` `{"running":true}` |
| Bản health (chưa chuẩn bị Round 1) | Round đang dừng | `POST /api/admin/round-control/reset/` rồi bắt đầu |

`round1.restart_competition()` (`backend/lib/storage/round1.py`) làm các bước sau:

1. Từ chối nếu round đang bật, hoặc mới dừng chưa đủ `RESTART_QUIET_SECONDS` = 45 giây (bằng `checker_timeout`, để PUT của lượt cũ không ghi vào tick 1 của lượt mới). Khi kết thúc tự nhiên, ForcAD tự tắt round, nên cũng phải chờ 45 giây.
2. Gọi `archive_competition()`: lưu snapshot vào `MekodataArchives`. Link "Tải hồ sơ lượt trước" xuất hiện trên dashboard.
3. Xóa flag, capture, SLA, lịch sử tick; đưa `TeamTasks` về 0, tick về 0, phase về `ready`. **Giữ** đội, task, `configured` và **token đội**, nên website không phải đồng bộ lại.
4. Xóa cache Redis liên quan (không xóa `team:token:*`).

**Không** dọn dữ liệu trên VM đội: bản vá của đội và file cũ vẫn còn, còn flag cũ đã mất hiệu lực vì bị xóa khỏi DB. Muốn dọn sạch VM thì dùng quy trình cũ: "Đóng và lưu hồ sơ", rồi chạy `recycle.py`.

Phần xóa dữ liệu dùng chung với `recreate_from_archive` qua `_clear_scores()` và `_flush_score_cache()`. Hành vi tái tạo không đổi: vẫn sinh token mới và đặt `configured=false`.

Kiểm thử: `test_round1.LifecycleTest` có thêm đoạn kiểm tra bắt đầu lại sau khi kết thúc. Đoạn này kiểm tra: bị từ chối khi chưa đủ 45 giây; hồ sơ lưu đủ 180 flag; điểm và flag về 0; token giữ nguyên; bắt đầu lại sinh 12 flag ở tick 1. Chạy bằng `python labs/round1/service/run_tests.py`.

---

## 6. Việc cần làm sau khi di chuyển

1. `cd platform/ForcAD-demo; docker compose up -d`. Các container cũ (nếu còn) đang trỏ tới đường dẫn cũ, nên cần tạo lại.
2. Chạy `python labs/round1/service/run_tests.py` để kiểm thử tích hợp. Lần tái cấu trúc này chưa chạy được bước này vì Docker đang tắt.
3. Phân tích lại bản đồ Understand-Anything (`.ua/`): bản hiện tại vẫn ghi đường dẫn cũ.
4. Nếu chạy trên máy khác: sửa `UserKnownHostsFile` và `IdentityFile` trong `ops/pool101/management-config`.
