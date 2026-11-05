# Fashion Shop — thiết kế lại, tick và CyberRangeCZ

Ngày cập nhật: 04/11/2026.

## 1. Nộp những gì

- **CyberRangeCZ:** `labs/fashion_shop/meko-fashion-sandbox.zip`. Giải nén vào gốc repository Sandbox Definition: `topology.yml`, `provisioning/`, `app/`. Portal sử dụng URL repository và branch/commit chứa cấu trúc này; không tải ZIP thay cho Git URL nếu giao diện yêu cầu repository.
- **Báo cáo:** tài liệu này và `labs/fashion_shop/report/tick-redesign/` (ảnh desktop/mobile và các luồng chức năng).
- **Toàn bộ mã nguồn + test:** `labs/fashion_shop/meko-fashion-shop.zip`. Đây là gói bàn giao đầy đủ, có thư mục bọc `fashion_shop`; không import gốc gói này trực tiếp vào CyberRange.
- Không nộp `.qa-*`, `.local-teams`, `data/`, state database, mật khẩu, SSH key hoặc profile trình duyệt.

Tạo lại cả hai ZIP từ gốc workspace bằng `py labs/fashion_shop/package_lab.py`. Gói Sandbox chỉ xuất danh sách source cho phép, không thu gom dữ liệu runtime.

## 2. Kết luận từ log được cung cấp

Log cho thấy cả bốn VM đi qua tạo mật khẩu, tạo user, cấu hình SSH, `sshd -t` và `sshd -T` với `rc=0`. Policy trả về `passwordauthentication yes`, `pubkeyauthentication no`, `authenticationmethods password` cho `user-access`.

File dừng giữa `stdout_lines` của `Read effective trainee SSH policy`, không có `fatal`, `FAILED` hoặc `PLAY RECAP`. Vì vậy chưa thể khẳng định nguyên nhân lỗi cuối cùng của lần provisioning đó.

Lỗi Sandbox Agenda được cung cấp sau đó xác định một lỗi khác, ở bước parse topology: `Group.name` phải khớp `^[a-z][a-z0-9A-Z-]*$`. Tên `fashion_shops` trong bản bàn giao trước vi phạm schema vì có dấu gạch dưới. Đã sửa `sandbox/topology.yml` thành `fashion-shops` và đóng gói lại cả hai ZIP. Nhận định trước đây khuyên dùng tên có gạch dưới là sai đối với schema CyberRangeCZ này. Ansible có thể cảnh báo tên group chứa dấu gạch ngang; không đổi sang gạch dưới để xử lý warning đó. Playbook chọn trực tiếp `team1:team2:team3:team4`, nên không phụ thuộc cú pháp truy cập group chứa dấu gạch ngang.

Kiểm thử hồi quy `test_topology_names_match_cyberrange_schema` đã tái hiện lỗi (1 FAIL, 2 PASS trong test_cyberrange.py trước sửa), kiểm tra tên các thực thể topology và node của group. Sau sửa cần dùng source/ZIP mới, cập nhật revision Sandbox Definition trên portal rồi thử tạo lại sandbox. Không chỉ chạy lại provisioning từ revision cũ.

Không có file `AGENTS.md` hay `docs/CODEX-NAVIGATION-GUIDE.md` trong workspace lúc kiểm tra; đã dùng hướng dẫn người dùng dán trong chat.

## 3. Các bước sửa và vị trí file

Mọi đường dẫn dưới đây tính từ `labs/fashion_shop/`.

| Bước | File | Thay đổi |
|---|---|---|
| 1 | `tests/test_rounds.py` | Test trước: đổi flag và locator của 5 bài, hết hiệu lực đường dẫn cũ, restart, tài khoản thật, bản vá và team riêng |
| 2 | `sandbox/app/rounds.py` | Tick lưu trong bảng `fashion_round` của `customers.db`; cập nhật hồ sơ và bảng catalog trong transaction SQLite có ATTACH |
| 3 | `sandbox/app/app.py` | Nạp tick trước mỗi request, khóa giữa các thread, API locator công khai không có flag, tài liệu upload/backup động, no-store |
| 4 | `sandbox/app/templates/shop.html`, `sandbox/app/static/shop.css` | Giao diện kem/nâu, typography và hero mới, bố cục mobile, ưu đãi có mã hiện tại |
| 5 | `sandbox/provisioning/playbook.yml` | Đường dẫn source theo playbook_dir, biến tick, GUI tùy chọn, health không qua proxy và kiểm tra HTTP giữa team |
| 6 | `sandbox/provisioning/trainee-access.yml` | Giữ password-only riêng từng team, khóa Kali mặc định, thêm kiểm tra key management trước reload; ẩn output sshd -T dài |
| 7 | `sandbox/provisioning/desktop.yml` | Kiểm tra có package Kali trước khi cài XFCE, báo rõ nếu image/repository không phù hợp |
| 8 | `tests/test_cyberrange.py` | Contract offline cho đường dẫn deploy, tùy chọn desktop, peer health và management SSH |
| 9 | `tests/browser_qa.mjs` | Dùng locator hiện tại, cấu hình CDP/output qua môi trường; test browser không phụ thuộc ID/path cố định |
| 10 | `package_lab.py`, `README.md` | Xuất riêng gói Sandbox với topology ở gốc và cập nhật hướng dẫn |

Các file lab đã có sẵn ở trạng thái untracked khi bắt đầu. Không commit/push và không thay đổi các artifact/dashboard khác của workspace.

## 4. Quy tắc tick và flag

Mặc định mỗi tick dài **120 giây**, tính từ lần khởi tạo dữ liệu trên từng VM. Tick đầu là 0, giữ locator cũ để tương thích dữ liệu bài cũ. Khi hết thời gian, request kế tiếp tính số tick đã trôi qua rồi cập nhật; không cần cron/thread nền. Nếu không có HTTP traffic, không ghi dữ liệu vô ích. Tick chưa đồng bộ theo đồng hồ cuộc thi trung tâm.

| Bài | Vị trí thay đổi sau tick |
|---|---|
| IDOR | ID hồ sơ khách VIP giả, từ vùng 3000 trở lên; không cố định tăng 1 hay tăng 4 |
| SQLi | Tên bảng supplier_notes theo tick, vẫn có cột secret để thực hành UNION |
| Upload | Tên tài liệu private trong kho mẫu in; JSON preview_path vẫn là điểm yếu |
| JWT | Mã offer trên `/vip?offer=...`; vẫn cần khai thác alg=none và role=vip |
| Backup | Tên file export `.sql.bak`; robots.txt gợi ý file hiện hành |

`GET /api/collection` trả `tick` và `locators`: đây là dữ liệu tra cứu bài, không chứa flag/password. Checker hoặc script khai thác phải lấy lại locator mỗi tick. Không dùng cố định `/profile/1`, `supplier_notes`, `design-brief.txt` hoặc `shop.sql.bak` cho các tick sau.

Flag là chuỗi `FLAG{...}` ngẫu nhiên mới cho từng bài, từng team. Locator và flag là hai thứ riêng: 3001/3005 trong ví dụ là mã đối tượng, không phải giá trị flag. Flag cũ hết hiệu lực ở dữ liệu hiện tại, không có grace period. Chưa có endpoint nộp flag hoặc tích hợp chấm điểm ForcAD; scoring trung tâm phải được tích hợp riêng trước khi tổ chức thi thật.

Restart giữ tick, session secret, tài khoản đã đăng ký và `patches.json`; không ghi đè source theo tick. Dữ liệu legacy được chuyển sang bảng round khi chạy lần đầu. Bản export/brief tĩnh cũ được loại khỏi thư mục dữ liệu để tránh lộ flag cũ. Không tự xóa tài khoản hoặc uploads.

Chạy **một process Waitress** như unit/Compose cung cấp; nhiều thread được khóa để response không đi qua thời điểm rotation. Không triển khai nhiều WSGI worker cùng một DATA_DIR. Mỗi team phải có DATA_DIR riêng trên filesystem local. ID khách thật dành vùng 2–2999; lab trả 409 khi đầy vùng này.

Đổi khoảng tick trên VM qua biến Ansible `fashion_tick_seconds`; khi chạy local dùng `FASHION_TICK_SECONDS`. Giá trị phải là số nguyên dương. Không giảm/tăng khoảng tick trong lúc thi vì ảnh hưởng cách tính các tick đã trôi qua.

## 5. Kali và SSH riêng từng team

Theo xác nhận của người dùng: **khóa tài khoản kali mặc định**, không đặt mật khẩu rỗng. Nếu có user kali, khóa password, hết hạn account, shell nologin. User management của image là `debian`, không được dùng kali hoặc user-access để provisioning.

Mỗi team SSH bằng user `user-access`, password ngẫu nhiên riêng, không dùng public key trainee, không có sudo. Password được sinh một lần, giữ qua lần provisioning sau. Tài khoản web được đăng ký riêng.

Quản trị viên lấy mật khẩu trên từng VM thông qua management:

```bash
sudo cat /var/lib/fashion-access/credentials.json
```

Chỉ chia sẻ trường `ssh_password` của đúng team. Nếu bật GUI, dùng `vnc_password` của team đó. File quyền 0600, thư mục 0700, task secret no_log. Không đưa file này vào Git hoặc báo cáo nộp công khai. Có thể cung cấp hash SHA-512 crypt riêng qua `fashion_trainee_password_hashes`; xem `HUONG-DAN-SSH.md` để override.

Thí sinh kết nối từ đường truy cập mạng sandbox đã cấp, ví dụ team1:

```bash
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password user-access@10.90.0.11
```

