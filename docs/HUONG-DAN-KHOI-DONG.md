# Hướng dẫn khởi động mã nguồn MekoDataCTF

Tài liệu dành cho Windows/PowerShell, theo cấu trúc mã nguồn hiện tại. Đường dẫn ví dụ là `C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform`; nếu chuyển máy, thay bằng nơi lưu dự án.

## 1. Chạy lên những gì?

| Thành phần | Chạy ở đâu / bằng gì | Kết quả |
|---|---|---|
| Website MekoDataCTF | Windows, `npm start` chạy `app.js` | `http://localhost:3000`: giới thiệu, đăng ký/đăng nhập, quản lý đội; `/admin` cho BTC; `/scoreboard` xem bảng điểm, sân đấu và nộp flag. Dữ liệu SQLite ở `platform/MekoDataCTF_Website/data/mekodata.db`. |
| ForcAD | Docker Desktop, `docker compose up -d` | `http://127.0.0.1:18080/`: dashboard và điều khiển round; `/admin/`: quản trị ForcAD; `/flower/`: theo dõi worker; `/submit.html`: trang nộp flag riêng. |
| Collector | Windows, `python platform/ForcAD-demo/collect_checker.py` | Tiến trình nền trong terminal, chuyển yêu cầu kiểm tra của ForcAD qua SSH tới VM checker; không mở trang web riêng. |
| Lab Round 1 | Các VM CyberRange | Bốn web lab tại `http://10.80.0.11` đến `http://10.80.0.14`, cổng 80; máy checker kiểm tra dịch vụ và đặt/đọc flag qua agent. Chỉ truy cập được khi có đường mạng tới lab. |

Luồng hoạt động:

```text
Người chơi → Website :3000 → ForcAD :18080
                                 ↓
                       checker trong Docker
                                 ↓ file JSON dùng chung
                       collector trên Windows
                                 ↓ SSH
                       agent trên VM checker
                                 ↓ HTTP
                       web lab trên 4 VM đội
```

**Để chạy đầy đủ cần Docker + website + collector + sandbox VM.** Nếu chỉ xem/sửa website đăng ký, có thể chạy riêng website; bảng điểm trực tiếp và nộp flag cần ForcAD.

## 2. Những file cần sửa trước khi chạy

Không cần sửa mã nguồn mỗi lần bật hệ thống. Chỉ chỉnh các file sau khi cài lần đầu, chuyển máy hoặc thay sandbox/cấu hình.

| File | Cần sửa gì? | Khi nào cần? |
|---|---|---|
| `platform/MekoDataCTF_Website/.env` | `SESSION_SECRET` là chuỗi ngẫu nhiên dài; `ADMIN_EMAIL`, `ADMIN_PASSWORD` cho BTC; `PORT=3000`; `NODE_ENV=development` khi chạy HTTP local. | Lần đầu hoặc đổi tài khoản/cổng. Mật khẩu seed cần ít nhất 8 ký tự. |
| Cũng trong `.env` | `FORCAD_URL=http://127.0.0.1:18080`; tùy chọn `FORCAD_ADMIN_USER`, `FORCAD_ADMIN_PASSWORD`, `FORCAD_CONFIG`, `FORCAD_SYNC_INTERVAL`. | Để website lấy điểm và tự đồng bộ token. Để trống thông tin admin thì website đọc từ `../ForcAD-demo/config.yml`. |
| `platform/ForcAD-demo/config.yml` | Các mục `admin`, `teams` (tên/IP), `tasks` (checker), `game` (giờ bắt đầu, múi giờ, thời lượng theo cấu hình ForcAD). | Cài ForcAD mới. Với bản Round 1 tùy chỉnh, chuẩn bị/bắt đầu qua dashboard; không coi sửa lịch trong YAML là thao tác bắt đầu round. |
| `labs/round1/lab.json` | `ssh_config`, `checker_host`, `teams[].name/host/ip`, `tasks`. | Đổi địa chỉ hoặc alias SSH của lab. Hiện tại: `team01`–`team04` tương ứng `attacker1`–`attacker4`, IP `10.80.0.11`–`10.80.0.14`. |
| `ops/pool101/management-config` | Địa chỉ/port quản trị và các mục SSH như `HostName`, `ProxyJump`/`ProxyCommand` nếu có; đặc biệt đường dẫn `IdentityFile`, `UserKnownHostsFile`. | Chuyển máy hoặc cấp sandbox mới. Dùng config/key do CyberRange cấp và trỏ về vị trí thật trên máy. |
| `platform/ForcAD-demo/docker-compose.yml` | Mapping cổng nginx đang là `127.0.0.1:18080:80`. | Chỉ khi cần đổi cổng hoặc địa chỉ lắng nghe; đổi cổng thì cập nhật cả `FORCAD_URL`. Cấu hình hiện tại chỉ mở ForcAD trên máy local. |
| `labs/round1/sandbox/topology.yml`, `provisioning/group_vars/all.yml`, `checker/web_targets.json` | Topology, biến provisioning và danh sách máy cần kiểm tra. | Chỉ khi tạo/thay đổi Sandbox Definition trên CyberRange. Docker Compose không tạo các VM này. |

