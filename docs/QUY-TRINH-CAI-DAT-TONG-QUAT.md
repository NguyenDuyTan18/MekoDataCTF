# Quy trình cài đặt tổng quát hệ thống Attack/Defense CTF (MekoDataCTF + ForcAD + CyberRangeCZ)

Tài liệu tổng quát phục vụ báo cáo. Mô tả **các bước cài đặt từ số không đến vận hành được một cuộc thi**, không phụ thuộc máy cụ thể. Mỗi bước được gắn nhãn nguồn gốc để phân biệt phần **tái sử dụng** và phần **tự tạo lại**.

Chi tiết lệnh theo máy hiện tại xem [HUONG-DAN-KHOI-DONG.md](HUONG-DAN-KHOI-DONG.md); phân tích kiến trúc xem [PHAN-TICH-KIEN-TRUC-VA-TAI-SU-DUNG.md](PHAN-TICH-KIEN-TRUC-VA-TAI-SU-DUNG.md).

## Quy ước nhãn

| Nhãn | Ý nghĩa |
|---|---|
| ♻️ **TÁI SỬ DỤNG** | Thành phần có sẵn (mã nguồn mở hoặc khung dùng chung), dùng lại gần như nguyên vẹn; không phải viết mới. |
| ⚙️ **CẤU HÌNH** | Chỉnh thông số/biến môi trường/địa chỉ; không viết mã. |
| ✍️ **TỰ TẠO LẠI** | Phải xây dựng mới cho mỗi lab/cuộc thi (đóng góp riêng của nhóm). |

---

## 1. Tổng quan kiến trúc

Hệ thống gồm **ba khối chạy độc lập** và một **tầng kết nối**:

```text
Người chơi
   │  (đăng ký, nộp flag, xem điểm)
   ▼
[Khối 1] Website MekoDataCTF  ──HTTP──►  [Khối 2] Engine ForcAD
   (Node.js/Express, SQLite)                (Docker: PostgreSQL/Redis/RabbitMQ)
                                                │  (điều phối tick, sinh/chấm flag)
                                                ▼
                                    Tầng kết nối: collector + SSH
                                                │
                                                ▼
                            [Khối 3] Hạ tầng CyberRangeCZ (sandbox)
                              VM checker  ──HTTP──►  VM đội (dịch vụ có lỗ hổng)
```

Ba cơ sở dữ liệu tách biệt (SQLite website / PostgreSQL ForcAD / SQLite lab) **không dùng chung bảng đội** — nên cần tầng đồng bộ token.

---

## 2. Phân loại nguồn gốc các thành phần (bảng tổng hợp)

| Thành phần | Nguồn gốc | Nhãn |
|---|---|---|
| Engine ForcAD (backend, ticker, scoring, frontend dashboard) | Dự án mã nguồn mở ForcAD | ♻️ TÁI SỬ DỤNG |
| Nền tảng CyberRangeCZ (OpenStack, sandbox orchestration) | Nền tảng mã nguồn mở CyberRangeCZ | ♻️ TÁI SỬ DỤNG |
| Khung checker HTTP (lớp `Client/Service/Verdict`, `run`) | Khung dùng chung trong repo | ♻️ TÁI SỬ DỤNG |
| Tầng transport checker (`agent.py`, `forcad.py`, `common.py`, `collect_checker.py`, `bridge.py`, `labconfig.py`) | Khung dùng chung trong repo | ♻️ TÁI SỬ DỤNG |
| Template sinh cấu hình checker, cấu trúc provisioning (Ansible) | Khung dùng chung trong repo | ♻️ TÁI SỬ DỤNG + ⚙️ |
| Website MekoDataCTF (đăng ký đội, scoreboard, nộp flag, đồng bộ token) | Tự phát triển | ✍️ TỰ TẠO LẠI (1 lần, dùng lại nhiều cuộc thi) |
| Lớp lỗ hổng cụ thể (`Idor/Sqli/Upload/Jwt/Backup`...) | Tự phát triển | ✍️ TỰ TẠO LẠI mỗi lab |
| Ứng dụng web có lỗ hổng (`app.py`) + dữ liệu mẫu (`seed.json`) | Tự phát triển | ✍️ TỰ TẠO LẠI mỗi lab |
| Sandbox Definition của lab (`topology.yml`, `group_vars`, `playbook.yml`) | Tự tạo từ khung mẫu | ✍️ TỰ TẠO LẠI mỗi lab |
| Lịch thi & luật điểm (`lab_profile.py`, `round_schedule.py`) | Tự phát triển | ✍️ TỰ TẠO LẠI / ⚙️ |
| Toàn bộ địa chỉ IP, tài khoản, khóa SSH, token | — | ⚙️ CẤU HÌNH |

