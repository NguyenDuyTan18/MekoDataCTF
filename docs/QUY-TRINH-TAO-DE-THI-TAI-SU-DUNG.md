**Hướng dẫn cho người mới: hiểu, cài đặt, khởi động và tạo bài thi MekoDataCTF**

Đối chiếu mã nguồn ngày 07/11/2026. Hướng dẫn dành cho Windows/PowerShell, theo workspace hiện tại. Các lệnh bên dưới là hướng dẫn thao tác; chưa được chạy để cài/triển khai môi trường trong lần soạn tài liệu này.

**Đọc nhanh: chọn đúng việc cần làm**

| Tình huống của bạn | Đọc và thực hiện |
|---|---|
| Chưa hiểu hệ thống | Đọc phần A để biết thành phần nào chạy ở đâu. |
| Máy mới chưa cài dự án | Làm phần B một lần; sau đó dùng phần C nếu đã được bàn giao sandbox có sẵn, hoặc phần D để tạo bài. |
| Dự án đã cài, muốn bật lại bài đang có | Làm phần C. Không cần tạo lab, cài lại dependency hay tạo pool. |
| Muốn thêm bài thi hoặc đổi danh sách đội | Sau khi có nền tảng phần B, làm phần D từ website chốt đội đến chạy thử và mở thi. |
| Chỉ muốn xem/sửa website | Cài website ở B2, chạy website ở C3; chưa cần sandbox và collector. |
| Có lỗi khi chạy | Xem phần E để xác định khối đang lỗi. |

**A — Hiểu dự án trước khi chạy lệnh**

Đây là hệ thống tổ chức thi Attack/Defense: mỗi đội có dịch vụ cần bảo vệ, tìm flag từ dịch vụ đội khác và nộp flag để tính điểm. “Tạo bài thi” gồm chuẩn bị gói nội dung, môi trường chạy và cấu hình chấm cho một bài. “Khởi động” là bật lại các thành phần đã được cài và cấu hình.

| Thành phần | Chạy ở đâu? | Làm gì? | Người vận hành mở gì? |
|---|---|---|---|
| Website MekoDataCTF | Máy vận hành, Node.js | Đăng ký đội, quản trị, giao diện nộp flag và bảng điểm | `http://localhost:3000`, `/admin`, `/scoreboard` |
| ForcAD | Docker trên máy vận hành | Điều khiển cuộc thi, gọi checker, quản lý flag và tính điểm | `http://127.0.0.1:18080/`, đăng nhập quản trị tại `/admin/` |
| Collector | Terminal Python trên máy vận hành | Chuyển yêu cầu của ForcAD qua SSH tới VM checker | Giữ terminal chạy; không có trang web riêng |
| CyberRangeCZ | Hệ thống cyber range đã được cung cấp | Tạo VM, mạng và chạy cài đặt môi trường theo định nghĩa | Portal CyberRangeCZ do quản trị cung cấp |
| Ứng dụng bài thi và checker | VM trong sandbox CyberRangeCZ | Dịch vụ của đội và chương trình kiểm tra/đặt/đọc flag | SSH hoặc giao diện truy cập được cấp |

```text
Máy vận hành Windows                     Môi trường CyberRangeCZ
Website :3000 → ForcAD :18080
                    ↓
            wrapper checker trong Docker
                    ↓ file JSON
            collector Python ─── SSH ───→ VM checker ─── HTTP ───→ VM các đội
                    ↑                            kết quả kiểm tra
            ForcAD tính điểm → Website hiển thị
```

Dòng file JSON là thư mục dùng chung giữa container và máy vận hành. Container ForcAD không giữ bộ SSH key thay cho collector.

| Thuật ngữ | Hiểu đơn giản |
|---|---|
| Lab / mã đề | Một gói bài, ví dụ `meko_boutique` hoặc đề mới `round2`. |
| Sandbox Definition | Các file mô tả máy/mạng và cách cài app/checker; chưa phải VM đang chạy. |
| Sandbox | Môi trường VM/mạng được tạo thật từ định nghĩa. |
| Pool | Nhóm sandbox cùng định nghĩa/phiên bản; số sandbox khác số VM đội. |
| Provisioning | Tự động cài package, source, cấu hình và dịch vụ lên VM, ở đây bằng Ansible. |
| Task | Một mục được chấm điểm của đề, ví dụ `idor`, `sqli`. |
| Checker / agent | Logic kiểm tra dịch vụ; agent nhận yêu cầu từ collector để gọi logic đó. |
| Tick | Một chu kỳ vận hành/chấm của cuộc thi. |
| Profile ForcAD | Cấu hình giúp engine biết dùng lab, đội, task và lịch nào. |

Trên máy mới, cần được bàn giao mã nguồn và đường dẫn lưu, địa chỉ Portal/tài khoản CyberRangeCZ, cùng thông tin truy cập nếu dùng sandbox có sẵn. Tài liệu giả định CyberRangeCZ/cloud đã hoạt động; dựng một cụm CyberRangeCZ/OpenStack mới là công việc hạ tầng riêng.

Các ví dụ dùng workspace `C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform`. Nếu mã nguồn nằm nơi khác, thay phần đường dẫn gốc trong các lệnh. `Set-Location` đổi thư mục đang làm việc; chạy lệnh ở đúng thư mục được ghi. `npm start` và collector giữ terminal bận; muốn chạy việc khác phải mở terminal mới. Dùng `Ctrl+C` để dừng tiến trình trong terminal.

**Cách đọc nhãn tái sử dụng**

| Nhãn | Ý nghĩa khi đổi sang một đề thi khác |
|---|---|
| **[DÙNG LẠI]** | Dùng lại mã nguồn hoặc cơ chế hiện có; không sửa logic theo nội dung đề nếu giữ giao thức tương thích. |
| **[DÙNG KHUNG, SỬA CẤU HÌNH]** | Dùng lại cấu trúc/file mẫu, nhưng phải khai báo lại dữ liệu và kiểm tra các giả định. Không phải chép nguyên trạng. |
| **[KHÔNG TÁI SỬ DỤNG]** | Nội dung hoặc tài nguyên riêng của đề/lượt thi: cần cung cấp mới, tạo mới hoặc đánh giá lại cho đề mới. |

“Không tái sử dụng” ở đây xét giữa các đề có nội dung hoặc đợt triển khai khác nhau. Nếu tổ chức lại đúng một đề, có thể dùng lại phiên bản source đã nghiệm thu, nhưng phải đưa dữ liệu thi về trạng thái ban đầu bằng quy trình phù hợp.

**Cấu trúc thư mục để nhận diện phần chung và phần riêng**

Gốc workspace: `C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform`.