Management key của nền tảng vẫn dùng riêng; playbook kiểm tra policy key management trước reload SSH. Open GUI của portal còn phụ thuộc image được cloud đánh dấu GUI Access và đường VNC; không thể bật metadata cloud chỉ bằng cài XFCE trên guest.

## 6. Quy trình đưa vào CyberRangeCZ

1. Chạy test local và `py labs/fashion_shop/package_lab.py`.
2. Giải nén **meko-fashion-sandbox.zip** vào thư mục repo lab riêng. Kiểm tra `topology.yml` ngay ở gốc, không ở `sandbox/` hoặc `fashion_shop/`.
3. Kiểm tra cloud có image `kali`, management user `debian`, flavor `standard.kali`; router dùng `debian-12-x86_64` / `standard.small`. Kiểm tra CIDR 10.90.0.0/24 và WAN 100.110.0.0/24 không trùng mạng hiện có.
4. Người vận hành review rồi commit/push repo đến branch dùng để nộp. Phiên làm việc này chưa push, chưa tạo repo và chưa import pool.
5. Trên portal tạo/cập nhật Sandbox Definition bằng Git URL và branch/revision chứa source mới, sau đó tạo pool/sandbox mới. Pool cũ giữ topology/inventory cũ không chứng minh revision mới đã được áp dụng.
6. Chạy provisioning. Không bắt buộc role/collection bên ngoài: các task dùng ansible.builtin. Giữ GUI mặc định; nếu chỉ cần SSH+HTTP, cấu hình `fashion_desktop_enabled: false` trong biến Ansible được worker/pool nạp.
7. Xác nhận PLAY RECAP có failed=0 cho bốn team, local `/health` trả đúng team, peer health HTTP :80 qua Apache giữa team thành công. Kiểm tra security group/routing nếu local được nhưng peer thất bại.
8. Lấy password của đúng VM, kiểm tra SSH password thành công, key trainee bị từ chối, management key vẫn hoạt động và user kali không đăng nhập được.
9. Mở shop của team, đăng ký, đọc `/api/collection`, đợi qua tick rồi đọc lại. Khai thác từng bài bằng locator mới; bật patch tương ứng rồi kiểm tra không lấy được flag mà tính năng hợp lệ vẫn chạy.

Khi lỗi, cần lưu log từ task thất bại đến PLAY RECAP và journal của dịch vụ tương ứng. Không chỉ chụp output `sshd -T`.

```bash
sudo systemctl status fashion-shop --no-pager
sudo journalctl -u fashion-shop -n 100 --no-pager
sudo /usr/sbin/sshd -t
sudo apache2ctl configtest
sudo systemctl status apache2 --no-pager
curl --noproxy '*' http://127.0.0.1/health
```

