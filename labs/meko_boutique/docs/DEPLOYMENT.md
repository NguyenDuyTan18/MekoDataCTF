# Triển khai Meko Boutique lên CyberRangeCZ

Tài liệu này mô tả cách đưa bài lab vào môi trường ảo CyberRangeCZ
(https://docs.platform.cyberrange.cz/). Mô hình: **ba đội** Kali độc lập trên một LAN.

## 1. Chuẩn bị Sandbox Definition

Gốc **Sandbox Definition** là thư mục `sandbox/`, chứa:

```
topology.yml
provisioning/
  playbook.yml
  requirements.yml
  group_vars/all.yml
  trainee-access.yml
app/            (mã nguồn Flask + static + templates + seed)
checker/        (check.py)
```

Chạy `py package_lab.py` để tạo `meko-boutique-sandbox.zip`: giải nén ra có `topology.yml`,
`provisioning/`, `app/`, `checker/` **ngay tại gốc** — dùng làm nội dung một Git repository riêng.
Import vào CyberRange bằng Git URL + revision của repository đó (không import gốc workspace này).

> Việc tạo repository/push/import pool thực hiện riêng khi được phê duyệt.

## 2. Topology

- 3 VM Kali: `team1`–`team3`, IP `10.90.0.11`–`10.90.0.13` trên network `meko-lan` (`10.90.0.0/24`).
- 1 router Debian `gateway` (`10.90.0.1`), WAN `meko-wan` (`100.90.0.0/24`).
- Group Ansible `meko-teams`.

**Trước khi import, xác minh trên cloud đích:**
- Tên image (`kali`, `debian-12-x86_64`), management user (`debian`), flavor
  (`standard.kali`, `standard.small`) — **không được bảo đảm tồn tại** trên mọi cloud.
- CIDR `10.90.0.0/24` và WAN không trùng management/tenant network.
- Quota CPU/RAM/disk, khả năng truy cập package repo của Kali, routing/firewall và GUI Access.

Giảm còn 1–2 đội: bớt host trong `topology.yml` (`hosts`, `net_mappings`, nhóm `meko-teams`),
đồng thời bớt mục tương ứng trong `group_vars/all.yml` (`meko_team_passwords`, `meko_addresses`)
và phạm vi `hosts:` của `playbook.yml`. Playbook kiểm tra kết nối chéo đội theo `meko_addresses`,
nên hai danh sách phải khớp số đội.

## 3. Mật khẩu và tài khoản (cấu hình sẵn trong YAML)

Theo yêu cầu vận hành, mật khẩu được đặt sẵn trong `sandbox/provisioning/group_vars/all.yml`:

- `meko_team_passwords`: mật khẩu SSH/console từng đội (`team1`/`team2`/`team3`).
- `meko_staff_secret`: khóa gốc sinh mật khẩu khu nhân viên riêng cho từng đội.

Provisioning (`trainee-access.yml`):
- Tạo tài khoản đội trùng tên host, đặt mật khẩu từ YAML.
- **Khóa tài khoản `kali` mặc định** nếu image có (`password_lock`, shell `nologin`).
- Bật **SSH bằng password** cho các tài khoản đội qua drop-in `/etc/ssh/sshd_config.d/90-meko-trainee.conf`.
- Giữ nguyên tài khoản quản trị của nền tảng (ví dụ `debian`) và khóa quản trị CyberRange.

> Đây là mật khẩu CHỈ DÙNG cho môi trường đào tạo cô lập. Đổi toàn bộ trước khi dùng ngoài cloud
> huấn luyện riêng tư. Không expose dịch vụ bài tập ra Internet.

## 4. Provisioning

`playbook.yml` chạy trên `team1:team2:team3`, sau đó cài agent trên máy `checker` (xem `FORCAD.md`):
1. Cấu hình tài khoản/SSH (mục 3).
2. Cài `apache2`, `python3-flask`, `python3-waitress` từ repo Kali (không cần PyPI trên VM).
3. Chép app vào `/opt/meko-boutique`, tạo user dịch vụ `meko-web`, dữ liệu tại `/var/lib/meko-boutique`.
4. Ghi `staff.env` (mật khẩu nhân viên) root-only.
5. Systemd `meko-boutique` chạy Waitress bind `127.0.0.1:8080`; Apache reverse proxy cổng 80.
6. Health check cục bộ và kiểm tra HTTP chéo đội.
7. Cho tài khoản đội sửa `/opt/meko-boutique` và chạy `sudo systemctl restart meko-boutique.service`.
8. Trên máy `checker`: chép agent vào `/opt/meko-checker`, ghi `/etc/meko-checker/config.json`, chạy thử với từng đội.

`requirements.yml` cần collection `ansible.posix`. Runner nền tảng cần Ansible.

## 5. Training Definition

Bài lab này cung cấp Sandbox Definition và tài liệu. Training Definition (level, cloud_content,
passkey) tạo trong giao diện CyberRange, trỏ tới pool đã allocate. Nội dung level nên tham chiếu
`docs/THI-SINH.md` và bảng địa chỉ. Chưa kèm file training-definition.json; có thể bổ sung theo
mẫu Linear Training Definition của nền tảng.

## 6. Vận hành

- Log ứng dụng: `journalctl -u meko-boutique -f`
- Apache: `/var/log/apache2/meko-access.log`, `meko-error.log`
- Health: `curl http://127.0.0.1/health`
- Dữ liệu flag nằm trong `/var/lib/meko-boutique`; restart không làm mất nếu thư mục này còn.
- Bản vá: `/var/lib/meko-boutique/patches.json` rồi `systemctl restart meko-boutique` (xem GIANG-VIEN.md).
- Health CLI: `python3 checker/check.py http://10.90.0.11 --team team1`.

## 7. Giới hạn nghiệm thu

Nghiệm thu local đã thực hiện được: chạy test, khởi động Flask, health, đăng ký/mua/hóa đơn, từng
challenge, bật vá, restart. Pool CyberRangeCZ/OpenStack **chưa** được provision từ môi trường
này. Chỉ sau khi import revision, provision thật, kiểm tra SSH bằng password, Apache, kết nối chéo
đội, logs, checker và flag persistence mới được ghi nhận là nghiệm thu pool.