```text
atk_def_platform/
├── platform/
│   ├── MekoDataCTF_Website/                [DÙNG LẠI] ứng dụng website
│   │   ├── app.js, models/, services/      [DÙNG LẠI] quản lý đội, hiển thị, đồng bộ
│   │   ├── scripts/export-lab-teams.js     [DÙNG LẠI] xuất đội → lab.json
│   │   ├── scripts/sync-forcad-tokens.js   [DÙNG LẠI] đồng bộ token
│   │   ├── .env                           [DÙNG KHUNG, SỬA CẤU HÌNH] cài ban đầu/đổi máy
│   │   └── data/mekodata.db                [KHÔNG TÁI SỬ DỤNG] hồ sơ mặc định cho giải mới
│   └── ForcAD-demo/
│       ├── docker-compose.yml             [DÙNG LẠI] cơ chế chạy nền tảng
│       ├── config.yml                     [DÙNG KHUNG, SỬA CẤU HÌNH] thiết lập nền tảng
│       ├── backend/lib/storage/
│       │   ├── competition.py                  [DÙNG LẠI] vòng đời đã đọc lab_profile
│       │   ├── round_schedule.py          [DÙNG LẠI] điều phối lịch
│       │   └── lab_profile.py             [DÙNG KHUNG, SỬA CẤU HÌNH] thêm profile đề
│       ├── front/public/round-control.js  [DÙNG KHUNG, SỬA CẤU HÌNH/MÃ] thêm lựa chọn đề
│       ├── collect_checker.py             [DÙNG LẠI] cầu nối JSON/SSH
│       └── checkers/<ma-de>/
│           ├── common.py                  [DÙNG LẠI] giao vận, nếu giữ giao thức hiện tại
│           ├── <task>.py                  [DÙNG KHUNG, SỬA CẤU HÌNH] chọn tên task
│           └── rpc/                       [KHÔNG TÁI SỬ DỤNG] dữ liệu yêu cầu/phản hồi cũ
├── shared/
│   ├── labconfig.py                       [DÙNG LẠI] đọc cấu hình và dựng lệnh SSH
│   └── service-checker/                   [KHÔNG TÁI SỬ DỤNG NGUYÊN TRẠNG] checker ServiceDesk
├── labs/
│   ├── _template/lab.json                 [DÙNG LẠI] mẫu cấu hình
│   └── <ma-de>/
│       ├── lab.json                       [DÙNG KHUNG, SỬA CẤU HÌNH] thông tin đề/đội/máy
│       ├── sandbox/
│       │   ├── topology.yml               [DÙNG KHUNG, SỬA CẤU HÌNH] VM, IP, mạng, image
│       │   ├── provisioning/
│       │   │   ├── playbook.yml           [DÙNG KHUNG, PHẢI CHỈNH] cài app/checker của đề
│       │   │   ├── trainee-access.yml     [DÙNG KHUNG, PHẢI CHỈNH] tài khoản, tên đội
│       │   │   ├── group_vars/all.yml     [DÙNG KHUNG, SỬA CẤU HÌNH] đội/IP/tham số mới
│       │   │   └── templates/             [DÙNG KHUNG, PHẢI CHỈNH] cấu hình app/checker
│       │   ├── app/                       [KHÔNG TÁI SỬ DỤNG] nội dung ứng dụng đề khác
│       │   └── checker/                   [KHÔNG TÁI SỬ DỤNG] logic kiểm tra đề khác
│       ├── docs/                          [KHÔNG TÁI SỬ DỤNG] nội dung đề và hướng dẫn riêng
│       └── tests/                         [KHÔNG TÁI SỬ DỤNG] kỳ vọng nghiệp vụ của đề khác
└── ops/<pool-id>/                         [KHÔNG TÁI SỬ DỤNG] bộ truy cập pool cũ cho pool mới
    └── management-config, key, known-hosts
```

Cây trên kết hợp phần chung đang tồn tại với cấu trúc mẫu cho một đề mới. Không phải mọi lab hiện có đều giống hệt: Round 1 còn có `service/`; Meko Boutique đặt ứng dụng và checker trong `sandbox/`. Không cần tạo `service/` cho đề dùng toàn bộ cơ chế provisioning như Meko Boutique.

Các nhãn dữ liệu không yêu cầu xóa database hoặc SSH key cũ. Phải giữ hồ sơ cũ, tạo môi trường/hồ sơ phù hợp cho lượt mới; không lấy dữ liệu cũ làm cấu hình mặc định của đề mới.

**B — Cài nền tảng lần đầu trên máy mới**

Làm phần này trước khi đăng ký đội hoặc chuẩn bị cuộc thi. Khi nền tảng đã được cài và bàn giao, chuyển thẳng sang C hoặc D.

**B1 — Cài công cụ và kiểm tra môi trường**