---

## 3. Điều kiện tiên quyết

| Yêu cầu | Ghi chú | Nhãn |
|---|---|---|
| Docker Engine + Docker Compose | Chạy toàn bộ backend ForcAD | ♻️ |
| Node.js LTS + npm | Chạy website; có dependency native `better-sqlite3` cần công cụ build | ♻️ |
| Python 3.11 + OpenSSH client | Chạy collector/CLI ForcAD và kết nối sandbox | ♻️ |
| Tài khoản & quota trên nền tảng CyberRangeCZ | Để tạo sandbox (VM đội + VM checker) | ♻️ + ⚙️ |

---

## 4. Quy trình cài đặt tổng quát

Thứ tự khuyến nghị: **ForcAD → Hạ tầng CyberRangeCZ/lab → Website → Kết nối → Bắt đầu**. (Website có thể cài song song; nó tự nối lại khi ForcAD lên.)

### Giai đoạn A — Chuẩn bị môi trường

**A1.** Cài Docker, Node.js, Python 3.11, OpenSSH. — ♻️ TÁI SỬ DỤNG
**A2.** Lấy mã nguồn dự án về máy triển khai. — ♻️
**A3.** Chuẩn bị khóa/SSH config do CyberRangeCZ cấp, hoàn tất xác minh host key (collector chạy SSH không tương tác, không được hỏi mật khẩu). — ⚙️ CẤU HÌNH

### Giai đoạn B — Khối 2: Engine ForcAD (nền tảng chấm điểm)

**B1.** Tạo `config.yml` từ `config.yml.example`: khai `admin`, `teams` (tên/IP), `tasks` (checker tương ứng mỗi lỗ hổng), `game` (giờ bắt đầu, múi giờ, thời lượng). — ⚙️ CẤU HÌNH
**B2.** Cài phụ thuộc CLI (`pip install -r cli/requirements.txt`) và chạy `control.py setup` để sinh file môi trường trong `docker_config/`. — ♻️ TÁI SỬ DỤNG
**B3.** `docker compose up -d --build`: bật PostgreSQL, Redis, RabbitMQ, initializer, ticker, Celery worker, Flower, API client/admin, HTTP receiver, nginx. — ♻️ TÁI SỬ DỤNG
**B4.** Nạp schema điều khiển lab (vd `setup_round1.py` / tương đương): tạo bảng, **không** bắt đầu thi, **không** sinh flag. — ♻️ (khung) + ✍️ (script schema riêng của lab)
**B5.** Dashboard dựng sẵn ở `front/dist/` được nginx phục vụ; chỉ build lại `front/` khi sửa giao diện. — ♻️ TÁI SỬ DỤNG

> **Đóng góp của nhóm ở khối này:** luật tính điểm, lịch tick/flag và script chuẩn bị round (`lab_profile.py`, `round_schedule.py`, `setup_*.py`) — ✍️ TỰ TẠO LẠI.

### Giai đoạn C — Khối 3: Hạ tầng CyberRangeCZ & lab lỗ hổng

**C1.** Thiết kế **Sandbox Definition**: topology (mạng, VM đội, VM checker), provisioning (Ansible: cài web lab + agent checker). — ✍️ TỰ TẠO LẠI mỗi lab *(dựa trên khung mẫu `labs/_template`)*
**C2.** Viết **ứng dụng web có lỗ hổng** và dữ liệu mẫu cho lab (`app.py`, `seed.json`). — ✍️ TỰ TẠO LẠI
**C3.** Viết **lớp checker cho từng lỗ hổng** (`check/put/get`) kế thừa khung `Service` dùng chung. — ✍️ TỰ TẠO LẠI *(khung `Client/Verdict/run` là ♻️)*
**C4.** Dựng sandbox trên CyberRangeCZ từ Sandbox Definition; nền tảng tự cấp phát VM và mạng. — ♻️ TÁI SỬ DỤNG + ⚙️
**C5.** Triển khai web lab + agent lên VM (vd `deploy.py --apply`): ghi mã nguồn, cài service systemd, đặt cờ vá mẫu về `false`; giữ file token quản trị lab sinh ra (`.secrets/teams.json`). — ♻️ (công cụ) + ⚙️
**C6.** Kiểm tra SSH tới VM checker và từng VM đội (mỗi lệnh phải in hostname, không hỏi mật khẩu). — ⚙️ CẤU HÌNH