**Lưu ý về đội/IP:** backend Round 1 vẫn có giá trị cố định trong `platform/ForcAD-demo/backend/lib/storage/round1.py` và `round_control.py`. Thay số đội/IP hoặc tạo lab khác không chỉ sửa `lab.json`; cần đối chiếu backend, checker và topology. Sửa `config.yml` cũng không tự cập nhật đội/task đã lưu trong database đang tồn tại.

Tài khoản website trong `.env` và tài khoản ForcAD trong `config.yml` là hai tài khoản riêng. Token đội dùng để đăng nhập/nộp flag khác với token quản trị web lab.

## 3. Chuẩn bị lần đầu

### 3.1. Công cụ và sandbox

- Cài Node.js/npm, Python 3 và OpenSSH client; mở Docker Desktop và đợi Engine hoạt động. Backend Docker dùng Python 3.11; nên dùng Python 3.11 cho CLI cài đặt local.
- `package.json` website khai báo Node >=18, nhưng có dependency native `better-sqlite3`; nên dùng Node LTS còn được hỗ trợ và tương thích dependency. Nếu `npm install` phải biên dịch native, máy cần công cụ build tương ứng.
- Có sẵn sandbox CyberRange gồm bốn VM đội và VM checker. Nội dung thư mục `labs/round1/sandbox/` là nguồn Sandbox Definition; không chạy file topology bằng Python.
- Sửa các file cấu hình ở mục 2. Giữ nguyên `.env` đã có; không chép đè bằng file mẫu.

Trên máy hiện tại có Python Launcher `py`, mặc định Python 3.14, nhưng lệnh `python` chưa nằm trong PATH. Có thể chạy collector bằng `py platform/ForcAD-demo/collect_checker.py`. Riêng CLI ForcAD có dependency khóa phiên bản cũ: nên cài thêm Python 3.11 rồi dùng `py -3.11 -m pip install -r cli/requirements.txt` và `py -3.11 control.py setup`. Các lệnh Python local khác bên dưới cũng có thể dùng `py -3.11` thay `python` sau khi cài. Giữ nguyên `python` trong lệnh `docker compose exec ...` vì đó là Python bên trong container.

Kiểm tra SSH từ thư mục gốc:

```powershell
ssh -F .\ops\pool101\management-config checker "hostname"
ssh -F .\ops\pool101\management-config attacker1 "hostname"
```

Kiểm tra tương tự với `attacker2`–`attacker4`. Collector dùng SSH không tương tác, nên kết nối bằng key phải hoạt động mà không hỏi mật khẩu; hoàn tất xác minh host key của sandbox trước khi chạy collector.