Đã đối chiếu source tham khảo [MekoDataCTF/main/provisioning/playbook.yml](https://github.com/NguyenThanhDatttttttt/MekoDataCTF/blob/main/provisioning/playbook.yml) và [topology.yml](https://github.com/NguyenThanhDatttttttt/MekoDataCTF/blob/main/topology.yml): giữ cấu trúc gốc repository, đường dẫn theo playbook_dir, dịch vụ systemd và health retry không qua proxy. Repo tham khảo hiện không cung cấp branch IDOR qua API lúc kiểm tra; đã đọc main. Không sao chép policy public-key trainee vì người dùng yêu cầu password-only.

## 7. Kiểm chứng và giới hạn

TDD: trước sửa, `test_rounds.py` có 5 FAIL vì thiếu API/tick và validation; `test_cyberrange.py` có 2 FAIL vì thiếu điều kiện GUI và kiểm tra management. Sau sửa, bộ 54 test local PASS. Browser CDP local PASS: ảnh offline, đăng ký, đăng nhập, tìm kiếm, cả 5 bài khai thác qua HTTP và mobile không tràn ngang. Ảnh mới ở `report/tick-redesign/`; báo cáo HTML/ảnh cũ ở `report/` là baseline trước thiết kế mới.

Coverage cuối: **97%** (281 statements, 9 chưa phủ); `app.py` 97%, `rounds.py` 97%. Đã chạy coverage với thư viện cài riêng trong `.qa-tools`, không sửa Python hệ thống. Lượt đầu bị lỗi quyền thư mục temp có sẵn; chạy lại với `--basetemp=labs/fashion_shop/.qa-coverage-final -p no:cacheprovider` đã PASS 54/54. Không dùng kết quả coverage 11% từ lượt lỗi setup.

Lệnh test nhanh từ gốc workspace:

```powershell
py -m pytest labs/fashion_shop/tests -q
```

Chưa chạy OpenStack/CyberRangeCZ thật, chưa kiểm chứng SSH/VNC trên image thực, chưa build Docker và chưa tích hợp scoring. Test provisioning là contract YAML offline, không thay thế chạy Ansible thật. Không khẳng định đã sửa được lỗi cuối log vốn chưa được cung cấp.

## 8. Tự đánh giá

Áp dụng skill agent-self-evaluation: chính xác 4/5 (có test/HTTP, thiếu pool thực); đầy đủ 4/5 (source, tick, access, gói nộp, tài liệu hoàn tất; scoring chưa tích hợp); rõ ràng 4/5 (có bảng file và các bước, cần quản trị viên đối chiếu UI portal); khả thi 4/5 (ZIP đúng cấu trúc, cần image/flavor và Git URL thực); súc tích 4/5 (tài liệu dài để tái hiện triển khai). Trung bình 4.0/5. Ưu tiên nghiệm thu tiếp: chạy pool thật, lấy log thất bại đầy đủ nếu còn lỗi, sau đó tích hợp tick/scoring trung tâm.

## 9. Log tiếp theo: VNC chiếm cổng 5900 và yêu cầu Apache

Log có PLAY RECAP: cả bốn team FAILED tại `Require the VNC port to be free on first start`, thông báo `Timeout when waiting for 127.0.0.1:5900 to stop`. Đây là lỗi xung đột listener VNC trước bước cài web. Service facts của team2 ghi lightdm running, fashion-desktop inactive, apache2 inactive/disabled. Log không chứa PID/socket owner để kết luận tiến trình cụ thể nào đang giữ 5900; không tự dừng LightDM hoặc kill tiến trình chỉ từ suy đoán.

Các sửa đổi tiếp theo:

1. `provisioning/desktop.yml`: không yêu cầu cổng 5900 của image trống. Desktop lab chuyển sang `fashion_vnc_port` mặc định 5901; X display `fashion_vnc_display` mặc định 9. Kiểm tra và khởi động dùng cùng giá trị. Cho phép cổng 5901–5999, display 1–99. Service facts dùng no_log để không tràn log. Thay mật khẩu VNC có notify restart.
2. `provisioning/files/fashion-desktop.service`: render bằng template với đường dẫn nguồn theo playbook_dir. TigerVNC chỉ nghe loopback, chạy user-access, yêu cầu VncAuth; không thay listener 5900 của image.
3. `provisioning/apache.yml`, `provisioning/files/fashion-shop-apache.conf`: cài Apache, bật proxy/proxy_http, VirtualHost :80, ProxyRequests Off, ProxyPass/ProxyPassReverse tới 127.0.0.1:8080. Bỏ symlink site welcome 000-default; chạy apache2ctl configtest trước start/reload, enable apache2 khi boot.
4. `provisioning/playbook.yml`: backend fashion-shop bind loopback :8080. Apache là dịch vụ web công khai. Health local và chéo team dùng cổng 80. Desktop chạy sau deploy/health web, để lỗi GUI không ngăn web được cài và kiểm tra.
5. `trainee-access.yml`, shortcut desktop, README, hướng dẫn SSH/GUI: URL public `http://10.90.0.11/`, URL local `http://127.0.0.1/` qua Apache.
6. `package_lab.py`: thêm apache.yml vào cả hai gói ZIP; Apache config xuất theo allowlist provisioning/files.

Kiến trúc: **Apache reverse proxy → Waitress/Flask**. Không dùng PHP hoặc mod_wsgi. Giữ một process Waitress để bảo toàn khóa tick. Nguồn: [Apache Reverse Proxy Guide](https://httpd.apache.org/docs/2.4/howto/reverse_proxy.html), [TigerVNC Xvnc](https://tigervnc.org/doc/Xvnc.html).

Desktop riêng đi qua SSH password của team:

```bash
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password -N -L 15901:127.0.0.1:5901 user-access@10.90.0.11
```

Mở VNC viewer đến host 127.0.0.1, port 15901 (TigerVNC có thể nhập `127.0.0.1::15901`), dùng vnc_password riêng của team. Open GUI portal hiện có vẫn dùng VNC native của image; đổi cổng guest không tự sửa Guacamole. Không khẳng định password VNC lab dùng được với listener native 5900. User kali vẫn bị khóa; cần nghiệm thu đăng nhập GUI native riêng.

Sau khi cập nhật repo/revision và chạy lại provisioning, kiểm tra bằng management:

```bash
sudo apache2ctl configtest
sudo systemctl status apache2 fashion-shop fashion-desktop --no-pager
sudo ss -ltnp '( sport = :80 or sport = :8080 or sport = :5900 or sport = :5901 )'
curl --noproxy '*' http://127.0.0.1/health
curl --noproxy '*' http://10.90.0.12/health
sudo journalctl -u apache2 -u fashion-shop -u fashion-desktop -n 100 --no-pager
```

Mong đợi Apache :80, backend chỉ 127.0.0.1:8080, VNC lab chỉ loopback :5901. Nếu 5901/display9 cũng bận, chọn cặp cổng/display còn trống qua biến Ansible. Có thể đặt fashion_desktop_enabled=false để chạy SSH+Apache khi chưa cần desktop riêng.

TDD trước sửa: **3 FAIL, 17 PASS** (VNC còn 5900, chưa hỗ trợ override cổng/display, backend còn bind mọi interface). Sau sửa: **57 PASS** toàn bộ test local. Test mới kiểm tra contract deploy Apache, backend loopback, template VNC và cổng mặc định/override. Không có Apache/Ansible sẵn trong Ubuntu WSL và Docker daemon không chạy; chưa chạy apache2ctl hoặc Ansible trên VM thật ở phiên này. Coverage 97% tại mục 7 là kết quả ứng dụng trước thay đổi provisioning; không đổi logic ứng dụng trong lần sửa này.

## 10. Log tiếp theo: Apache thiếu thư mục log (AH02291)

Log mới cho thấy cả bốn VM FAILED tại `Validate the complete Apache configuration`. Lỗi gây dừng là `AH02291: Cannot access directory '/var/log/apache2/'` cho main error log và VirtualHost; configtest trả rc=1. Cảnh báo `AH00557`/`AH00558` cho hostname team1–team4 chưa resolve là vấn đề riêng, không phải nguyên nhân thiếu thư mục. Gói apache2 đã có trên image tối giản không bảo đảm các thư mục runtime/log còn tồn tại; `apt state=present` không tạo lại chúng khi package đã cài.

Đã sửa `labs/fashion_shop/sandbox/provisioning/apache.yml`:

1. Sau cài package và trước configtest/start/reload, tạo lại `/var/log/apache2` (root:adm, 0750), `/run/apache2` (root:root, 0755), `/var/lock/apache2` (www-data:www-data, 0755) bằng ansible.builtin.file state=directory. Không xóa log cũ, không mở quyền ghi thư mục log cho thí sinh.
2. Tạo `/etc/apache2/conf-available/fashion-shop-servername.conf` với `ServerName 127.0.0.1`, bật qua symlink trong conf-enabled, notify Reload Apache. Đây là cấu hình toàn cục, không chỉ ServerName trong VirtualHost. [Tài liệu Apache ServerName](https://httpd.apache.org/docs/2.4/mod/core.html#servername).
3. Giữ nguyên configtest bắt buộc trước start/reload. Không bỏ qua lỗi bằng ignore_errors hoặc ép rc=0.
4. Thêm test `test_apache_directories_and_global_servername_exist_before_configtest` trong tests/test_cyberrange.py để kiểm tra đường dẫn, owner/mode, symlink bật cấu hình và thứ tự chuẩn bị trước configtest.

TDD: test_cyberrange.py trước sửa **1 FAIL, 4 PASS** vì thiếu bước tạo directory; sau sửa toàn bộ **58 test PASS** (`py -m pytest labs/fashion_shop/tests -q`). Đóng gói lại cả hai ZIP với apache.yml mới. Đây là test contract offline; chưa chạy lại Apache trên pool người dùng nên chưa khẳng định tất cả bước tiếp theo đã thành công.

Cập nhật source/revision Sandbox Definition rồi reprovision. Log mới phải có hai task `Restore Apache directories missing from minimal images` và `Configure a resolvable global Apache server name`; nếu thiếu thì worker vẫn đang dùng source cũ. Khi nghiệm thu bằng management:

```bash
sudo ls -ld /var/log/apache2 /run/apache2 /var/lock/apache2
sudo cat /etc/apache2/conf-enabled/fashion-shop-servername.conf
sudo apache2ctl configtest
sudo systemctl status apache2 --no-pager
curl --noproxy '*' http://127.0.0.1/health
```

Mong đợi configtest `Syntax OK`, apache2 active và health trả đúng team. SSH password riêng từng team, tài khoản kali bị khóa, backend loopback, tick/flag và VNC 5901 không đổi trong lần sửa này.

## 11. Log tiếp theo: Apache hoạt động, fashion-desktop lỗi lúc khởi động

### Bằng chứng và chẩn đoán

File log mới có 2004 dòng, gồm một lần chạy có PLAY RECAP failed=1 trên cả bốn team, rồi phần đầu một lần chạy tiếp bị cắt. Lần chạy đầy đủ xác nhận:

- Apache configtest rc=0, `Syntax OK` trên bốn team.
- `/health` qua Apache trả HTTP 200 và đúng team1–team4.
- Kiểm tra HTTP chéo đội và kiểm tra danh tính peer đi qua trước phần desktop.
- Cổng lab 5901 trống; lỗi ở `Start the desktop service`, thông báo systemd `control process exited with error code`.
- Không có nội dung journal hay exit status của ExecStartPre trong log. Vì vậy chưa xác nhận nguyên nhân chính xác trên VM; không kết luận đã sửa xong desktop trên cloud.

Unit hiện có `ExecStartPre=tigervncserver -list -cleanstale`. Đã kiểm tra mã package TigerVNC: wrapper gọi sanityCheck trước xử lý tùy chọn -list; sanityCheck yêu cầu `hostname -f` trả hostname. Log Apache trước đó từng ghi hostname team1–team4 không resolve. Đây là giả thuyết có bằng chứng, không phải lỗi đã được journal của VM xác nhận.

### Tái hiện cô lập

Đã tải và giải nén **tigervnc-common/tigervnc-standalone-server 1.13.1+dfsg-2build2 từ Ubuntu 24.04** vào `.qa-vnc-source` trong workspace; không cài package hệ thống, không đổi hostname thật, không khởi động X/VNC. Chạy module `TigerVNC::Common::sanityCheck` thật với chương trình hostname giả lập theo PATH:

```text
FQDN_READY=0 rc=1 -e: Could not acquire fully qualified host name of this machine.
FQDN_READY=1 rc=0
PASS real TigerVNC Common.pm sanity check: missing hostname fails; resolved hostname passes
```

Đây là kiểm chứng cơ chế trên package Ubuntu, không phải nghiệm thu phiên bản TigerVNC đang cài trên Kali của pool. Tài liệu Debian testing cũng xác nhận wrapper mới dùng `~/.config/tigervnc` và có tùy chọn -list/-cleanstale: [tigervncserver manual](https://manpages.debian.org/testing/tigervnc-standalone-server/tigervncserver.1.en.html).

### Các bước sửa và file

1. `sandbox/provisioning/desktop.yml`: chạy `/bin/hostname -f`. Chỉ nếu rc khác 0 hoặc stdout rỗng, thêm block riêng vào `/etc/hosts`: `127.0.1.1 {{ ansible_hostname }}`; giữ nguyên các dòng cũ. Chạy hostname -f lần nữa và yêu cầu thành công trước khởi động VNC. Không thay hostname của VM hay sửa DNS cloud.
2. Tạo `.config` và `.config/tigervnc` dưới /home/user-access với owner user-access, mode 0700; giữ đường dẫn password riêng `.vnc/passwd` được truyền tường minh cho server. Bổ sung package xauth/xfonts-base để chuẩn bị runtime, không khẳng định chúng đang thiếu trên VM.
3. Bọc start/restart, kiểm tra RFB và XFCE trong block/rescue. Nếu lỗi, đọc `systemctl show` (Result, ActiveState, ExecMainStatus, ExecStartPre) và 80 dòng journal gần nhất, rồi fail với nội dung chẩn đoán. Không ignore_errors và không biến desktop lỗi thành PASS.
4. `sandbox/provisioning/playbook.yml`: bỏ handler Restart fashion desktop riêng. Thay đổi helper/password/unit quyết định restarted ngay trong block có rescue; không còn lần restart qua handler nằm ngoài vùng chẩn đoán. Khi không có thay đổi, chỉ bảo đảm state started.
5. `tests/test_desktop.py`: kiểm tra hostname hợp lệ không bị ghi lại hosts, hostname lỗi được sửa trước start, có thư mục cấu hình mới, lỗi startup in journal và vẫn fail; kiểm tra handler desktop cũ đã được bỏ.

TDD: trước sửa **2 FAIL, 16 PASS** trong test_desktop.py; sau sửa **60 test PASS** toàn bộ lab. Hai ZIP đã được tạo lại và kiểm tra nội dung provisioning. `.qa-vnc-source` (gồm .deb, mã package và script tái hiện) không nằm trong các gói nộp.

### Chạy lại và nghiệm thu

Thay source bằng ZIP mới, cập nhật repo/revision rồi reprovision. Log phải có `Check the hostname required by TigerVNC` và `Verify the hostname before launching the VNC wrapper`. Nếu desktop vẫn lỗi, phần `Explain the desktop failure without hiding it` sẽ có journal để xác định bước tiếp; không cần đoán từ thông báo systemd chung chung.

Người vận hành có management access có thể kiểm tra:

```bash
hostname -f
sudo systemctl show fashion-desktop -p Result -p ActiveState -p ExecMainStatus -p ExecStartPre
sudo journalctl -u fashion-desktop -n 80 --no-pager
sudo ss -ltnp '( sport = :5901 )'
```

Giữ Apache cổng 80, backend loopback 8080, desktop loopback 5901, SSH password riêng từng team và khóa user kali. Nếu chỉ nghiệm thu web/SSH lúc này, có thể chủ động đặt fashion_desktop_enabled=false; không tự tắt desktop để che lỗi trong bản mặc định.

### Báo cáo agent-introspection-debugging

- Mục tiêu: hoàn thành lab với Apache, tick, SSH riêng và desktop chạy được trên pool.
- Thất bại: các contract offline trước đây không kiểm tra điều kiện hostname thật của wrapper; log systemd thiếu journal nên chẩn đoán bị hạn chế.
- Phục hồi: thu hẹp tới lệnh pre-start, đọc mã package và tái hiện sanityCheck cô lập; sửa có điều kiện, thêm chẩn đoán service thất bại.
- Kết quả: partial ở mức triển khai cloud; code/test/export hoàn tất local, cần reprovision để xác nhận desktop. Chưa tuyên bố root cause VM chắc chắn hoặc cloud PASS.
- Phòng ngừa: giữ kiểm tra hostname và journal tự động trong provisioning để tránh vòng lặp gửi log chung chung.

Tự đánh giá lần này: accuracy 4/5 (đã tái hiện cơ chế nhưng chưa có journal Kali), completeness 4/5 (source/test/gói/docs hoàn tất, cloud chưa nghiệm thu), clarity 4/5 (phân biệt bằng chứng và giả thuyết), actionability 4/5 (có gói mới và task chẩn đoán), conciseness 4/5 (ghi đủ các bước để tái hiện). Trung bình 4.0/5.

## 12. Pool mới không tạo xong: team4 UNREACHABLE ở provisioning hạ tầng

Người dùng xác nhận đây là **pool mới đang tạo**, chưa có gói SSH management để tải. Không yêu cầu người dùng cung cấp key ở giai đoạn này. Câu hỏi trước đó của agent về file management config không phù hợp giai đoạn và đã được đính chính.

### Bằng chứng từ log

- Nền tảng checkout tag v2.2.1, commit c5b7bce; thông báo detached HEAD là thông tin Git khi checkout tag, không phải lỗi gây dừng.
- Task lỗi là Gathering Facts trong play `Sandbox networking for netplan hosts`, file `/app/ansible_repo/provisioning/networking-hosts.yml` của provisioning hạ tầng.
- Chỉ team4, management IP **192.168.131.25**, bị SSH rc=255: `kex_exchange_identification: Connection closed by remote host`, kèm `Connection closed by UNKNOWN port 65535`.
- Worker thử lại tới attempt 20. Gathering Facts mất khoảng 1123 giây; không có bằng chứng rằng chỉ cần đợi boot thêm vài giây là đủ.
- PLAY RECAP: team4 ok=0, unreachable=1, failed=0; team1–team3/gateway/man/proxy-jump không unreachable. failed=0 không có nghĩa pool thành công khi unreachable=1.
- Không thấy play `Install one independent fashion shop on each team VM` trong log. Apache, desktop, tick và password-only trainee của Fashion Shop chưa chạy trong lần tạo pool này.

Log không chỉ ra chắc chắn kết nối bị đóng ở VM đích hay một hop proxy-jump/MAN. UNKNOWN port 65535 không đủ căn cứ để mở port 65535. Worker dùng user debian và PasswordAuthentication=no cho management; đây là kết nối riêng với user-access/password của thí sinh.

### Cần xử lý ở đâu

Việc lỗi nằm ở bước tạo pool/provisioning hạ tầng trước khi chạy source lab. Thêm task vào playbook Fashion Shop hoặc sửa Apache/VNC không thể chữa kết nối mà task lab chưa có cơ hội chạy. Không đổi management sang password, không sửa private key, không giảm kiểm tra host key, không đổi image/flavor hay xóa pool để thử ngẫu nhiên.

Người vận hành OpenStack/CyberRange kiểm tra đúng VM team4 của stack/pool đang lỗi, đối chiếu management IP 192.168.131.25. Có thể dùng giao diện OpenStack Instances → instance team4 tương ứng → Log/Console. Đọc console boot không cần gói SSH management tải từ pool. Console shell tương tác vẫn có thể yêu cầu thông tin đăng nhập guest; nếu không có, dùng console log và nhờ quản trị viên cloud, không yêu cầu mở mật khẩu Kali mặc định.

Lệnh **chỉ đọc** trên máy quản trị đã có OpenStack CLI và quyền project phù hợp:

```bash
openstack server list --long
openstack server show <TEAM4_INSTANCE_ID> -f yaml
openstack console log show --lines 100 <TEAM4_INSTANCE_ID>
openstack port list --server <TEAM4_INSTANCE_ID>
```

Các giá trị trong dấu <> phải thay bằng ID thật của đúng stack. Không chạy các lệnh này trên máy thí sinh chưa cấu hình OpenStack và không cần gửi credential vào chat. Nguồn CLI: [OpenStack Compute commands](https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/compute/v2/index.html).

Thứ tự kiểm tra:

1. **VM team4 boot/health:** đối chiếu ACTIVE/ERROR, fault của instance và console boot. Tìm kernel panic, OOM, disk đầy, lỗi cloud-init hoặc sshd. ACTIVE chỉ là trạng thái instance, chưa chứng minh SSH hoạt động. Nếu có lỗi tài nguyên/boot, xử lý theo bằng chứng phía cloud.
2. **Đường management:** đối chiếu port/IP của team4 với inventory worker; so sánh network, port binding và security group với team1 đang kết nối được. Kiểm tra đường proxy-jump → MAN → management IP theo config thực tế của pool, không dùng 10.90.0.14 là IP mạng bài tập để thay thế tùy tiện.
3. **Trong guest nếu quản trị viên đã có console shell:** `systemctl status ssh --no-pager`, `ss -ltnp '( sport = :22 )'`, `/usr/sbin/sshd -t`, `journalctl -u ssh -n 100 --no-pager`, `cloud-init status --long`. Dựa vào log thực tế để xử lý service/network; không tự suy đoán lỗi password của thí sinh.
4. **Trong worker/hạ tầng bởi người quản trị:** xem SSH verbose với đúng inventory/SSH config và credential nội bộ do nền tảng cấp để tách hop nào đóng kết nối. Không yêu cầu người dùng tải key từ pool chưa tạo xong.
5. Khi management SSH của team4 hoạt động, dùng thao tác retry/resume bước allocation/provisioning hạ tầng mà phiên bản portal hỗ trợ. Nếu portal không có retry phù hợp, quản trị viên chọn cách phục hồi; không tự xóa/recreate pool đang lỗi để che mất bằng chứng.

Sau phục hồi, cần thấy team4 unreachable=0 trong recap hạ tầng, rồi mới kiểm tra log playbook Fashion Shop và nghiệm thu Apache/VNC. Chưa kết luận lỗi desktop ở mục 11 đã khỏi chỉ từ log hạ tầng này.

### Trạng thái thực hiện

Đã phân tích log và cập nhật tài liệu; không có quyền truy cập cloud/console của pool mới trong phiên này nên chưa khôi phục management SSH team4. Không thay source lab hoặc xuất một bản ZIP giả định có thể sửa lỗi hạ tầng. Không chạy lại 60 test ứng dụng vì không đổi code và các test đó không xác minh đường SSH management này.

Tự đánh giá: accuracy 4/5 (xác định đúng tầng lỗi, chưa xác định hop đóng kết nối), completeness 3/5 (chưa phục hồi cloud vì không có access), clarity 4/5 (phân biệt giai đoạn dựng pool và deploy lab), actionability 4/5 (có vị trí kiểm tra và lệnh chỉ đọc), conciseness 4/5 (giữ đủ bước cho người quản trị). Trung bình 3.8/5. Bước cần tiếp theo là console boot/team4 hoặc log SSH của worker, không phải key tải từ pool.

## 13. Sửa trong labs, giữ nguyên Kali

Theo yêu cầu tiếp theo của người dùng: chỉ sửa file dự án trong labs và **giữ Kali**, không tạo bản Debian thay thế. Ý tưởng profile Debian nhẹ đã được dừng trước khi thực hiện; không có thay đổi image hoặc flavor.

- `labs/fashion_shop/sandbox/topology.yml`: đổi group từ fashion-shops sang **fashionshops**. Tên chỉ có chữ này hợp regex CyberRangeCZ và tránh dấu gạch ngang khiến Ansible báo Invalid characters were found in group names. Dấu gạch dưới cũng không dùng vì đã bị schema CyberRangeCZ từ chối ở mục 2.
- `sandbox/provisioning/playbook.yml`: giữ target team1:team2:team3:team4 trực tiếp, cập nhật comment; không phụ thuộc group cũ hoặc mới.
- `tests/test_cyberrange.py`: thêm test tên group tương thích cả hai bên, đồng thời khóa hợp đồng bốn VM đều image kali, mgmt_user debian, flavor standard.kali.
- Không đổi IP, router, CIDR, mật khẩu, Apache, VNC hoặc tick. Không thêm user_data/extra giả định có thể sửa SSH trước stage-one; schema topology không cung cấp cơ chế đó trong các trường đã xác minh.

TDD trước sửa: test_cyberrange.py **1 FAIL, 5 PASS** vì group fashion-shops có dấu gạch ngang. Sau sửa bộ test toàn lab **61 PASS**. Hai ZIP được tạo lại và topology bên trong được kiểm tra còn đủ bốn Kali, group fashionshops, không chứa dữ liệu runtime/bí mật.

**Giới hạn:** đây là sửa warning tên group, không phải bằng chứng sửa được kex_exchange_identification/UNREACHABLE của team4. Các thông số team4 tương ứng ba VM còn lại trong topology; log chưa chứng minh image, flavor hoặc IP lab là nguyên nhân. Không thay đổi chúng để giả vờ đã chữa lỗi. Việc custom provisioning chưa chạy trước lỗi stage-one được giữ đúng như phân tích mục 12. Không cần đổi gói chỉ để thử chữa SSH management; dùng gói mới khi muốn cập nhật sửa tên group này.

## 14. Tự sinh mật khẩu SSH/Kali và VNC, thêm lệnh xem thông tin

Người dùng xác nhận chỉ áp dụng SSH/Kali và VNC, không tạo tài khoản web tự động. Code trước đó đã có cơ chế sinh SSH/VNC khi không cấp override. Lần sửa này hoàn thiện helper chạy độc lập và cách người tổ chức xem credential đã sinh; không tuyên bố cơ chế tự sinh trước đây hoàn toàn thiếu.

File sửa trong `labs/fashion_shop`:

1. `sandbox/provisioning/files/generate-access.py`: helper tự tạo thư mục state với mode 0700 nếu chưa có, trước khi lưu credentials; không chmod thư mục cha có sẵn một cách tùy tiện. File credential tạo bằng mkstemp 0600 và publish qua hard link atomic, không ghi đè state của lần chạy khác. Sinh SSH 24 ký tự và VNC 8 ký tự bằng secrets; giữ password cũ khi chạy lại.
2. Thêm CLI `--state-file` (mặc định vẫn /var/lib/fashion-access/credentials.json) và `--show`. Show trả team, username, ssh_password, vnc_password; không in hash. Show state chưa tồn tại báo lỗi exit 2, không sinh password mới khiến người dùng nhầm là đã áp dụng. Kiểm tra team vẫn bắt buộc.
3. `sandbox/provisioning/generated-access.yml`: thông báo cuối hướng dẫn lệnh xem đúng team, không in password vào provisioning log. Giữ no_log ở task tạo password và set_fact; không bỏ override thủ công đã có chủ đích.
4. `tests/test_generated_access.py`: thêm test tự tạo parent directory, show không rehash/không đổi dữ liệu, show thiếu state không sinh mới, và output generation giữ contract JSON created/credentials mà Ansible đang dùng.
5. `HUONG-DAN-SSH.md`: thêm lệnh xem password, làm rõ đây là password riêng của lab và phân biệt desktop loopback 5901 với GUI native của image.

Sau cập nhật source và provisioning, người tổ chức chạy trên đúng VM bằng quyền quản trị:

```bash
sudo /usr/bin/python3 /usr/local/libexec/fashion-generate-access --team team1 --show
```

Đổi team1 theo VM tương ứng. Không đăng output có plaintext lên Git hoặc log công khai. User SSH vẫn là user-access, account kali mặc định vẫn khóa. Password tự sinh không thể biết từ source GitHub vì chỉ được tạo lúc chạy; tài khoản web vẫn đăng ký riêng.

Chạy helper ở chế độ tạo chỉ tạo/lưu dữ liệu credential; task user trong trainee-access.yml mới áp dụng hash cho tài khoản Linux. Do đó cần provisioning thành công trước khi coi password đã có hiệu lực. Nếu dùng override thủ công, credential tự sinh trong state không thay thế password override đang có hiệu lực.

TDD trước sửa: **4 FAIL, 5 PASS** trong test_generated_access.py vì thiếu parent directory và CLI. Sau sửa toàn bộ **65 test PASS**. Kiểm tra bổ sung trên Ubuntu WSL dùng OpenSSL thật: sinh bốn bộ credential khác nhau, SHA-512 crypt khớp password, chạy lại giữ dữ liệu và --show không có hash. Chỉ in kết quả PASS, không in password; dùng thư mục .qa-access-* tạm trong workspace và dọn sau chạy, không đổi user/password hệ thống. Các kiểm tra này không thay thế provisioning trên pool thật.

Coverage chạy lại cho ứng dụng và các helper Python: **95%** tổng (374 statements, 19 chưa phủ), generate-access.py **90%**, set-vnc-password.py **88%**, app.py/rounds.py **97%**. Lệnh coverage thực thi cùng 65 test, dùng thư mục tạm riêng .qa-coverage-passwords-20261104, không chỉ tái sử dụng số coverage cũ.

Không commit/push GitHub hoặc triển khai cloud trong lần sửa local này. Gói ZIP được tạo lại để người vận hành review/cập nhật source. Tự đánh giá: accuracy 4/5 (có kiểm tra hash thật, chưa deploy VM), completeness 4/5 (đúng phạm vi SSH/VNC, source/test/docs/gói hoàn tất), clarity 4/5 (phân biệt tạo state và áp dụng password), actionability 4/5 (có lệnh show, cần triển khai source mới), conciseness 4/5 (ghi đủ cách dùng và kết quả). Trung bình 4.0/5.

## 15. Đặt mật khẩu mặc định trong YAML theo yêu cầu mới

Mục này thay thế mặc định tự sinh mô tả ở các mục trước. Người dùng yêu cầu đặt trước password trong YAML; không tạo tài khoản web mặc định.

File chính: `labs/fashion_shop/sandbox/provisioning/group_vars/all.yml` (trong repo Sandbox là provisioning/group_vars/all.yml). Ansible nạp group_vars cạnh playbook. Cấu hình lab công khai:

| Team | Username SSH | Password SSH | Password VNC lab |
|---|---|---|---|
| team1 | user-access | MekoTeam1@2026 | Meko1Vnc |
| team2 | user-access | MekoTeam2@2026 | Meko2Vnc |
| team3 | user-access | MekoTeam3@2026 | Meko3Vnc |
| team4 | user-access | MekoTeam4@2026 | Meko4Vnc |

Các bước sửa:

1. Thêm mapping plaintext `fashion_trainee_passwords` và `fashion_trainee_vnc_passwords` vào group_vars/all.yml. Đây là default của bài lab theo yêu cầu, không dùng cho account quản trị hoặc dịch vụ thật.
2. Trong trainee-access.yml, chọn mode YAML khi có plaintext nhưng chưa có override hash/env. Kiểm tra đủ bốn team, password SSH khác nhau và 12–128 ký tự ASCII in được, không khoảng trắng. Băm bằng openssl passwd -6 -stdin trên VM; stdin bảo vệ password khỏi argv. Salt fashionteamNssh riêng từng team giúp hash không thay đổi ở mỗi lần provisioning. Hash tiếp tục đi qua validator và task user hiện có.
3. Đóng băng biến `fashion_yaml_ssh` trước block, để when không bị đổi sang false sau khi loop set_fact vừa cập nhật hash đầu tiên. Không dùng điều kiện trực tiếp dựa vào fashion_access_hashes đang bị thay đổi trong loop.
4. Không tự sinh SSH khi plaintext YAML đã khai báo. VNC dùng mapping YAML qua cơ chế manual hiện có. Hash override/biến môi trường SSH được cung cấp có chủ đích vẫn được ưu tiên; mapping VNC YAML ưu tiên hơn worker env như logic hiện có.
5. package_lab.py xuất thêm provisioning/group_vars vào cả hai ZIP, cập nhật README và hướng dẫn SSH/GUI. Không commit/push hay thay password VM trong phiên local này.

TDD trước sửa **2 FAIL** trong test_default_access.py (chưa có file YAML, mode tự sinh còn được chọn khi đã cấu hình plaintext). Bổ sung kiểm tra when bị re-evaluate: **1 FAIL, 1 PASS** trước khi đóng băng biến chọn mode. Sau sửa toàn bộ **67 test PASS**. Đã render argv/stdin từ YAML rồi chạy OpenSSL thật trong WSL, kiểm tra hash của đủ bốn password đúng và ổn định khi chạy lại; không thay tài khoản hệ thống. Chưa chạy provisioning trên pool thật.

Áp dụng: cập nhật source từ gói mới rồi chạy provisioning của lab. Sau thành công, SSH dùng user-access với password bảng trên. VNC lab dùng password VNC tương ứng qua SSH tunnel tới loopback 5901; không phải password VNC native của image. User kali vẫn khóa; bốn VM vẫn image kali/flavor standard.kali.

Khi mode YAML đang dùng, **credentials.json hoặc --show cũ có thể chứa password tự sinh trước đây và không còn là nguồn password có hiệu lực**. Dùng YAML/bảng trên. Muốn quay lại tự sinh, xóa mapping plaintext SSH/VNC trong group_vars và bỏ các override tương ứng, rồi reprovision. Không xóa mapping trong khi đang thi nếu không chủ đích đổi cơ chế truy cập.

Đánh giá lần sửa: accuracy 4/5 (hash thực đã kiểm tra, thiếu nghiệm thu Ansible/SSH trên VM), completeness 4/5 (YAML, áp dụng hash, VNC, test, gói và docs đầy đủ), clarity 4/5 (nêu ưu tiên và state cũ), actionability 4/5 (có bảng password và file sửa), conciseness 4/5 (đủ bước triển khai). Trung bình 4.0/5.

## 16. Log mới: bỏ điều kiện metapackage Kali không có trong apt cache

### Bằng chứng

File log trước dài 2469 dòng, gồm hai đoạn chạy bị cắt ở phần assert peer, chưa có FAILED/PLAY RECAP. Không kết luận lần chạy thành công chỉ từ phần bị cắt đó. File tiếp theo dài 2858 dòng đã cho thấy lỗi:

```text
apt-cache show kali-desktop-xfce
rc: 100
stderr: E: No packages found
TASK [Explain an incompatible desktop image]
assertion: fashion_kali_package.rc == 0
FAILED
```

Các bước hash mật khẩu YAML, tạo user-access và kiểm tra policy SSH đã chạy qua trước đó. Apache configtest Syntax OK; health local HTTP 200 trên cả bốn team. Phần VNC chưa được cấu hình xong trong lần chạy lỗi này, nên chưa khẳng định password VNC YAML đã có hiệu lực trên desktop.

### Sửa đúng chỗ trong labs

1. `labs/fashion_shop/sandbox/provisioning/desktop.yml`: bỏ hai task Detect Kali package source / Explain an incompatible desktop image. Điều kiện này đã coi thiếu một metapackage là image không tương thích, trong khi desktop chỉ cần các package XFCE runtime. Không dùng ignore_errors để che lỗi.
2. Trong apt task, thay kali-desktop-xfce bằng **xfce4 và xfce4-terminal**; giữ TigerVNC, D-Bus, xauth, fonts, Firefox và acl. apt vẫn update_cache và phải thành công. Không sửa apt sources hoặc trộn repository, không đổi topology/image sang Debian.
3. `sandbox/provisioning/playbook.yml`: giảm output kiểm tra peer. URI loop có label tên team; assert chỉ loop qua tên team và tra response trong registered results, dùng quiet=true. Không truyền cả response/invocation lồng nhau vào item của assert. Vẫn kiểm tra status=200 và JSON team đúng, không bỏ kiểm tra chéo đội. Mục đích là giúp log không bị ngập trước task desktop và thông báo lỗi thật.
4. `tests/test_desktop.py`: thêm test không còn apt-cache gate cho kali-desktop-xfce, cài đủ runtime XFCE/VNC. `tests/test_cyberrange.py`: hai trường hợp peer đúng/sai, vừa bảo đảm loop gọn vừa giữ khả năng phát hiện trả nhầm team. Cập nhật HUONG-DAN-KALI-GUI.md.

Giữ nguyên bốn VM **image kali, mgmt_user debian, flavor standard.kali**, Apache :80, backend loopback :8080, VNC lab loopback :5901, các password mặc định tại group_vars/all.yml và account kali bị khóa.

Nguồn đối chiếu: [Kali metapackages](https://www.kali.org/tools/kali-meta/), [XFCE core metapackage](https://packages.debian.org/bookworm/xfce4). Package xfce4 kéo các thành phần session, panel, window manager và settings cần thiết; không cần metapackage branding Kali để gọi startxfce4.

### Kiểm chứng và áp dụng

- RED log gọn: 2 FAIL, 6 PASS trước khi đổi loop assert.
- RED desktop: 1 FAIL, 18 PASS trước khi thay metapackage.
- GREEN cuối: **70 test PASS** toàn lab (`py -m pytest labs/fashion_shop/tests -q`).
- Hai gói ZIP được tạo lại và kiểm tra source bên trong không còn apt-cache gate, có xfce4/xfce4-terminal, còn đủ bốn VM Kali và mật khẩu YAML.

Cập nhật repo/branch IDOR đang dùng bằng source mới, chạy lại provisioning lab. Trong log mới sẽ không có task Explain an incompatible desktop image; thay vào đó apt cài XFCE rồi tiếp tục hostname/VNC. Cần PLAY RECAP failed=0/unreachable=0 và kiểm tra listener/session trước khi kết luận desktop cloud đã hoạt động. Chưa chạy lại pool thật trong phiên sửa local này.

Tự đánh giá: accuracy 4/5 (lỗi cụ thể đã có trong log; chưa nghiệm thu apt/desktop trên image cloud), completeness 4/5 (sửa source, kiểm thử, docs, gói nộp), clarity 4/5 (phân biệt thiếu metapackage với đổi distro), actionability 4/5 (source mới có thể reprovision), conciseness 4/5 (ghi đủ bằng chứng và cách áp dụng). Trung bình 4.0/5.

## 17. Menu sandbox mất Open GUI: GUI Access của image đang tắt

Ảnh người dùng gửi cho thấy menu team4 chỉ có Open Console / Open Console in new Window. Người dùng đã kiểm tra và xác nhận **GUI Access của image kali đang tắt** trong Sandbox Agenda → Images. Đây là điều kiện đã xác minh làm nút GUI không xuất hiện, khác với lỗi VNC service không chạy hoặc password sai sau khi mở kết nối.

Theo [CyberRangeCZ Images](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/images/), cột Gui Access là thuộc tính của image. [Sandbox Access](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/) yêu cầu image được đánh dấu GUI bên cạnh dịch vụ VNC/RDP thực. Cài xfce4 trong guest không tự đổi thuộc tính OpenStack và không tự hiện nút GUI.

### Khôi phục thuộc tính image

Trên máy quản trị có OpenStack CLI đã cấu hình quyền sửa đúng image, đọc trước:

```bash
openstack image show kali -f yaml
```

Đối chiếu ID image với image thực sự được VM sandbox sử dụng. Nếu có nhiều image cùng tên, dùng đúng ID để tránh sửa nhầm. Metadata chuẩn trong tài liệu xây dựng image KYPO là **owner_specified.openstack.gui_access**:

```bash
openstack image set --property owner_specified.openstack.gui_access=true <KALI_IMAGE_ID>
openstack image show <KALI_IMAGE_ID> -f yaml
```

Nguồn khóa metadata: [MUNI-KYPO image upload guide](https://gitlab.ics.muni.cz/muni-kypo-images/muni-kypo-images-wiki/-/wikis/How-to-upload-an-image-to-OpenStack/diff?version_id=ebc1606a311acac3f2031f6c55afb651724c19b0). Trang Sandbox Access có viết gui_acess thiếu chữ c; phải đối chiếu backend phiên bản triển khai nếu cột GUI Access không đổi, không tự coi hai tên là tương đương hay đặt thêm trường không được schema topology hỗ trợ.

Đây là lệnh sửa metadata cloud để người quản trị thực hiện; **chưa chạy trong phiên local này**. Không cần SSH key của pool để sửa image bằng OpenStack API/CLI, nhưng cần quyền quản trị image và cấu hình xác thực OpenStack phù hợp trên máy chạy lệnh. Không đặt credential OpenStack lên VM thí sinh hoặc commit vào repo lab.

Sau thay đổi, refresh trang Images và kiểm tra GUI Access chuyển true. Refresh topology sandbox và kiểm tra menu Open GUI. Nếu nền tảng lưu thông tin image/topology cũ, cần người quản trị kiểm tra cơ chế đồng bộ/cache của phiên bản đó; không tự xóa pool để thử hoặc hứa rằng sửa metadata luôn cập nhật tức thời mọi pool hiện có.

### Hiện nút GUI và mở được desktop là hai bước

Source lab hiện giữ VNC native image ở cổng 5900, chạy desktop lab riêng tại **127.0.0.1:5901** qua SSH tunnel. Vì vậy bật GUI Access làm điều kiện hiển thị menu được đáp ứng, nhưng không tự chuyển Guacamole sang 5901 hoặc làm nó truy cập được listener loopback trên guest.

- Password Meko1Vnc–Meko4Vnc trong group_vars/all.yml chỉ được áp dụng cho fashion-desktop riêng.
- Không khẳng định đó là password listener native 5900 mà portal có thể đang dùng.
- Nếu muốn Open GUI trực tiếp vào desktop riêng của lab, cần tích hợp đường Guacamole/tunnel/port tới đúng service và nghiệm thu riêng. Không đổi bừa service sang 5900 vì log trước đã chứng minh cổng này đang có listener khác.

Không sửa topology.yml, không đổi bốn image Kali và không sửa service chỉ để giả vờ bật được metadata cloud từ file guest. Đã cập nhật tài liệu theo bằng chứng GUI Access=false; việc bật metadata trên server và nghiệm thu kết nối vẫn cần người vận hành thực hiện.

## 18. Sửa luồng đăng nhập Console/GUI trong thư mục labs

Người dùng báo cả password SSH/VNC trong bảng đều không vào được Console/GUI, sau đó yêu cầu sửa code trong thư mục dự án.

### Vì sao bảng password trước chưa đủ

- Password SSH trong YAML được áp dụng cho **user-access**, không phải kali. Account kali bị khóa, hết hạn và shell nologin theo yêu cầu trước. Nếu nhập username kali thì các password SSH trong bảng không được kiểm tra với user-access. Không có bằng chứng về username hoặc journal của lần nhập thất bại nên chưa kết luận mọi lỗi SSH chỉ do nhập sai user.
- Cấu hình GUI trước đây của agent bị lệch với đường truy cập portal: password MekoNVnc được ghi cho fashion-desktop ở **127.0.0.1:5901**, còn listener native 5900 không nhận password đó. Guacamole không thể đi thẳng từ máy khác vào loopback guest; nếu dùng 5900 cũng có thể tới service cũ. Không nên coi bảng password đã dùng được cho Open GUI khi chưa nối đúng service.
- GUI Access của image được người dùng xác nhận đang tắt. Đây vẫn là điều kiện metadata cloud độc lập với file lab; phần source mới không tự bật image metadata.

### File và hành vi đã sửa

1. `sandbox/provisioning/group_vars/all.yml`: đặt endpoint GUI mặc định port **5900**, display 9, localhost=false; giữ nguyên password SSH/VNC từng team. Danh sách unit được phép thay là lightdm.service và x11vnc.service.
2. `files/fashion-desktop.service`: nghe VNC trên interface mạng để portal có thể kết nối, yêu cầu VncAuth, dùng đúng /home/user-access/.vnc/passwd từ YAML; XFCE chạy trực tiếp dưới user-access. Không có bước đăng nhập lại user kali vào greeter của phiên riêng này.
3. Thêm `files/vnc-listener.py`: helper **chỉ đọc** ss và /proc/PID/cgroup, trả danh sách systemd unit thật đang sở hữu socket. Không tự stop/kill. Unknown PID/unit hoặc owner thuộc SSH/Apache/network bị đánh dấu không được thay. Fashion-desktop hiện có được nhận diện riêng, không coi là service native cần dừng.
4. `desktop.yml`: kiểm tra mọi owner trước khi thay. Chỉ stop/disable unit GUI đã xác minh và được cho phép; không dừng LightDM chỉ vì tên đó có trong image. Block migration/start/check có rescue đọc journal và thử khôi phục các service native đã xác minh nếu migration lỗi; khôi phục enabled=true cho unit trước đó enabled. Restore task có thể lỗi và phải được xem trong log; toàn bộ provisioning vẫn fail theo lỗi ban đầu, không báo PASS giả.
5. Kiểm tra VNC local, xfce4-session và banner RFB từ gateway tới IP mạng lab. Kiểm tra gateway chứng minh service không chỉ bind loopback; không thay thế nghiệm thu đường Guacamole thực hoặc xác thực VNC từ trình duyệt.
6. Thêm `provisioning/verify-access.yml`: sau áp dụng password và reload SSH, chạy đăng nhập thử thật qua sshd/PAM bằng user-access. Dùng sshpass -e, password qua environment SSHPASS/no_log, host key pin từ public key cục bộ, StrictHostKeyChecking=yes; file known_hosts tạm được xóa trong always. Khi lỗi, đọc journal SSH và fail rõ ràng. Cài openssh-client/sshpass trong trainee runtime.
7. Probe SSH chỉ chạy khi biết plaintext từ YAML hoặc state tự sinh. Không thể xác minh password plaintext của override chỉ cấp hash; mode đó bỏ probe. Probe là loopback, không chứng minh mọi Match Address/routing trên đường Guacamole đã đúng.
8. Ghi rõ username user-access trong shop-addresses.txt, cập nhật README/HUONG-DAN-SSH.md và viết lại HUONG-DAN-KALI-GUI.md cho luồng portal 5900. package_lab.py thêm verify-access.yml; helper VNC tự được xuất qua allowlist files.

Việc stop/disable LightDM khi được xác minh sở hữu VNC sẽ thay cả phiên GUI native/greeter liên quan trên VM lab bằng fashion-desktop. Đây là thay đổi có chủ đích để portal tới service có password YAML; không tuyên bố giữ nguyên greeter native như bản cũ. Nếu owner socket khác danh sách, task fail trước khi dừng dịch vụ; cần đọc owner để cấu hình phù hợp, không thêm tùy tiện SSH/network vào danh sách.

### Cách đăng nhập sau khi triển khai thành công

Team1: Open Console username **user-access**, password **MekoTeam1@2026**. Open GUI dùng VNC password **Meko1Vnc** khi image GUI Access đã bật và Guacamole trỏ đúng port 5900. Team2–team4 theo bảng YAML tương ứng. Kali là tên image/hệ điều hành, account kali vẫn khóa. Không dùng VNC password làm password SSH hoặc ngược lại. Nếu không có nút Open GUI, xử lý metadata như mục 17; nếu có nút nhưng không kết nối, cần kiểm tra đường Guacamole tới VM và service/password.

### Kiểm chứng

- RED trước helper/endpoint: 6 FAIL, 18 PASS (thiếu helper và unit còn loopback 5901).
- RED trước SSH probe: 1 FAIL, 17 PASS (chưa có verify-access.yml).
- RED trước rollback: 1 FAIL, 19 PASS (chưa có khôi phục native GUI).
- GREEN: **80 test PASS** toàn lab. Test mới có owner free/LightDM/self/unknown/protected, CLI chỉ inspection và input không hợp lệ, template VNC port/bind, đường probe gateway, live SSH probe không đưa password vào argv và cleanup/rollback.
- Coverage ứng dụng và helper Python **95%** (417 statements, 21 chưa phủ); vnc-listener.py 95%. Sau bổ sung ControlMaster=no/ControlPath=none/BatchMode=no để SSH probe không tái sử dụng phiên đăng nhập có sẵn, đã chạy lại 46 test liên quan và đều PASS.
- Đã gọi helper qua ss/proc thật trong Ubuntu WSL để kiểm tra inspection (port 5900 trống); không dừng service hoặc thay password hệ thống. Chưa tái hiện listener native Kali hay chạy Ansible trên pool thật.

Các task live SSH/gateway probe được thêm vào source để chạy **khi reprovision**, không phải bằng chứng đã đăng nhập thành công lên VM người dùng trong phiên này. Source và hai ZIP đã cập nhật local, chưa push/triển khai cloud. Bước cần nghiệm thu là PLAY RECAP failed=0/unreachable=0, probe SSH pass, probe VNC gateway pass, rồi thử Open Console/GUI thật.

Tự đánh giá: accuracy 4/5 (chỉ ra đúng lệch username/endpoint, chưa có auth log từ pool), completeness 4/5 (source/test/docs/gói và rollback, cloud chưa nghiệm thu), clarity 4/5 (phân biệt account kali, user-access, VNC password và metadata), actionability 4/5 (có source chạy probe thực khi deploy), conciseness 4/5 (ghi đủ hành vi thay listener). Trung bình 4.0/5.

## 19. PID 1 giữ cổng VNC: hỗ trợ systemd socket activation

Log mới từ branch IDOR có lỗi trên cả bốn team:

```text
VNC port owner requires review: ['Unapproved listener PID 1: ']. No service has been stopped.
```

Đây là thiếu hỗ trợ trong helper do agent viết: PID 1 là systemd, không phải process VNC có service cgroup thông thường. Code cũ chỉ đọc cgroup nên không ánh xạ socket do manager giữ sang unit .socket. Không được chữa bằng cách dừng/kill PID 1 hoặc bỏ qua việc xác minh owner.

**Log này đồng thời xác nhận `Verify password login through the running SSH daemon` đã PASS cho team1–team4.** Như vậy password YAML/user-access đã qua SSH/PAM loopback thật trong lần chạy đó. Điều này không chứng minh đường Guacamole ngoài VM hoặc desktop đã hoạt động; lỗi lần này ở migration VNC, không phải bước băm password.

### File sửa

1. `labs/fashion_shop/sandbox/provisioning/files/vnc-listener.py`: khi ss thấy PID 1 giữ cổng, liệt kê unit socket active bằng systemctl list-units, rồi đọc **Id/ActiveState/Listen/Triggers bằng systemctl show**. Không parse cột địa chỉ của list-sockets vì tài liệu systemd nói định dạng đó không ổn định cho máy đọc.
2. Chỉ ánh xạ unit active có Listen kiểu Stream và endpoint TCP đúng cổng mục tiêu. Kiểm tra địa chỉ IPv4/IPv6/wildcard hoặc port số; đường dẫn UNIX như /run/vnc:5900 không được coi là TCP 5900. Unit phải thuộc danh sách cho phép; socket/target thuộc SSH, Apache, network hoặc template/instance SSH bị bảo vệ.
3. Stop plan sắp socket trước service thực được Triggers chỉ ra, để không bị socket kích hoạt lại service giữa migration. Template @.service chưa instantiate không được đưa vào lệnh stop như một service có thể chạy. Unknown owner làm toàn bộ stop plan rỗng, không chuyển một phần.
4. `provisioning/group_vars/all.yml` và fallback trong desktop.yml: danh sách GUI owner mặc định gồm xvnc.socket, vncserver.socket, tigervnc.socket, x11vnc.socket, lightdm.service, x11vnc.service. Không wildcard toàn bộ socket. Nếu image có tên socket khác, log mới nêu tên unit để review; không tự nhận mọi socket cùng cổng là VNC.
5. Giữ block stop/start/rollback hiện có trong desktop.yml; module systemd xử lý tên unit .socket cũng như .service. Helper vẫn chỉ inspection, không tự dừng dịch vụ.
6. `tests/test_vnc_listener.py`: tái hiện PID 1, socket đúng cổng, từ chối sai cổng/UNIX/protected/unapproved, thứ tự stop và cách đọc thuộc tính. Cập nhật hướng dẫn GUI.

Nguồn: [systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html) — show dành cho machine-readable properties; list-sockets không thích hợp để parse tự động cột địa chỉ.

### Kiểm thử

- RED trước sửa: **8 FAIL, 8 PASS** trong test_vnc_listener.py.
- GREEN cuối: **89 test PASS** toàn lab.
- Coverage ứng dụng và helper Python: **95%** (473 statements, 26 chưa phủ), riêng vnc-listener.py **93%**. Đây là lượt coverage mới chạy cùng 89 test, không tái dùng số của bản trước.
- Kiểm tra read-only với systemd thật trong Ubuntu WSL xác nhận Listen của socket được serialize như `/run/dbus/system_bus_socket (Stream)` và parser không coi đây là TCP.
- Tạo socket test có tên ngẫu nhiên fashion-vnc-probe-*.socket, chỉ bind **127.0.0.1:5998**, Accept=yes với template test riêng trong WSL. Chạy helper CLI thật: tìm đúng socket cho phép, unknown rỗng, không thực hiện stop. Dọn socket và runtime links sau test, kiểm tra cổng trống lại. Không sửa/dừng SSH hoặc VNC cloud.
- Lần thử tạo unit đầu không đủ quyền Linux; chưa tạo được unit. Đã kiểm tra/dọn đúng tên test nếu có, chạy lại bằng root WSL và test PASS. Không sử dụng kết quả lần thiếu quyền để tuyên bố thành công.

Gói source được tạo lại. Cập nhật branch IDOR bằng source mới rồi reprovision; xem helper trả stop_units có tên .socket cụ thể, migration qua được port check và RFB/XFCE/gateway probe PASS. Chưa chạy hoặc xác nhận Open GUI trên pool người dùng trong phiên local này. Password, user-access, image Kali và các cổng giữ nguyên như mục 18; GUI Access metadata vẫn là điều kiện độc lập.

Tự đánh giá: accuracy 4/5 (đã tái hiện PID 1 bằng systemd thật, chưa có metadata socket từ pool), completeness 4/5 (helper, cấu hình, test, hướng dẫn và gói đầy đủ, chờ reprovision), clarity 4/5 (nêu rõ không dừng manager), actionability 4/5 (source nhận diện unit cụ thể), conciseness 4/5 (ghi đủ cách xác minh). Trung bình 4.0/5.

## 20. Console dùng được nhưng GUI chờ server: thêm desktop qua Apache và kiểm tra VNC thật

Ảnh portal hiển thị `Waiting for server…` chưa xác định được nguyên nhân cụ thể. Console thành công không chứng minh Guacamole đã kết nối được VNC. Phiên này sửa source local, không có quyền truy cập server CyberRange để thay cấu hình Guacamole hoặc nghiệm thu pool. Không thay tiếp password theo phỏng đoán.

### Các bước sửa và file tương ứng

1. Thêm `labs/fashion_shop/tests/test_vnc_probe.py` và `tests/test_novnc.py` trước code. Kiểm tra mới cần xác thực VncAuth, nhận pixel thật, từ chối password sai/packet thiếu/packet quá lớn, và có route desktop riêng trong Apache. RED ban đầu: **20 test fail** vì helper, service và route chưa có. Vector DES được tính lại bằng công cụ riêng trước khi hoàn thiện test.
2. Thêm `sandbox/provisioning/files/check-vnc.py`. Helper đọc password qua stdin, thương lượng RFB 3.7/3.8, yêu cầu VncAuth, thực hiện DES challenge-response, đọc ServerInit và yêu cầu một pixel raw. Không chấp nhận chỉ banner RFB. Có giới hạn kích thước packet, số message và thời gian đọc. JSON thành công chỉ chứa authenticated, width, height, frame_received; lỗi không in password.
3. `sandbox/provisioning/desktop.yml`: cài `python3-pycryptodome`, copy helper thành `/usr/local/libexec/fashion-check-vnc`, thêm task **Authenticate VNC and receive a desktop frame** dùng password đang áp dụng cho chính VM. Stdin/no_log, tối đa ba lần thử; lỗi vẫn làm provisioning fail và rescue hiển thị lý do helper cùng journal desktop. Tiếp tục kiểm tra XFCE và đường mạng gateway như trước.
4. Cài gói `novnc` và `websockify` qua apt. Thêm `files/fashion-novnc.service`: user-access chạy bridge **127.0.0.1:6080 → 127.0.0.1:cổng VNC đã cấu hình**; không bind public 6080, không lưu password vào unit. Service phụ thuộc fashion-desktop. VNC phía sau vẫn bắt buộc password.
5. Thêm `files/fashion-novnc.html`, copy vào `/usr/share/novnc/fashion.html`. Trang chỉ chuyển sang vnc.html với hostname/port/protocol của địa chỉ đang mở, path WebSocket cố định. Host được đặt rõ để tương thích cách giải path của noVNC 1.3 và các bản mới. Không nhúng password trong HTML hoặc URL.
6. `provisioning/apache.yml`: bật thêm proxy_wstunnel, alias, dir. Trong `files/fashion-shop-apache.conf`, đặt ProxyPass `/desktop/websockify` tới bridge trước exclusion `/desktop/`, rồi mới catch-all `/` tới backend shop. Alias desktop trỏ assets noVNC, DirectoryIndex fashion.html, tắt directory listing. Web shop tiếp tục chạy qua Apache như cũ.
7. `desktop.yml`: template/start fashion-novnc, chờ loopback 6080, kiểm tra `/desktop/vnc.html` HTTP 200 qua Apache và in URL desktop không có credentials. Thêm dependency pycryptodome cho test trong requirements-dev.txt. Package script hiện đã xuất toàn bộ `provisioning/files`, nên các file mới có trong cả hai ZIP.
8. Cập nhật README và HUONG-DAN-KALI-GUI.md: URL mỗi đội, password đúng loại, yêu cầu VPN/route, lệnh tunnel HTTP và vị trí journal. Giữ bốn image Kali, account kali khóa, username user-access và các default password YAML đã được người dùng yêu cầu.

### Dùng bản sửa trên pool

1. Lấy **nội dung** `labs/fashion_shop/sandbox/` hoặc giải nén `meko-fashion-sandbox.zip` vào repository Sandbox Definition đang dùng. Gốc repo phải có topology.yml, provisioning/, app/. Không chỉ copy vào thư mục không được pool tham chiếu.
2. Cập nhật branch/revision mà pool sử dụng, rồi chạy lại provisioning theo quy trình của hệ thống. Nếu tạo pool mới, chọn đúng revision mới. Sửa local hoặc reload trình duyệt không cập nhật VM cũ. Phiên này chưa push GitHub và chưa chạy provisioning cloud.
3. Kiểm tra PLAY RECAP failed=0/unreachable=0; task SSH probe, VNC authentication/frame, gateway VNC và Apache browser page đều phải PASS.
4. Qua VPN/đường truy cập sandbox, mở `http://10.90.0.13/desktop/` cho team3, nhập **Meko3Vnc** nếu không override YAML. Team1 dùng .11/Meko1Vnc; team2 .12/Meko2Vnc; team4 .14/Meko4Vnc. Trang noVNC không dùng password SSH và không yêu cầu username user-access.
5. Có thể tiếp tục thử Open GUI trên portal nếu metadata và đường Guacamole đã đúng. Đường `/desktop/` độc lập với Guacamole; không tự bật GUI Access hoặc chữa routing bên server. Nếu chỉ portal lỗi nhưng `/desktop/` dùng được, đã khoanh vùng thêm được đường portal, chưa xác định chính xác cấu hình server nào sai.

Nếu máy người dùng không tới được IP sandbox thì URL này cũng không tự truy cập được. Dùng VPN/route được tổ chức cung cấp. Với SSH được phép, ví dụ `ssh -L 18080:127.0.0.1:80 user-access@10.90.0.13`, rồi mở `http://127.0.0.1:18080/desktop/`. Log quản trị: `journalctl -u fashion-desktop -u fashion-novnc`, `/var/log/apache2/fashion-shop-error.log`. Tài khoản thí sinh không được cấp thêm sudo.

### Bằng chứng kiểm thử

| Phạm vi | Kết quả thực tế | Giới hạn |
|---|---|---|
| RED trước triển khai | 20 FAIL ở hai file test mới | Chưa có các helper/route mới |
| Toàn bộ pytest + coverage | **117 PASS**, **95%**: 572 statements, 28 chưa phủ; helper check-vnc **98%** | Chạy local, không phải Ansible trên Kali cloud |
| TigerVNC 1.13.1 thật trong Ubuntu WSL | Password đúng qua auth và nhận pixel raw; password sai bị từ chối | Virtual X server thử riêng, không chạy phiên XFCE trên pool |
| Apache 2.4.58 với virtual host từ source | Syntax OK; shop stub `/`, launcher, vnc.html, core/rfb.js đều HTTP 200 | Đổi cổng và đường assets chỉ trong harness test |
| Chrome headless → Apache → websockify 0.10 → TigerVNC | Launcher hỏi password; sai bị từ chối; đúng connected; framebuffer 800×600 được khởi tạo; WebSocket **HTTP 101** tại đúng `/desktop/websockify` | Không phải Guacamole, không phải ảnh desktop XFCE của người dùng |
| Cleanup | Các cổng test 5997/16080/18986/18987 đã đóng; symlink xkbcomp tạm đã xóa | Không dừng/sửa dịch vụ cloud |

Lệnh pytest/coverage đã chạy (PowerShell, dùng coverage trong thư mục .qa-tools sẵn có):

```powershell
$env:PYTHONPATH = "$PWD/labs/fashion_shop/.qa-tools"
$env:COVERAGE_FILE = "$PWD/labs/fashion_shop/report/.coverage-browser-vnc"
py -m coverage run --source=labs/fashion_shop/sandbox/app,labs/fashion_shop/sandbox/provisioning/files -m pytest labs/fashion_shop/tests -q -p no:cacheprovider --basetemp=labs/fashion_shop/.qa-coverage-browser-vnc
py -m coverage report -m
```

Browser test nằm ở `tests/browser_vnc_qa.mjs`, chỉ cho phép target localhost/127.0.0.1 và yêu cầu QA_VNC_PASSWORD qua environment. Runtime test giải nén gói Ubuntu vào .qa-gui-runtime, không cài package toàn hệ thống. Xvnc cần xkbcomp ở đường hệ thống cố định, nên harness tạo symlink tạm khi chưa tồn tại và chỉ xóa đúng link đó trong finally. Không thay file xkbcomp có sẵn. Các lần đầu thiếu thư viện/font/xkbcomp đã fail; không tính là PASS. Lượt browser đầu ở cổng 18086 nhận trang Flask khác của Windows; đổi sang 18986 rồi mới chạy đúng stack và PASS. Ảnh report/images/09-vnc-browser.png là X server trống của test, không phải bằng chứng GUI cloud đã được phục hồi. Chưa chạy Ansible hoặc Guacamole end-to-end trên pool.

Nguồn thiết kế: [noVNC embedding](https://github.com/novnc/noVNC/blob/master/docs/EMBEDDING.md), [Apache mod_proxy](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html), [RFB RFC 6143](https://www.rfc-editor.org/rfc/rfc6143.html), [Debian pycryptodome file list](https://packages.debian.org/bookworm/amd64/python3-pycryptodome/filelist). Debian dùng namespace Cryptodome; helper có fallback Crypto cho môi trường test Windows.

Tự đánh giá theo agent-self-evaluation: accuracy **4/5** (đã auth VNC và nâng cấp WebSocket thật, chưa xác nhận Guacamole cloud); completeness **3/5** (source/test/docs/gói hoàn tất, lỗi portal thật còn cần nghiệm thu trên server); clarity **4/5** (URL và loại password rõ, tài liệu có lịch sử dài); actionability **4/5** (có gói và từng bước áp dụng, cần người vận hành cập nhật revision/reprovision); conciseness **4/5** (bàn giao ngắn, bằng chứng chi tiết nằm ở docs). Trung bình **3.8/5**. Cải thiện ưu tiên là chạy source mới trên pool và thử cả `/desktop/` lẫn Open GUI; chỉ sau đó mới kết luận phục hồi GUI cloud. Người dùng có thể đồng ý với đánh giá này vì bản sửa local đã có bằng chứng nhưng không được coi là server đã tự cập nhật.
