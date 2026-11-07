# Nhật ký thay đổi: Meko Boutique và ForcAD

Cập nhật: 07/11/2026. Tài liệu ghi lại những gì đã đổi để nối lab Meko Boutique vào ForcAD,
kết quả rà soát tick, và phần chưa được kiểm chứng. Chưa có thay đổi nào được commit.

## 1. Tick hoạt động thế nào

Bộ điều phối là `pump()` trong `platform/ForcAD-demo/backend/lib/storage/round1.py`, được ticker gọi
mỗi 0,5 giây. Quy tắc thời gian nằm trong `round_schedule.py`, số liệu của từng lab trong `lab_profile.py`. Trạng thái lưu trong bảng `MekodataRound1`.

```text
ready → preparing → running → checking → ready ...
                                  └ sau tick 10 → draining → finished
```

| Pha | Việc xảy ra |
|---|---|
| `preparing` | Tăng tick, cập nhật số round, nạp lại cache flag, đặt hạn `round_time` |
| `running` | Nạp flag (`put`), cập nhật attack data, nhận flag đội nộp |
| `checking` | Chạy `check` và `get`, chấm SLA. Meko vẫn nhận flag trong pha này |
| `ready` | Meko chờ tới hết tick, vẫn nhận flag |
| `draining` | Nhận flag sau tick cuối. Meko: 0 tick, round1: 2 tick |
| `paused` | Lưu thời gian còn lại, tiếp tục đúng chỗ khi bật lại |

Thông số Meko: một round đúng 50 phút, 10 tick 300 giây, mỗi đội 5 flag mỗi tick, kiểm tra trong 60 giây cuối tick,
không có giai đoạn nhận flag cuối. Flag nộp được ở tick tạo và 2 tick sau (`flag_lifetime = 2`). Round1 giữ logic cũ:
kiểm tra sau tick và thêm 2 tick nhận flag.

Định dạng flag do `Flag.generate` của ForcAD sinh: `MekoDataCTF{30 ký tự A-Z0-9}`.

**Lab không có khái niệm tick.** Mỗi tick chỉ thêm dữ liệu vào website, code và bản vá giữ nguyên.

**Khối lượng mỗi tick của Meko:** 15 `put`, sau đó tối đa 60 lệnh (`check` và 3 `get` cho 15 cặp đội, task),
chạy 4 luồng. Đo trên app local: mỗi lệnh 0,03–0,64 giây, chưa tính SSH. Thời gian SSH qua hai máy
trung gian chưa đo được.

## 2. Lỗi tìm thấy khi rà soát

| Lỗi | Hậu quả | Cách sửa |
|---|---|---|
| Khóa `flags_cached` không hết hạn, còn từng flag hết hạn sau `flag_lifetime × round_time × 2` | Tạm dừng lâu, flag còn hiệu lực bị báo `FLAG_INVALID` | `refresh_flag_cache()` khi mở tick và khi tiếp tục sau tạm dừng |
| Database đã cấu hình round1 thì nút Chuẩn bị bị ẩn | Không chuyển được sang Meko trên giao diện | `leave_archived_lab()`, hiện nút của lab khác sau khi đóng và lưu hồ sơ |
| Trạng thái luôn ghi "Round 1" | Nhầm lab khi chạy Meko | Hiển thị theo `lab` |
| Cột `Flags.flag` chỉ 32 ký tự, flag Meko dài 43 | `put` thành công trên web đội nhưng ForcAD không lưu được, mọi task báo `Current tick flag was not placed` | Nới thành `VARCHAR(64)` trong `create_tables.sql` và `ensure_schema()`, thêm test so giới hạn cột với mọi định dạng flag |
| Ansible đổi chuỗi JSON ở `stdin` thành dict Python khi chạy thử agent | Provisioning lỗi `JSONDecodeError` ở VM `checker`, không phải lỗi agent hay mạng | Thêm khoảng trắng đầu chuỗi `stdin` trong `playbook.yml`, đã tái hiện và kiểm tra bằng Ansible 2.16.14 |

## 3. Thay đổi trong `labs/meko_boutique` (thư mục mới)

Sao từ `labs/fashion_shop`, source của thư mục đó không bị sửa.