### 3.2. Chuẩn bị ForcAD

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo
python -m pip install -r cli/requirements.txt
```

Nếu bản mới chưa có `config.yml`, tạo từ `config.yml.example` rồi sửa theo mục 2. File mẫu chứa đội/task ví dụ, **chưa phải cấu hình Round 1 sẵn dùng**. Bản hiện tại đã có `config.yml` thì giữ cấu hình đang dùng.

**Chỉ khi chưa thiết lập cấu hình**, chạy:

```powershell
python control.py setup
```

Lệnh này tạo/cập nhật các file môi trường trong `docker_config/`, mục `storages` trong `config.yml` và `docker-compose-base.yml`. Không cần chạy lại mỗi lần bật máy; không tùy tiện đổi mật khẩu storage khi đã có PostgreSQL cũ.

Khởi động các container bằng cấu hình local của repo:

```powershell
docker compose up -d --build
docker compose ps -a
```

ForcAD chạy PostgreSQL, Redis, RabbitMQ, initializer, ticker, Celery worker, Flower, API client/admin, events, HTTP receiver và nginx. Chờ khởi tạo database xong, rồi cài schema điều khiển Round 1:

```powershell
docker compose exec ticker python /app/scripts/setup_round1.py
```

Lệnh schema không bắt đầu thi hoặc sinh flag. Nếu thiếu bảng khi vừa chạy lần đầu, xem log initializer và chờ khởi tạo hoàn tất rồi thử lại.

`front/dist/` đã có giao diện dựng sẵn và được nginx phục vụ. Chỉ khi sửa giao diện hoặc thiếu bản build mới cần vào `front/`, chạy `npm install`, `npm run build`, rồi trở lại thư mục ForcAD. Không cần chạy `npm run dev` của frontend ForcAD để sử dụng hệ thống.

### 3.3. Cài web lab lên VM mới

Sau khi sandbox và SSH đã sẵn sàng, từ thư mục gốc:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform
python labs/round1/service/deploy.py --apply
```

Lệnh này ghi source/cấu hình lên VM, cài web lab và agent checker, restart service và đặt các cờ vá mẫu về `false`; không sinh flag. **Chỉ dùng khi triển khai lab**, không chạy lại hằng ngày trên cuộc thi đang có bản vá của đội. Không có `--apply` thì script chỉ in hướng dẫn.

Giữ file `labs/round1/service/.secrets/teams.json` được tạo sau triển khai; đây là token quản trị lab dùng cho checker. Trên VM, web lab chạy qua systemd `attacker-http@attackerN`; `agent.py` trên checker được collector gọi qua SSH, không cần tự mở terminal chạy agent liên tục.

### 3.4. Cài website

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website
npm install
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Sửa `.env` trước khi chạy hai lệnh sau:

```powershell
npm run seed
npm start
```

`seed` tạo/cập nhật tài khoản BTC và nạp nội dung mặc định khi cần. Chạy lại sẽ cập nhật mật khẩu theo `.env`; không cần seed mỗi lần bật website. `npm start` chạy `app.js` và giữ terminal hoạt động; khi phát triển có thể dùng `npm run dev` thay thế.

## 4. Khởi động hằng ngày, từ frontend đến backend

Áp dụng sau khi đã cài xong mục 3. Lệnh dưới đây dành cho lab **Meko Boutique**; với Round 1, xem cuối mục này.

| Bước | Lớp | Chạy ở đâu | Địa chỉ |
|---|---|---|---|
| 1 | Website và scoreboard cho đội | Terminal 1 | `http://localhost:3000` |
| 2 | Dashboard ForcAD cho BTC | Nginx trong Docker | `http://127.0.0.1:18080` |
| 3 | Backend ForcAD | Docker | Không mở trang riêng |
| 4 | Collector | Terminal 3 | Không mở trang riêng |
| 5 | Lab trên VM | CyberRange | `10.90.0.11`–`10.90.0.13` |