| Công cụ | Cách chuẩn bị | Dấu hiệu đã có |
|---|---|---|
| Node.js và npm | Cài từ [trang Node.js](https://nodejs.org/en/download), chọn bản LTS tương thích dependency của repo; mở terminal mới sau khi cài | `node --version` và `npm --version` in phiên bản |
| Python | CLI ForcAD của repo được hướng dẫn dùng Python 3.11; cài/bàn giao môi trường 3.11 và Python Launcher phù hợp | `py -3.11 --version` in Python 3.11.x |
| Docker Desktop | Cài theo [hướng dẫn Windows của Docker](https://docs.docker.com/desktop/setup/install/windows-install/), hoàn tất backend Linux/WSL theo hướng dẫn và mở Docker Desktop | `docker version` có cả Client và Server; `docker compose version` chạy được |
| OpenSSH Client | Nếu chưa có `ssh`, cài OpenSSH Client theo [hướng dẫn Microsoft](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) | `ssh -V` in phiên bản |

Không cần cài OpenSSH Server trên máy Windows chỉ để collector kết nối tới VM. Docker ở đây chạy container Linux của ForcAD.

Kiểm tra trong PowerShell:

```powershell
node --version
npm --version
py -3.11 --version
ssh -V
docker version
docker compose version
```

Nếu một lệnh chưa được nhận diện, hoàn tất cài công cụ tương ứng và mở lại terminal trước khi chạy các bước sau. Với `better-sqlite3`, nếu npm phải biên dịch native và thất bại, cần kiểm tra phiên bản Node và công cụ build phù hợp; không coi website đã cài xong khi `npm install` còn lỗi.

**B2 — Cài website và tạo tài khoản ban tổ chức**

Đây là bước nền tảng làm một lần, không lặp lại việc cài dependency cho mỗi đề nếu môi trường không đổi.

Máy vận hành Windows cần Node.js/npm tương thích dependency của website, Python, OpenSSH client, Docker Desktop hoạt động và đường mạng quản trị tới CyberRangeCZ. CLI ForcAD trong repo được hướng dẫn dùng Python 3.11. Ansible provisioning được CyberRangeCZ chạy qua runner, không yêu cầu chạy trực tiếp trên PowerShell.

Trong PowerShell:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website'
npm install
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Sửa `.env`: `PORT`, `NODE_ENV`, `SESSION_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `FORCAD_URL`. Với cấu hình local hiện tại, `FORCAD_URL=http://127.0.0.1:18080`. Tài khoản ForcAD dùng qua `FORCAD_ADMIN_USER`/`FORCAD_ADMIN_PASSWORD` hoặc đọc từ cấu hình ForcAD sau khi thiết lập.

Có thể mở file bằng `notepad .env` từ thư mục website. Mẫu dưới đây minh họa các dòng cần hoàn thiện; thay giá trị trong dấu `<...>` bằng giá trị của đơn vị:

```dotenv
PORT=3000
NODE_ENV=development
SESSION_SECRET=<chuoi-ngau-nhien-dai>
ADMIN_EMAIL=<email-ban-to-chuc>
ADMIN_PASSWORD=<mat-khau-ban-to-chuc>
FORCAD_URL=http://127.0.0.1:18080
FORCAD_ADMIN_USER=
FORCAD_ADMIN_PASSWORD=
FORCAD_SYNC_INTERVAL=60
```

Tạo chuỗi ngẫu nhiên để điền `SESSION_SECRET` bằng lệnh:

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

`NODE_ENV=development` ở đây dành cho cách chạy HTTP local/LAN trong hướng dẫn. Việc triển khai tên miền/HTTPS cần cấu hình vận hành riêng.

Sau khi sửa cấu hình lần đầu:

```powershell
npm run seed
npm start
```

Mở `http://localhost:3000`, vào `/admin` bằng tài khoản BTC. Những lần bật lại chỉ cần `npm start`; `seed` có thể cập nhật mật khẩu BTC theo `.env` nên không chạy mỗi lần mở một đề.

- **[DÙNG LẠI]:** ứng dụng website, chức năng đăng ký, quản trị và bảng điểm.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** `.env` khi cài ban đầu hoặc đổi nơi chạy.
- **[KHÔNG TÁI SỬ DỤNG]:** nội dung thông báo, lịch đăng ký và danh sách đội của giải khác.
- **Hoàn thành khi:** website hoạt động và BTC quản lý được đội đăng ký. Bảng điểm có thể chưa kết nối khi ForcAD chưa bật.

**B3 — Cài nền tảng ForcAD lần đầu**

ForcAD là nền tảng dùng chung. Không cài lại từ đầu mỗi lần đổi đề.

Mở PowerShell mới nếu terminal website đang bận chạy `npm start`.

Chỉ với một bản chưa thiết lập:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo'
py -3.11 -m pip install -r cli/requirements.txt
if (!(Test-Path config.yml)) { Copy-Item config.yml.example config.yml }
```

Sửa cấu hình ban đầu theo nơi chạy, tài khoản quản trị và yêu cầu cuộc thi. File mẫu có đội/task mẫu, không phải cấu hình đề đã nghiệm thu. Sau đó, chỉ khi chưa thiết lập storage/env:

```powershell
py -3.11 control.py setup
```

Lệnh setup sinh cấu hình storage/env và có thể tạo tài khoản quản trị. Không chạy lại tùy tiện trên storage đang có dữ liệu. Sửa `config.yml` không tự cập nhật đội/task đã nằm trong database.

Khởi động Docker và cập nhật schema điều khiển:

Nếu bản source chưa có `front/dist/`, phải dựng giao diện trước vì Dockerfile nginx chép thư mục này vào image. Chạy từ thư mục ForcAD:

```powershell
Set-Location .\front
npm install
npm run build
Set-Location ..
```

Sau đó, vẫn tại thư mục ForcAD:

```powershell
docker compose up -d --build
docker compose ps -a
docker compose exec -T postgres pg_isready -U forcad
```

Chờ initializer/database sẵn sàng rồi chạy:

```powershell
docker compose exec -T ticker python /app/scripts/setup_round1.py
```

Script schema không bắt đầu thi hoặc tạo flag. Dashboard local ở `http://127.0.0.1:18080/`.

- **[DÙNG LẠI]:** Docker Compose, database engine, scheduler, API, cơ chế chấm và vòng đời.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** cấu hình nền tảng nếu đổi nơi chạy.
- **[KHÔNG TÁI SỬ DỤNG]:** điểm, flag và dữ liệu cuộc thi cũ làm dữ liệu khởi đầu đề mới.
- **Hoàn thành khi:** container hoạt động, schema sẵn sàng và BTC đăng nhập được dashboard.

**B4 — Xác nhận hoàn tất cài nền tảng**

- Website mở được và BTC đăng nhập được bằng tài khoản từ `.env` đã seed.
- Dashboard ForcAD mở được và BTC đăng nhập được bằng tài khoản ForcAD đã thiết lập trong `config.yml`.
- Đây là hai tài khoản quản trị khác nhau; không mặc định chúng có cùng mật khẩu.
- Website lấy điểm và đồng bộ token cần `FORCAD_URL` đúng; sau khi sửa `.env`, khởi động lại website.
- Trước khi có sandbox, nền tảng có thể mở giao diện nhưng chưa kiểm tra được dịch vụ của đội.

**C — Khởi động hằng ngày một bài đã có**

Phần này dùng lab **Meko Boutique** làm ví dụ vì repo đã có profile/nút tương ứng. Chỉ áp dụng khi lab đã được triển khai và cấu hình SSH đúng. Nếu chưa có môi trường thật, làm phần D; chạy Docker không tạo VM CyberRangeCZ.

| Giữ hoạt động | Ở đâu? | Công việc |
|---|---|---|
| Docker Desktop và container | Nền máy vận hành | Engine ForcAD và các storage |
| Terminal website | PowerShell riêng | Chạy `npm start` |
| Terminal collector | PowerShell riêng | Chạy collector đúng lab |
| Sandbox | CyberRangeCZ | VM đội, app và VM checker đang hoạt động |

**C1 — Kiểm tra bài và môi trường VM trước**

1. Xác nhận chọn `meko_boutique`, đọc `labs/meko_boutique/lab.json` để lấy `ssh_config`, `checker_host`, đội/IP và `agent_command` thực tế.
2. Trên Portal CyberRangeCZ, xác nhận môi trường đã allocate/provision thành công. Với pool có sẵn, không tạo lại chỉ vì bật máy vận hành.
3. Kiểm tra SSH tới VM checker và một VM đội. Ví dụ dưới đây dùng đường dẫn hiện khai trong lab, không phải số pool bắt buộc cho mọi máy:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform'
ssh -F '.\ops\pool139\management-config' -o BatchMode=yes checker 'hostname'
ssh -F '.\ops\pool139\management-config' -o BatchMode=yes team1 'hostname'
```

Thành công khi in đúng hostname mà không hỏi mật khẩu. Nếu nhận pool mới, thay đường dẫn bằng bộ truy cập mới và cập nhật `lab.json`. Trên lần kết nối đầu, cần hoàn tất xác minh host key theo bộ truy cập được cấp trước khi thử chế độ không tương tác. Không cần cài lại ứng dụng nếu provisioning đã hoàn tất.

**C2 — Bật ForcAD**

Mở Docker Desktop, đợi engine hoạt động; mở PowerShell:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo'
docker compose up -d
docker compose ps -a
```

Lệnh `up -d` chạy nền nên có thể đóng terminal này sau khi kiểm tra. Nếu vừa thay code/image, làm bước build/nạp lại tương ứng trong phần D thay vì chỉ `up -d`.

Mở `http://127.0.0.1:18080/`, đăng nhập tại `/admin/` nếu được yêu cầu và xem trạng thái cuộc thi đang lưu. Container bật lại không đồng nghĩa tạo lượt thi mới; dữ liệu cũ có thể đang lưu lượt chạy dở.

**C3 — Bật website**

Trong terminal riêng:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website'
npm start
```

Giữ terminal mở. Thành công khi terminal báo website đang chạy và truy cập được `http://localhost:3000`. Mở `/admin` để quản trị website hoặc `/scoreboard` để xem giao diện thi. Không chạy lại `seed` khi chỉ bật website.

**C4 — Bật collector đúng bài**

Trong terminal riêng:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform'
$env:MEKO_LAB = 'meko_boutique'
py -3.11 platform/ForcAD-demo/collect_checker.py
```

Giữ terminal mở; chỉ chạy một collector cho cấu hình đang vận hành. Biến `MEKO_LAB` cần đặt trong chính terminal khởi động collector. Nếu không đặt, loader mặc định là `round1`, dễ dẫn tới chọn nhầm cấu hình.

**C5 — Kiểm tra đội/token và mở lượt thi**

1. Nếu chạy tiếp lượt đã chuẩn bị: xác nhận profile trên dashboard đúng với collector, xem trạng thái rồi dùng nút tiếp tục/bắt đầu phù hợp. Không chuẩn bị lại hoặc reset dữ liệu chỉ để mở giao diện.
2. Nếu là lượt mới chưa chuẩn bị: trên dashboard chọn **Chuẩn bị Meko Boutique (5 task)**. Khi chuyển từ bài khác, hoàn tất dừng/đóng/lưu hồ sơ cũ trước theo quy trình.
3. Sau khi đội ForcAD đã có, kiểm tra tên kỹ thuật của đội trên website và đồng bộ token. Có thể xem báo cáo ở terminal khác:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website'
npm run sync:forcad
```

4. Xác nhận SSH, app, checker và quyền truy cập đội đã được nghiệm thu, sau đó bấm **Bắt đầu** khi sẵn sàng mở thi.
5. Đội đăng nhập website, mở `/scoreboard`, kiểm tra bảng điểm và nộp flag. Phải được cấp đường truy cập VM riêng theo mô hình giải; token website không tự cấp SSH.

Với Round 1, chọn `MEKO_LAB=round1`, đường SSH và đội theo `labs/round1/lab.json`, rồi dùng nút **Chuẩn bị Round 1 (3 task)**. Không trộn collector của một lab với profile lab khác.

File `KHOI-DONG-LAI-MEKO.bat` ở gốc hỗ trợ bật ForcAD, cập nhật schema, mở collector Meko Boutique và dashboard. Nó **không** cài website, chạy website, tạo sandbox hoặc thay thế các kiểm tra ở trên. Chọn cách thủ công hoặc file hỗ trợ; không bật thêm collector thứ hai.

**C6 — Máy khác truy cập thế nào và dừng dự án ra sao?**

- `localhost` là máy đang mở trình duyệt. Máy thí sinh cần dùng `http://<IP-máy-vận-hành>:3000` nếu tổ chức trong LAN; máy chủ phải cho phép cổng website theo cấu hình mạng của đơn vị.
- ForcAD hiện bind `127.0.0.1:18080`, phục vụ BTC/website trên máy vận hành; không mặc định truy cập cổng này từ máy khác.
- IP `10.90.0.x` là mạng lab của ví dụ. Máy vận hành hoặc máy thí sinh chỉ truy cập trực tiếp được khi có đường mạng/VPN/jump access phù hợp; không phải lỗi website nếu thiếu đường mạng này.
- Để dừng: bấm **Dừng** trên dashboard, đợi tác vụ đang xử lý hoàn tất, nhấn `Ctrl+C` trong terminal collector và website, rồi chạy lệnh dưới trong thư mục ForcAD:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo'
docker compose stop
```

`stop` giữ dữ liệu để chạy tiếp. Không dùng reset database, xóa volume hoặc script recycle làm lệnh tắt/bật thông thường. Việc thu hồi sandbox chỉ làm sau khi lưu hồ sơ nếu kết thúc đợt thi.

**D — Tạo bài thi mới sau khi nền tảng đã cài**

Phần này bắt đầu từ danh sách đội trên website. Khi chỉ bật lại bài cũ, dùng phần C và bỏ qua các thao tác tạo đề dưới đây.

**Luồng tạo bài mới**

```text
Cài website nếu chưa có → mở đăng ký → chốt số lượng và tên đội
  → tạo lab.json và bảng đội–VM–IP
  → chuẩn bị topology + provisioning + gói app/checker của đề
  → đăng ký Sandbox Definition → tạo pool → allocate/provision
  → lấy SSH access → hoàn thiện lab.json
  → cấu hình ForcAD + checker adapter → chuẩn bị profile
  → ghép đội website–ForcAD và đồng bộ token
  → chạy collector → thi thử và nghiệm thu → mở thi chính thức
```

**D1 — Chốt danh sách đội từ website**

1. Thu nhận đăng ký, kiểm tra đội đủ điều kiện và chốt danh sách.
2. Đếm số đội chính thức.
3. Trong quản trị đội, khai “Tên đội trên ForcAD” duy nhất. Nếu để trống, website dùng slug của tên hiển thị.
4. Kiểm tra tên kỹ thuật theo quy tắc công cụ export: chữ thường `a-z`, số, dấu `-`, tối đa 32 ký tự, ký tự đầu/cuối là chữ hoặc số.

Ví dụ xuyên suốt tài liệu: đề `round2`, ba đội có tên kỹ thuật `team1`, `team2`, `team3`. Tên hiển thị trên website được giữ riêng.

| Đội website | Tên kỹ thuật | VM dự kiến | IP dự kiến |
|---|---|---|---|
| Tên hiển thị đội A | team1 | team1 | 10.90.0.11 |
| Tên hiển thị đội B | team2 | team2 | 10.90.0.12 |
| Tên hiển thị đội C | team3 | team3 | 10.90.0.13 |

IP trên chỉ là ví dụ; cần chọn subnet phù hợp với cloud, tránh xung đột mạng. Nếu tên VM khác tên kỹ thuật của đội, khai `host` tương ứng trong `lab.json`.

- **[DÙNG LẠI]:** quản lý đội và cơ chế chuẩn hóa tên.
- **[KHÔNG TÁI SỬ DỤNG]:** danh sách đội chốt cho giải khác; phải xác định lại.
- **Hoàn thành khi:** có bảng đội–tên kỹ thuật–VM–IP, không trùng tên/IP.

**D2 — Tạo thư mục đề và xuất đội vào lab.json**

Ví dụ dưới đây chỉ dành cho đề `round2` chưa tồn tại:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform'
if (Test-Path .\labs\round2) { throw 'Đề round2 đã tồn tại; chọn mã khác hoặc kiểm tra cấu hình hiện có.' }
New-Item -ItemType Directory -Path .\labs\round2
Copy-Item .\labs\_template\lab.json .\labs\round2\lab.json
```

Đổi `name` thành `round2`, thay `tasks` bằng danh sách task thật của đề. Sau đó xuất danh sách đội:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website'
npm run export:lab -- --subnet 10.90.0 --start 11
npm run export:lab -- --write round2 --subnet 10.90.0 --start 11
```

Lệnh đầu xem trước, lệnh sau ghi mục `teams` vào lab đã tồn tại. Công cụ hiện tại lấy **toàn bộ đội trong database website**, sắp theo ID và gán IP tuần tự. Nó chưa có bộ lọc đội được duyệt, không tạo VM và không tạo đội ForcAD. Nếu website chứa đội ngoài danh sách thi, phải xử lý danh sách đầu ra cho đúng phạm vi; không xóa hồ sơ lịch sử chỉ để chạy export.

Sau khi kiểm tra, `lab.json` phải có mã đề, task, đội/IP/host. Các trường SSH và lệnh agent hoàn thiện ở D6. Khi `host` trống, loader mặc định dùng `name`.

- **[DÙNG LẠI]:** `export-lab-teams.js`, `labconfig.py`, mẫu cấu hình.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** nội dung `lab.json` cho đề mới.
- **Hoàn thành khi:** danh sách export khớp danh sách thi và bảng ánh xạ đã chốt.

**D3 — Chuẩn bị Sandbox Definition và cách cài app/checker**

Tạo cấu trúc dưới `labs/round2/sandbox/`:

```text
sandbox/
├── topology.yml
├── provisioning/
│   ├── playbook.yml
│   ├── requirements.yml
│   ├── trainee-access.yml
│   ├── group_vars/all.yml
│   └── templates/
├── app/
└── checker/
```

Đây là nơi nhận ứng dụng và checker do tác giả đề cung cấp. Quy trình này không hướng dẫn viết lỗ hổng hoặc thuật toán checker.

Trong `topology.yml`, khai mỗi VM đội theo bảng D1, thêm VM checker, router, mạng và ánh xạ IP. Xác minh tên image, management user, flavor, quota trên cloud đích. Không coi image/flavor của lab mẫu là có sẵn trên mọi cloud.

Trong provisioning, phải cấu hình đủ:

| Việc cài đặt | Thông tin cần khai cho đề |
|---|---|
| Chọn máy đích | Nhóm hoặc danh sách VM đội và VM checker |
| Cài runtime | Các package đúng với ứng dụng và checker |
| Cài ứng dụng | Source, thư mục cài, tài khoản dịch vụ, cổng, biến môi trường |
| Khởi tạo dữ liệu | Dữ liệu ban đầu riêng cho từng đội; không mang flag/dữ liệu lượt trước |
| Chạy dịch vụ | systemd hoặc cơ chế phù hợp, thư mục dữ liệu, quyền sửa/restart cho đội |
| Cài checker | Source, đường dẫn agent, cấu hình IP/URL và thông tin truy cập cần thiết |
| Cấp quyền quản trị | Tài khoản SSH quản trị chạy được lệnh agent không tương tác |
| Kiểm tra sau cài | Dịch vụ hoạt động, máy checker tới được các đội, kết nối chéo đội đúng luật |

Ví dụ **riêng Meko Boutique hiện có**: provisioning cài Apache, Flask/Waitress; đặt app ở `/opt/meko-boutique`; dữ liệu ở `/var/lib/meko-boutique`; tạo service `meko-boutique`; chép `agent.py`, `forcad.py`, `meko_checker.py` lên `/opt/meko-checker`; sinh `/etc/meko-checker/config.json`. Các đường dẫn và package này không phải chuẩn bắt buộc cho đề khác.

Nếu dùng playbook Meko Boutique làm mẫu và thay số đội/tên đội, cần sửa cả:

- `topology.yml`: `hosts`, `net_mappings`, nhóm máy và router/mạng liên quan.
- `group_vars/all.yml`: bảng địa chỉ, tài khoản và tham số theo đội.
- `playbook.yml`: các `hosts: 'team1:team2:team3'`, đường dẫn app/service/checker và task kiểm tra mẫu `backup`.
- `trainee-access.yml`: danh sách `assert`, điều kiện tài khoản quản trị, dòng `Match User team1,team2,team3` và nội dung bảng địa chỉ ghi cho thí sinh.
- Template checker: định dạng cấu hình phải khớp checker của đề.

Chỉ sửa topology hoặc `lab.json` là chưa đủ. `trainee-access.yml` hiện có điều kiện cố định đúng ba đội.

- **[DÙNG KHUNG, PHẢI CHỈNH]:** topology, playbook, cấu hình truy cập, template và cách quản lý service.
- **[KHÔNG TÁI SỬ DỤNG]:** ứng dụng/lỗ hổng/dữ liệu nghiệp vụ, thuật toán `check/put/get`, kỳ vọng test và nội dung đề của một bài khác.
- **Hoàn thành khi:** gói source sạch, các danh sách đội đồng nhất và provisioning có đủ bước cài app/checker.

**D4 — Đưa Sandbox Definition vào CyberRangeCZ**

1. Chuẩn bị repository Sandbox Definition. Nội dung `sandbox/` phải nằm ngay gốc repository: `topology.yml`, `provisioning/`, `app/`, `checker/`.
2. Lưu phiên bản cần triển khai và ghi lại Git URL + revision. Việc đưa repository lên máy chủ Git là thao tác của người triển khai theo quyền được cấp.
3. Trong CyberRangeCZ, mở **Sandbox Definitions**, tạo định nghĩa và nhập URL/revision.
4. Kiểm tra nền tảng đọc được repository và nhận cấu trúc hợp lệ.

Lab Meko Boutique có `package_lab.py` để tạo ZIP đúng cấu trúc. Script này riêng cho lab đó; nếu dùng làm mẫu cho đề mới, phải chỉnh tên/path và quy tắc đóng gói. Bản hiện tại giữ các credential cấu hình trong `group_vars/all.yml`; phải kiểm tra nội dung gói/repository trước khi phân phối.

- **[DÙNG LẠI]:** cách đăng ký định nghĩa qua Git URL/revision.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** công cụ đóng gói và thông tin repository.
- **[KHÔNG TÁI SỬ DỤNG]:** bản đóng gói/revision của đề khác làm mặc định cho đề mới.
- **Hoàn thành khi:** CyberRangeCZ có Sandbox Definition gắn đúng phiên bản đề.

**D5 — Tạo pool, allocate và kiểm tra provisioning**

1. Mở **Pools**, tạo pool từ Sandbox Definition đã đăng ký.
2. Chọn số sandbox theo mô hình tổ chức.
3. Allocate môi trường và theo dõi log tạo VM/mạng/provisioning.
4. Kiểm tra từng VM đúng tên/IP, ứng dụng khởi động được và checker đã cài đủ file.
5. Nếu cài đặt lỗi, sửa provisioning hoặc điều kiện cloud rồi xử lý lại tài nguyên theo chức năng nền tảng trước khi đi tiếp.

Với topology nhiều đội chung một LAN như Meko Boutique, một sandbox có thể chứa cả ba VM đội. Không lấy số đội làm kích thước pool mặc định. Mỗi đợt thi độc lập cần được xác định phạm vi môi trường riêng.

Pool được gắn với revision tại thời điểm tạo. Nếu thay phiên bản Sandbox Definition và cần triển khai revision mới, tạo pool mới theo [tài liệu Pool của CyberRangeCZ](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/); sửa Git không tự cập nhật các máy đang chạy.

- **[DÙNG LẠI]:** quy trình tạo pool, allocate và provisioning của CyberRangeCZ.
- **[KHÔNG TÁI SỬ DỤNG]:** ID pool, VM đang chứa dữ liệu/bản vá/flag của lượt cũ làm môi trường sạch của lượt mới.
- **Hoàn thành khi:** provisioning thành công và cấu trúc thực tế khớp cấu hình.

**D6 — Lấy SSH access và nối máy vận hành với VM checker**

1. Tải bộ management SSH access đúng sandbox/môi trường; lưu nguyên các file cần thiết dưới `ops/<pool-id>/`.
2. Kiểm tra đường dẫn `IdentityFile`, `UserKnownHostsFile`, thông tin gateway/ProxyJump trong SSH config trỏ đúng nơi lưu thực tế.
3. Dùng kết nối quản trị được cấp để xác minh hostname/host key. Sau đó kiểm tra SSH không tương tác, vì collector chạy với `BatchMode=yes`.

Ví dụ, thay `<pool-id>` bằng thư mục thực tế:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform'
ssh -F '.\ops\<pool-id>\management-config' checker 'hostname'
ssh -F '.\ops\<pool-id>\management-config' -o BatchMode=yes checker 'hostname'
ssh -F '.\ops\<pool-id>\management-config' -o BatchMode=yes team1 'hostname'
```

Hoàn thiện `labs/round2/lab.json` bằng thông tin thật. Ví dụ dưới đây dùng nguyên ứng dụng/checker Meko Boutique và ba đội; với checker khác phải thay `agent_command`/task cho đúng:

```json
{
  "name": "round2",
  "ssh_config": "ops/<pool-id>/management-config",
  "checker_host": "checker",
  "agent_command": "sudo -n /usr/bin/python3 /opt/meko-checker/agent.py --config /etc/meko-checker/config.json",
  "agent_timeout": 35,
  "tasks": ["idor", "sqli", "upload", "jwt", "backup"],
  "teams": [
    {"name": "team1", "host": "team1", "ip": "10.90.0.11"},
    {"name": "team2", "host": "team2", "ip": "10.90.0.12"},
    {"name": "team3", "host": "team3", "ip": "10.90.0.13"}
  ]
}
```

Trên VM checker, agent phải nhận JSON từ stdin và trả JSON kết quả đúng giao thức adapter. Khi đổi checker, cần kiểm tra lại tương thích; giữ tên file `agent.py` không tự chứng minh có thể dùng lại logic.

- **[DÙNG LẠI]:** `labconfig.py`, OpenSSH và cơ chế gọi agent qua SSH.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** các trường SSH/agent trong `lab.json`.
- **[KHÔNG TÁI SỬ DỤNG]:** địa chỉ/key/bộ truy cập của pool cũ cho một pool mới.
- **Hoàn thành khi:** SSH quản trị chạy không tương tác và thực thi được lệnh agent.

**D7 — Đăng ký checker adapter, profile và lựa chọn đề mới**

Đây là phần cần người có khả năng chỉnh cấu hình Python/JavaScript. Hệ thống hiện chưa có giao diện nhập đề mới để tự sinh toàn bộ cấu hình. Người vận hành bài có sẵn chỉ cần phần C.

Tạo thư mục `platform/ForcAD-demo/checkers/round2/`. Dùng lại `common.py` từ adapter hiện có nếu agent giữ giao thức JSON đang dùng. Với mỗi task, tạo file wrapper tương ứng. Ví dụ cho task `idor`:

```python
#!/usr/bin/env python3
from common import main
import sys
sys.exit(main('idor'))
```

Wrapper chỉ chọn task; không chứa logic đăng nhập/đọc dữ liệu của bài. Không chép thư mục `rpc/` đang có yêu cầu/phản hồi cũ.

Lưu wrapper với UTF-8 không BOM và xuống dòng LF để shebang chạy đúng trong Linux. ForcAD gọi file checker trực tiếp, nên file phải có quyền thực thi trong container. Với thư mục đề ví dụ đã có, kiểm tra/cấp quyền trong container worker:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo'
docker compose exec -u root celery sh -c 'chmod +x /checkers/round2/*.py'
```

Thư mục checker được mount từ máy vận hành; cần kiểm tra kết quả quyền thực thi theo filesystem của máy triển khai.

Trong `backend/lib/storage/lab_profile.py`, thêm khóa `round2` vào `PROFILES`. Ví dụ chỉ phù hợp khi dùng Meko Boutique, ba đội và cùng quy tắc lịch hiện có:

```python
'round2': {
    'title': 'Round 2',
    'prefix': '/checkers/round2/',
    'tasks': ('idor', 'sqli', 'upload', 'jwt', 'backup'),
    'teams': {
        '10.90.0.11': 'team1',
        '10.90.0.12': 'team2',
        '10.90.0.13': 'team3',
    },
    'hosts': ['team1', 'team2', 'team3'],
    'create_teams': True,
    'flag_template': 'MekoDataCTF{{{body}}}',
    'round_time': 300,
    'ticks_per_round': 10,
    'check_seconds': 60,
    'drain_ticks': 0,
},
```

Tên task/profile/đội/IP phải đồng nhất với `lab.json`. Chọn định dạng flag tương thích với dịch vụ. Thời gian kiểm tra phải đủ cho số đội/task thật; thông số ví dụ không bảo đảm phù hợp khi tăng quy mô. `prepare()` hiện còn đặt `flag_lifetime=2`; trường này chưa cấu hình riêng qua profile.

Dashboard hiện chỉ có lựa chọn các lab đã được viết trong `front/public/round-control.js`. Nếu muốn dùng nút cho đề mới, cần bổ sung nút gọi `prepareLab(..., 'round2', ...)`, cập nhật điều kiện ẩn/hiện/khóa nút và nhãn nhận diện lab. Đây vẫn là chỉnh mã giao diện; chưa có màn hình thêm đề hoàn toàn từ cấu hình.

Sau khi sửa frontend, dựng lại từ thư mục `front/`:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo\front'
npm install
npm run build
Set-Location ..
docker compose restart ticker client-api admin-api
docker compose up -d --no-deps --build nginx
```

Backend các service trên đang mount source; restart để nạp thay đổi profile. Chỉ thực hiện trong giai đoạn chuẩn bị, trước khi bắt đầu lượt thi. Nếu sửa dependency/image thì cần build lại các service liên quan.

- **[DÙNG LẠI]:** `common.py` khi tương thích, collector, cơ chế đọc profile, scheduler và vòng đời trong `competition.py`.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** wrapper task, profile và nút chọn đề.
- **[KHÔNG TÁI SỬ DỤNG]:** logic checker của bài khác chỉ bằng cách đổi tên wrapper.
- **Hoàn thành khi:** profile đã được nạp, các wrapper tồn tại đúng đường dẫn và có cách chọn đề mới.

**D8 — Chuẩn bị cuộc thi ForcAD và ghép đội website**

1. Nếu đang có cuộc thi cũ, hoàn tất dừng/đóng/lưu hồ sơ qua quy trình hiện có trước khi đổi lab.
2. Đăng nhập dashboard và chọn chuẩn bị đúng đề `round2`.
3. Backend nạp profile, đăng ký task, chọn đội hoạt động và lưu lịch. Với `create_teams=True`, đội thiếu được tạo theo IP; với `False` phải có đủ đội trước.
4. Kiểm tra lại tên/IP. Cơ chế tạo đội hiện kiểm tra đội có sẵn bằng IP, nên không bảo đảm tự đổi tên đội cũ tại cùng IP.
5. Trên website, trường “Tên đội trên ForcAD” phải trỏ đúng tên đội hoạt động tương ứng.
6. Xem trước kết quả đồng bộ từ thư mục website:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\MekoDataCTF_Website'
npm run sync:forcad
```

Website đang chạy sẽ tự đồng bộ khi khởi động, định kỳ và khi thông tin đội đổi. Nếu cần đồng bộ ngay bằng CLI, sau khi kiểm tra đúng ánh xạ:

```powershell
npm run sync:forcad -- --apply
```

Đây là lệnh ghi token website sang ForcAD, không tạo VM hoặc đội thiếu. Token nộp flag của đội khác với thông tin SSH và credential nội bộ checker.

- **[DÙNG LẠI]:** cơ chế chuẩn bị profile và dịch vụ đồng bộ token.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** ánh xạ tên đội trên website.
- **[KHÔNG TÁI SỬ DỤNG]:** danh tính/credential của đội giải cũ cho đội mới.
- **Hoàn thành khi:** mọi đội dự thi khớp đúng một đội ForcAD hoạt động và token đã đồng bộ.

**D9 — Chạy collector và nghiệm thu một lượt thi thử**

Trong terminal riêng, giữ chạy trong suốt lượt thi; chỉ chạy một collector cho cấu hình đang vận hành:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform'
$env:MEKO_LAB = 'round2'
py platform/ForcAD-demo/collect_checker.py
```

Collector đọc `lab.json` khi khởi động. Nếu sửa cấu hình, dừng và chạy lại collector trong giai đoạn chuẩn bị để nhận giá trị mới.

Nghiệm thu đủ luồng:

| Kiểm tra | Kết quả cần có |
|---|---|
| Đội/máy | Mỗi đội vào đúng VM và chỉ có quyền truy cập được cấp |
| Dịch vụ | Dịch vụ từng đội hoạt động, kết nối trong mạng đúng luật |
| Checker | ForcAD → wrapper → collector → SSH → agent → app hoạt động |
| Vòng đời flag | `put` lưu được flag; `get` đọc/xác minh được; `check` kiểm tra đúng dịch vụ |
| Nộp flag | Flag hợp lệ được nhận; flag sai/hết hạn được xử lý đúng luật |
| Website | Đăng nhập đội, nộp flag, bảng điểm và trạng thái hiển thị đúng |
| Lịch | Tick, thời lượng kiểm tra và kết thúc phù hợp số đội/task |

Ví dụ Meko Boutique báo `status=101` cho UP. Cần đọc cả nội dung công khai/nội bộ khi lỗi; SSH thông nhưng logic checker sai vẫn chưa đạt nghiệm thu.

- **[DÙNG LẠI]:** collector và trình tự nghiệm thu tích hợp.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** mã lab và địa chỉ kiểm tra.
- **[KHÔNG TÁI SỬ DỤNG]:** kết quả nghiệm thu đề/pool cũ để kết luận đề/pool mới hoạt động.
- **Hoàn thành khi:** có kết quả thi thử xác nhận đầy đủ các mục trên.

**D10 — Chuẩn bị lượt chính thức, cấp truy cập và mở thi**

1. Lưu hồ sơ thi thử và phiên bản source/cấu hình đã nghiệm thu.
2. Tái tạo hoặc đưa app/database/ForcAD về trạng thái sạch qua công cụ phù hợp của đề. Nút bắt đầu lại điểm không mặc nhiên phục hồi source đã vá hay database ứng dụng.
3. Cấp thông tin truy cập VM đúng cho từng đội; không phát bộ management access của BTC cho thí sinh.
4. Kiểm tra nhanh lại dịch vụ, checker và đồng bộ đội sau khi chuẩn bị môi trường sạch.
5. Chuẩn bị profile chính thức, giữ website/Docker/collector hoạt động rồi bắt đầu trên dashboard.
6. Sau thi, lưu kết quả/log/cấu hình phiên bản trước khi thu hồi môi trường hoặc tổ chức lượt khác.

`labs/round1/service/deploy.py` và `recycle.py` phục vụ triển khai/tái tạo dịch vụ Round 1. Không dùng nguyên trạng để phục hồi ứng dụng Meko Boutique hoặc đề khác, vì thao tác source, dữ liệu và kiểm tra sau reset khác nhau.

- **[DÙNG LẠI]:** cơ chế lưu hồ sơ và điều khiển round trong phạm vi giao thức hiện có.
- **[DÙNG KHUNG, PHẢI CHỈNH]:** quy trình cấp truy cập và công cụ phục hồi nếu thay ứng dụng.
- **[KHÔNG TÁI SỬ DỤNG]:** trạng thái flag, điểm, dữ liệu và bản vá của thi thử làm trạng thái ban đầu của lượt chính thức.

**Nhánh tùy chọn — Phân phối bài qua Training của CyberRangeCZ**

Nếu sử dụng giao diện training, tạo Training Definition chứa hướng dẫn/nội dung, tạo Training Instance, gán pool và cấp quyền/token Training Run theo mô hình tổ chức. Cần thiết kế quyền truy cập đúng khi nhiều đội chung một sandbox; không tự coi một Training Run là một đội A/D. Nếu cấp truy cập theo cơ chế riêng của giải, phải ghi rõ cách cấp máy tương ứng.

- **[DÙNG LẠI]:** cơ chế Training Definition/Instance/Run.
- **[DÙNG KHUNG, SỬA CẤU HÌNH]:** lịch, pool, người tham gia và quyền truy cập.
- **[KHÔNG TÁI SỬ DỤNG]:** nội dung level, đề bài, gợi ý, đáp án của một đề khác.

**Những chỗ hiện chưa tổng quát hóa hoàn toàn**

| Thành phần | Hiện trạng cần biết |
|---|---|
| Website → đội thi | Export lấy toàn bộ đội; chưa có bộ lọc danh sách được duyệt cho một đề. |
| `lab.json` → topology/provisioning | Chưa tự sinh đồng bộ; phải cập nhật và đối chiếu. |
| `lab.json` → profile ForcAD | Chưa tự sinh profile; đội/task/IP có thể bị khai trùng ở nhiều file. |
| Dashboard chọn đề | Còn khai nút/nhãn/điều kiện bằng mã JavaScript. |
| Quy tắc flag | Một số giá trị còn cố định trong vòng đời, ví dụ lifetime được chuẩn bị là 2. |
| Provisioning Meko Boutique | Còn danh sách ba đội, tên service/path và task thử cố định. |
| Phục hồi ứng dụng | Phụ thuộc đề, không có một lệnh reset ứng dụng chung đã được chứng minh cho mọi lab. |

Vì vậy, cách diễn đạt đúng với mã nguồn hiện tại là: **tái sử dụng nền tảng, giao vận và trình tự triển khai; tái cấu hình các điểm tích hợp; cung cấp riêng nội dung đề, logic checker và thao tác phục hồi đặc thù.**

**E — Xử lý lỗi theo thành phần**

| Dấu hiệu | Kiểm tra ở đâu? | Hành động tiếp theo |
|---|---|---|
| `node`, `npm`, `py`, `ssh` hoặc `docker` không được nhận diện | B1 | Kiểm tra công cụ/PATH, mở terminal mới sau khi cài. |
| `npm install` lỗi | Terminal website hoặc frontend | Xem lỗi dependency/native build; chưa chuyển sang bước chạy nếu cài chưa thành công. |
| Không mở được website cổng 3000 | Terminal Node, `.env` | Xem lỗi khởi động, cổng bị chiếm hoặc `PORT` đã đổi. |
| Website mở được nhưng không có điểm | ForcAD và `FORCAD_URL` | Kiểm tra cổng 18080, kết nối API và trạng thái round. |
| Không mở được dashboard 18080 | Docker Desktop/container nginx/API | Chạy `docker compose ps -a` và lệnh log dưới đây. |
| SSH timeout | Mạng tới sandbox, gateway, trạng thái VM | Kiểm tra VPN/route/địa chỉ quản trị; chưa phải lỗi tính điểm. |
| SSH báo permission denied | SSH config, key, management user | Đối chiếu bộ truy cập đúng sandbox và đường dẫn key. |
| `SSH collector unavailable` | Terminal collector và mã lab | Kiểm tra collector chạy, `MEKO_LAB` đúng và thư mục adapter khớp. |
| `Sandbox agent unavailable` | SSH, `agent_command`, quyền chạy agent | Thử SSH không tương tác và lệnh agent đúng cấu hình. |
| Chỉ một task lỗi | Checker/app của task đó | Đọc log và logic riêng của đề; collector thông không chứng minh nghiệp vụ đúng. |
| Không ghép được đội/token | Website và ForcAD | So sánh tên kỹ thuật, đội active và báo cáo `sync:forcad`. |
| Thay config nhưng không có tác dụng | Tiến trình đang giữ cấu hình cũ | Restart website/collector hoặc nạp lại profile theo thành phần đã đổi. |

Trong thư mục ForcAD, xem log khi cần:

```powershell
Set-Location 'C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\platform\ForcAD-demo'
docker compose logs --tail 50 nginx client-api admin-api ticker initializer
```

Khi nhờ người khác hỗ trợ, ghi mã lab, bước đang thực hiện, thành phần lỗi và thông báo lỗi; không gửi nguyên file `.env`, SSH private key hoặc token đội.

**Nguồn đối chiếu**

- [Workflow CyberRangeCZ](https://docs.platform.cyberrange.cz/basic-concepts/typical-training-workflow/training-workflow-cloud/).
- [Cài Node.js](https://nodejs.org/en/download).
- [Cài Docker Desktop trên Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
- [OpenSSH trên Windows](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).
- [Hướng dẫn khởi động hệ thống](HUONG-DAN-KHOI-DONG.md).
- [Công cụ xuất đội](../platform/MekoDataCTF_Website/scripts/export-lab-teams.js).
- [Profile ForcAD](../platform/ForcAD-demo/backend/lib/storage/lab_profile.py).
- [Collector](../platform/ForcAD-demo/collect_checker.py).
- [Provisioning Meko Boutique](../labs/meko_boutique/sandbox/provisioning/playbook.yml).
- [Cấu hình quyền truy cập Meko Boutique](../labs/meko_boutique/sandbox/provisioning/trainee-access.yml).
- [Triển khai Meko Boutique](../labs/meko_boutique/docs/DEPLOYMENT.md).