**App (`sandbox/app/`)**
- Bỏ tick, tự đổi flag, `/api/checker/flag/<task>`, `/api/collection`.
- Mỗi flag là một bản ghi riêng: `orders.memo`, `collection_notes`, `simulation/private/<token>.json`, `vip_offers`, `reconciliation_notes`.
- Tách `catalog.sqlite3` khỏi `shop.sqlite3`.
- Thêm `/account/notes`, `/outfits/<token>`, `/member/offers/<id>`, `/staff/vip`, `/staff/reconciliation`.
- Bản vá backup chỉ chặn khách, nhân viên vẫn tải được export.

**Checker (`sandbox/checker/`)**
- `meko_checker.py`, `forcad.py`, `agent.py`, 5 script dòng lệnh, `config.example.json`.

**Hạ tầng**
- `lab.json`, VM `checker` tại `10.90.0.30`, play cài agent, template `checker-config.json.j2`.
- `meko_staff_secret` sinh mật khẩu staff riêng từng đội, thay `meko_staff_password`.
- Đội được sửa `/opt/meko-boutique` và restart dịch vụ. Bỏ `meko_checker_key`, `meko_tick_seconds`.

**Test và tài liệu**
- `tests/test_functional.py`, `test_checker.py`, `test_forcad_integration.py`, `test_tick_flow.py`, `test_round_schedule.py`.
- `docs/FORCAD.md` mới; cập nhật `README.md`, `DEPLOYMENT.md`, `GIANG-VIEN.md`, `THI-SINH.md`.

## 4. Thay đổi trong `platform/ForcAD-demo`