Website có thể bật trước ForcAD: trang báo mất kết nối, rồi tự nối lại và đồng bộ token khi ForcAD lên.

**Cách nhanh:** sau khi bật Docker Desktop, chạy `.\KHOI-DONG-LAI-MEKO.bat` ở thư mục gốc. File này làm bước 2–4 rồi mở trang điều khiển. Sau đó vẫn cần làm bước 1, 5, 6 và 7.

### Bước 1. Website (frontend cho các đội)

Mở **Terminal 1** và giữ chạy suốt buổi thi:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website
npm start
```

Đúng khi terminal in `MekoDataCTF đang chạy tại http://localhost:3000`. Dòng `Không đồng bộ được: fetch failed` chỉ có nghĩa là ForcAD chưa lên.

Các đội trong LAN truy cập bằng IP máy này. Lấy IP:

```powershell
Get-NetIPConfiguration | Where-Object IPv4DefaultGateway | ForEach-Object { $_.IPv4Address.IPAddress }
```

Rồi mở `http://<IP>:3000/scoreboard`. Nếu máy khác không vào được, chạy một lần trong PowerShell **Run as administrator**:

```powershell
New-NetFirewallRule -DisplayName "MekoDataCTF Website 3000" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow -Profile Private
```

### Bước 2. Dashboard ForcAD (frontend cho BTC)

Không cần chạy riêng: nginx phục vụ bản dựng sẵn trong `front/dist/` ở bước 3. Chỉ khi sửa mã trong `front/src/` mới dựng lại:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo\front
npm install
npm run build
```

### Bước 3. Backend ForcAD

Mở Docker Desktop, đợi Engine chạy, rồi mở **Terminal 2**:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo
docker version
docker compose up -d --build
docker compose ps -a
docker compose exec -T postgres pg_isready -U forcad
docker compose exec -T ticker python /app/scripts/setup_round1.py
```

- `docker compose up` bật PostgreSQL, Redis, RabbitMQ, initializer, ticker, Celery, Flower, API, events, HTTP receiver và nginx.
- Đợi `pg_isready` báo `accepting connections` rồi mới chạy lệnh cuối.
- `setup_round1.py` cập nhật schema, không bắt đầu thi và không sinh flag.

Kiểm tra API:

```powershell
curl.exe -s http://127.0.0.1:18080/api/client/teams/
```

### Bước 4. Collector

Mở **Terminal 3** và giữ chạy suốt buổi thi. Chỉ chạy một collector:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform
$env:MEKO_LAB = 'meko_boutique'
py platform/ForcAD-demo/collect_checker.py
```

### Bước 5. Lab trên VM

Bật sandbox trên CyberRange và kết nối mạng tới pool. Từ thư mục gốc:

```powershell
ssh -F .\ops\pool139\management-config checker "hostname"
ssh -F .\ops\pool139\management-config team1 "hostname"
ssh -F .\ops\pool139\management-config team2 "hostname"
ssh -F .\ops\pool139\management-config team3 "hostname"
```

Mỗi lệnh phải in tên máy mà không hỏi mật khẩu. Nếu `Connection timed out`, máy này chưa tới được pool, collector sẽ không chấm được service.

### Bước 6. Đồng bộ token đội

Token tự đồng bộ khi website khởi động, mỗi 60 giây và khi đội thay đổi. Để xem đội nào ghép được, mở terminal thứ tư:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website
npm run sync:forcad
```

Đội ForcAD của lab là `team1`–`team3`. Đội website có tên khác phải được khai **Tên đội trên ForcAD** trong `/admin`.

### Bước 7. Chuẩn bị và bắt đầu round