> **Đóng góp của nhóm ở khối này:** Sandbox Definition + app lỗ hổng + lớp checker. Phần vòng đời sandbox (cấp phát/thu hồi) là tính năng ♻️ của CyberRangeCZ, chỉ cần gọi đúng.

### Giai đoạn D — Khối 1: Website MekoDataCTF

**D1.** `npm install` trong thư mục website. — ♻️ (chạy công cụ) trên mã ✍️ tự phát triển
**D2.** Tạo `.env`: `SESSION_SECRET`, tài khoản BTC (`ADMIN_EMAIL/PASSWORD`), `PORT`, `FORCAD_URL`, tùy chọn thông tin admin ForcAD và chu kỳ đồng bộ. — ⚙️ CẤU HÌNH
**D3.** `npm run seed`: tạo tài khoản BTC và nạp nội dung mặc định. — ♻️ (công cụ) trên mã ✍️
**D4.** `npm start`: chạy `app.js`, mở cổng website; mở firewall nếu cần cho LAN. — ⚙️

### Giai đoạn E — Tầng kết nối & vận hành

**E1.** Chạy **collector** (`collect_checker.py`) với biến `MEKO_LAB=<tên lab>`: poll yêu cầu tick của ForcAD → SSH vào VM checker → chạy agent. — ♻️ TÁI SỬ DỤNG
**E2.** **Đồng bộ token đội** website → ForcAD (tự chạy khi website khởi động, định kỳ, và khi đội thay đổi; CLI `npm run sync:forcad` để kiểm tra ghép đội). — ♻️ (website tự phát triển, dùng lại được)
**E3.** **Chuẩn bị & bắt đầu round** trên dashboard ForcAD: chọn lab → *Chuẩn bị* (tạo đội/task) → *Bắt đầu* (đồng hồ chạy, flag bắt đầu sinh). — ♻️ + ⚙️
**E4.** Đội đăng nhập `/scoreboard`, nộp flag bằng token đội. — vận hành.

---

## 5. Khi tạo một lab/cuộc thi MỚI thì phải tạo lại những gì?

Đây là phần trả lời trực tiếp cho câu hỏi "phần nào tái sử dụng / phần nào tự tạo lại":

**Giữ nguyên (♻️) — không viết lại:**
- Engine ForcAD + dashboard, nền tảng CyberRangeCZ.
- Toàn bộ tầng transport checker: `agent.py`, `forcad.py`, `common.py`, `collect_checker.py`, `bridge.py`, `labconfig.py`.
- Khung checker HTTP (`Client`, `Service` cơ sở, `Verdict`, `run`, helper).
- Website (chỉ cấu hình lại tên đội/lab).
- Cấu trúc provisioning Ansible + template sinh config.

**Tạo lại (✍️) cho mỗi lab:**
- Ứng dụng web có lỗ hổng + dữ liệu mẫu.
- Lớp checker cho từng lỗ hổng (`check/put/get`).
- Sandbox Definition (topology + provisioning) của lab.
- Lịch thi & luật điểm (số tick, số flag/đội/tick, thời lượng) và script chuẩn bị round.

**Chỉ cấu hình lại (⚙️):**
- IP đội, tài khoản BTC, khóa/SSH config, token, cổng dịch vụ, ánh xạ tên đội website ↔ ForcAD.

---

## 6. Sơ đồ quy trình rút gọn (đưa vào báo cáo)

```text
A. Môi trường ──► B. ForcAD (Docker + config + schema)
                        │
C. CyberRangeCZ: Sandbox Definition ✍️ ──► dựng sandbox ♻️ ──► deploy lab+agent
                        │
D. Website (npm + .env + seed) ──► E. Collector + đồng bộ token ──► Bắt đầu round
```

Tỷ lệ tổng quát: **nền tảng & transport ≈ tái sử dụng; nội dung lab & luật thi ≈ tự tạo lại.** Chính ranh giới này là cơ sở để chia ba phân hệ luận văn.