| File | Thay đổi |
|---|---|
| `checkers/meko_boutique/` (mới) | `common.py`, 5 script RPC. Bị `.gitignore`, commit bằng `git add -f` |
| `backend/lib/storage/lab_profile.py` (mới) | Task, đội, máy, `round_time`, `ticks_per_round` của từng lab |
| `backend/lib/storage/round_schedule.py` (mới) | Quy tắc thời gian dùng chung, không phụ thuộc database |
| `backend/lib/storage/round1.py` | Đọc theo lab, cột `lab`, `started_at`, `refresh_flag_cache()`, `leave_archived_lab()`, lịch neo cố định |
| `backend/lib/storage/round_control.py` | Đếm task theo lab |
| `backend/services/admin/viewsets/round_control.py` | API chuẩn bị nhận `lab`, API trạng thái trả `ticks_per_round` |
| `backend/services/api/views.py` | `ticks_per_round` lấy theo lab |
| `collect_checker.py` | Đọc `agent_command`, `agent_timeout` từ `lab.json` |
| `shared/labconfig.py` | Đường dẫn SSH config dùng dấu `/`, vì `ssh` của Git làm mất dấu `\` khi có `ProxyJump` |
| `front/public`, `front/dist` | Nút Meko, tên lab, đổi lab sau khi lưu hồ sơ, mặc định tick 300, đồng hồ chạy cả pha `checking` và `ready` |
| `config.yml`, `prepare_local_demo.py` | `round_time` = 300 |

**Ảnh hưởng tới round1:** tick đổi từ 120 thành 300 giây, giai đoạn cuối từ 240 thành 600 giây, số tick từ 15 thành 10.
Chế độ health-only không đổi: vẫn 2 round × 15 tick, trần 30 tick.
Đã sửa `labs/round1/service/README.md` và `test_round1.py` cho khớp.

## 4b. Đổi cách chấm điểm sang công thức RuCTFE 2012 (07/11/2026)

Thay toàn bộ cách tính điểm trong `platform/ForcAD-demo/backend/lib/storage/round1.py` theo công thức RuCTFE 2012.
Trước đó: mỗi flag cướp được +1 cho đội tấn công, −1 cho đội bị mất; tổng = `attack − lost + sla`, không chuẩn hóa.

**Điểm tấn công — `record_attack()`:**
- Đội nộp flag **đầu tiên +2**, mọi đội nộp **cùng flag đó sau đó +1**.
- First-blood được xác định bằng `COUNT(*) FROM StolenFlags WHERE flag_id=…` ngay sau khi INSERT. An toàn tương tranh
  vì hàng `TeamTasks` của nạn nhân đã bị khóa `FOR UPDATE` phía trên, nên mọi đội tấn công cùng một flag bị tuần tự hóa.
- **Bỏ hình phạt −1** khi mất flag (`victim_delta = 0`); cột `lost` vẫn tăng để thống kê nhưng không trừ điểm.

**Điểm phòng thủ + chuẩn hóa — `scores()`:** tính lại hoàn toàn từ dữ liệu thô, không đọc `TeamTasks.score`.
- Attack thô = số flag cướp được + số lần first-blood.
- Defense thô = số flag **bảo vệ được** (`MekodataPlacements` có `flag_id` nhưng không nằm trong `StolenFlags`) **+ điểm SLA**.
- **Chuẩn hóa về 100 chỉ ở bước hiển thị**: `attack_i/attack_max*100`, `defense_i/defense_max*100`,
  `total = attack_norm + defense_norm`. Database vẫn giữ nguyên số đếm thô.

| File | Thay đổi |
|---|---|
| `backend/lib/storage/round1.py` → `record_attack()` | first-blood +2/+1; bỏ phạt −1; `victim_delta=0`; thông điệp nêu first blood |
| `backend/lib/storage/round1.py` → `scores()` | tính attack/defense/first-blood từ `StolenFlags`, `MekodataPlacements`, `MekodataSLA`; chuẩn hóa 100 khi đọc |

**Chưa làm:** văn bản "Luật điểm" trên website vẫn ghi +100/−100 — `platform/MekoDataCTF_Website/public/js/scoreboard-ui.js`
(`RULES = {flag:100, sla:100, down:100}`) và `views/scoreboard.ejs` (card ATTACK). Cần cập nhật riêng cho khớp engine.

**Kiểm chứng:** mới kiểm cú pháp Python và xác nhận `MekodataPlacements.flag_id` được ghi sau mỗi PUT (dòng 241).
Chưa chạy end-to-end vì Docker đang tắt.

## 5. Trạng thái kiểm chứng

| Hạng mục | Trạng thái |
|---|---|
| Test trong `labs/meko_boutique` trừ `test_lab.py` | 97/97 đạt ngày 05/11/2026 |
| Đường script, RPC, collector, agent, app | Đã chạy, thay SSH bằng lệnh local |
| SSH thật tới pool 139 (`ops/pool139/`) | Đạt 05/11/2026: `check` 15/15 UP, 1,3–2,3 giây mỗi lệnh; `put` và `get` qua collector 5/5 UP trên `team1` |
| Logic `pump()` với lịch 50 phút | Đã chạy bằng đồng hồ giả, database và Redis là bản giả |
| `labs/round1/service/run_tests.py` với Postgres, Redis tạm | Đạt 6/7 lần chạy; 1 lần fail 1 test, không còn log nên chưa rõ nguyên nhân, có thể chập chờn. Định dạng flag khai báo theo lab (`flag_template`) |
| Checker ngoài trong Docker → collector → SSH → agent → web đội, pool 139 | 15/15 đạt 05/11/2026: `check`, `put`, `get`, và `get` sai flag trả CORRUPT; trung bình 2,5 giây mỗi lệnh |
| `leave_archived_lab()` và `prepare("meko_boutique")` trên database thật | Đạt 05/11/2026: 5 task, 3 đội, `round_time` 300 |
| Tick thật trên pool 139 | Đạt từ tick 3 ngày 05/11/2026: 15/15 flag, 15/15 task UP, SLA +1 cho 3 đội |
| Nộp flag của đội khác và chấm điểm RuCTFE (first-blood +2/+1, defense + chuẩn hóa 100) | **Chưa chạy** — mới sửa 07/11/2026, chỉ kiểm cú pháp |
| Nút trên trình duyệt | **Chưa chạy** |
| `labs/meko_boutique/tests/test_lab.py` | 6 test fail, còn theo cấu trúc cũ; chưa có test khai thác cho cấu trúc mới |

## 6. Việc tiếp theo

1. Bật Docker, chạy `test_round1.py`, thử đổi lab.
2. Chạy thử một round trên pool 139 và theo dõi pha `checking`.
3. Chạy thử nộp flag nhiều đội để kiểm điểm RuCTFE: first-blood +2, đội sau +1, defense theo flag bảo vệ được, chuẩn hóa 100 trên `/scoreboard`.
4. Cập nhật văn bản "Luật điểm" trên website cho khớp công thức mới.
5. Viết lại `test_lab.py` theo luồng mới.