1. Mở `http://127.0.0.1:18080/` và đăng nhập quản trị.
2. Nếu đang ở lab khác: bấm **Dừng**, rồi **Đóng và lưu hồ sơ**.
3. Bấm **Chuẩn bị Meko Boutique (5 task)**. Bước này tự tạo `team1`–`team3` nếu chưa có.
4. Bấm **Bắt đầu**. Đồng hồ 50 phút chạy và flag mới được sinh từ lúc này.
5. Mở `http://localhost:3000/scoreboard`. Đội đăng nhập bằng tài khoản đội trưởng hoặc token đội để nộp flag.

**Bật container và mở trang web không có nghĩa là đã bắt đầu một lượt thi mới.** Nếu database đang lưu round chạy dở, kiểm tra trạng thái trên dashboard trước khi bấm **Bắt đầu**.

### Chạy Round 1 thay vì Meko Boutique

Đặt `$env:MEKO_LAB = 'round1'` ở bước 4, kiểm tra SSH bằng `.\ops\pool101\management-config` ở bước 5 và bấm **Chuẩn bị Round 1 (3 task)** ở bước 7. Tên đội trên ForcAD là `team01`–`team04`.

## 5. Kiểm tra và dừng

| Hiện tượng | Kiểm tra |
|---|---|
| Không mở được cổng 18080 | Docker Desktop đã chạy chưa; trong thư mục ForcAD dùng `docker compose ps -a`, `docker compose logs --tail 50 nginx client-api admin-api ticker initializer`. |
| Website không chạy/cổng 3000 bận | Xem lỗi trong terminal Node; kiểm tra `.env`, dependency và `PORT`; sửa `.env` thì khởi động lại website. |
| Website mở được nhưng không có điểm | ForcAD có truy cập được không; `FORCAD_URL` có đúng không; round đã được chuẩn bị/bắt đầu chưa. |
| Checker báo DOWN / Sandbox agent unavailable | Collector có đang chạy không; alias/key SSH có đúng sandbox không; VM và các service lab có hoạt động không. |
| Nộp flag báo token sai/không khớp đội | Kiểm tra tên đội ForcAD trong website và trạng thái đồng bộ token; chạy `npm run sync:forcad` để xem kế hoạch ghép đội. |

Dừng theo thứ tự: bấm **Dừng** trên dashboard ForcAD và đợi xử lý hoàn tất; nhấn `Ctrl+C` ở terminal website và collector; trong thư mục ForcAD chạy `docker compose stop`. Dữ liệu được giữ để chạy tiếp.

Không dùng `control.py reset`, xóa `docker_volumes/postgres/data` hoặc chạy `recycle.py` như bước khởi động thông thường: các thao tác này liên quan xóa/reset dữ liệu. Muốn tổ chức lượt thi mới và dọn VM, làm theo quy trình đóng/lưu hồ sơ và tái tạo trong [README Round 1](../labs/round1/service/README.md).

## 6. Tài liệu chi tiết

- [Bảng chỉnh thông số](../adjust_settings.md)
- [Cấu trúc workspace và cách chạy từng file](TAI-CAU-TRUC-WORKSPACE.md)
- [Đồng bộ token website → ForcAD](DONG-BO-TOKEN-FORCAD.md)
- [Website: cài đặt và tính năng](../platform/MekoDataCTF_Website/README.md)
- [Lab Round 1: triển khai, điều khiển và tái tạo](../labs/round1/service/README.md)
- [Lab Meko Boutique với ForcAD](../labs/meko_boutique/docs/FORCAD.md)
- [Giao diện dashboard của `/scoreboard`](SCOREBOARD-GIAO-DIEN-DASHBOARD.md)

Mục 4 được đối chiếu với mã nguồn và script trong repo ngày 05/11/2026. Lúc viết, Docker Desktop đang tắt và SSH tới pool 139 bị timeout, nên mới chạy thật `npm start` và kiểm tra các trang website; các lệnh Docker, collector và SSH chưa chạy lại trong đợt này.
