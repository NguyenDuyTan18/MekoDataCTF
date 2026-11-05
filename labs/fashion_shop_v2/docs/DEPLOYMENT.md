# Cấu hình và triển khai · Meko Boutique V2

## Tách biệt và dữ liệu

`sandbox/app/data/seed.json` là dữ liệu khởi tạo bất biến. Mỗi máy tạo SQLite, state, patch và dữ liệu thiết kế trong `/var/lib/meko-boutique`; không chép runtime vào source/ZIP. Mỗi host có `TEAM_ID` riêng và từ chối khởi động nếu thư mục dữ liệu mang ID đội khác.

## Local dev

Từ `labs/fashion_shop_v2` cài `requirements.txt`, đặt `TEAM_ID=team1`, `MEKO_DATA=.runtime/team1`, chạy `python sandbox/app/app.py`. Tick cấu hình bằng `MEKO_TICK_SECONDS`. Staff route `/staff/login` yêu cầu `MEKO_STAFF_PASSWORD`; để trống thì đăng nhập staff bị tắt. Không đặt mật khẩu nhân viên trong giao diện khách mua.

Kiểm thử: `py -m pytest tests -q`. Checker endpoint trong test có khóa tạm. Test không dùng dịch vụ bên ngoài/pool.

## Sandbox Definition

Gốc source triển khai là `sandbox/`, có topology.yml cùng `provisioning/`, `app/`, `checker/`. Topology có 4 máy Kali `team1`–`team4`, gateway Debian, group `meko-teams`, network `meko-v2-lan` và WAN riêng. Trước khi import, rà soát trùng CIDR với management/tenant networks.

Image/flavor trong YAML chỉ theo quy ước đang dùng trong lab tham chiếu: `kali`, `debian-12-x86_64`, `standard.kali`, `standard.small`, management user `debian`. Chúng **không được bảo đảm tồn tại**. Quản trị viên phải xác minh tên image, user management, GUI Access, flavor, quota CPU/RAM/disk, khả năng package repo, routing và firewall trên cloud đích. Apache nhận HTTP cổng 80, Waitress chỉ bind loopback 8080. Router không thay cho security group/network policy.

Playbook cài Apache/Python từ repo Kali, cấu hình reverse proxy, health check và tài khoản đội `team1`–`team4`. Tài khoản `kali` bị khóa nếu tồn tại; management user/key CyberRange không bị sửa. Các tài khoản đội không có sudo. Mạng người chơi được mở HTTP tới các host theo chính sách CyberRange.

## Mật khẩu Kali/SSH

Mặc định, playbook sinh mật khẩu ngẫu nhiên riêng từng đội và lưu root-only trong `/etc/meko-boutique/credentials.json`, ổn định khi reprovision cùng VM. Giảng viên lấy credential qua SSH quản trị và cấp riêng. Không commit credential vào `group_vars/all.yml` hoặc gói ZIP. Có thể đặt mapping riêng qua Ansible vars `meko_trainee_passwords: {team1: ..., team2: ..., team3: ..., team4: ...}`; cần bốn chuỗi khác nhau, dài tối thiểu 16 ký tự, file vars chỉ trên controller tin cậy. Không dùng management key làm mật khẩu thí sinh.

Tài khoản local GUI/console và SSH trùng tên đội. Provisioning bật XFCE/TigerVNC cổng 5900 qua service `meko-desktop` trước website; quyền GUI Access của image trên nền tảng vẫn cần bật riêng. Mật khẩu VNC 8 ký tự lưu tại `/etc/meko-boutique/gui-credentials.json`, khác password SSH. Hướng dẫn sửa Waiting for server và playbook GUI độc lập: [GUI-FIX.md](GUI-FIX.md). Mật khẩu nhân viên lưu tại `/etc/meko-boutique/staff.env` (root-only) và bền vững khi reprovision cùng VM.

## Log, health và checker

- App: `journalctl -u meko-boutique -f`
- Apache access/error: `/var/log/apache2/meko-access.log`, `/var/log/apache2/meko-error.log`
- Health: `curl http://127.0.0.1/health`
- Checker: đọc key root-only `/etc/meko-boutique/checker.env`, rồi chạy `python3 checker/check.py http://10.93.0.11 --key KEY --team team1 --task sqli`.
- Tick: biến `MEKO_TICK_SECONDS` trong unit; restart không reset state nếu `/var/lib/meko-boutique` còn nguyên.
- Patch: `/var/lib/meko-boutique/patches.json`, rồi `systemctl restart meko-boutique`.

Đặt/đọc flag bằng endpoint checker PUT/GET. Hiện chưa nối với giao diện chấm điểm hoặc token contract CyberRange. Bảo vệ key và chỉ expose checker cho mạng quản trị trong môi trường chấm thực tế.

## Bàn giao và nghiệm thu

Từ thư mục lab chạy `py package_lab.py`. ZIP nguồn có source, test, tài liệu, script đóng gói; Sandbox ZIP giữ layout gốc chuẩn. Cả hai loại bỏ `.runtime`, SQLite/state/flags, credential riêng, `.venv`, cache và file tạm.

Nghiệm thu hiện có thể thực hiện local: chạy tests, khởi động Flask, health, đăng ký/mua/hóa đơn, từng challenge, bật vá, tick và restart. Pool CyberRange/OpenStack chưa được provision từ môi trường này. Chỉ sau import revision mới, provision thật, kiểm tra SSH/GUI, Apache, peer connectivity, logs, checker và flag persistence mới được ghi nhận là nghiệm thu pool.
