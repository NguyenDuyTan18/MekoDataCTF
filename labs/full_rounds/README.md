# MekoDataCTF · Full Rounds

Sandbox Definition cho CyberRangeCZ trên OpenStack, dùng topology của Meko Boutique. Ba VM đội `team1`–`team3` ở `10.90.0.11`–`10.90.0.13` chạy cả hai vòng. VM `checker` ở `10.90.0.30` chạy hai agent theo yêu cầu từ ForcAD.

| Vòng | Profile ForcAD | Dịch vụ trên mỗi VM đội |
| --- | --- | --- |
| 1 · Meko Boutique | `full_rounds` | HTTP 80 · SQLi, IDOR, Upload, JWT, Backup |
| 2 · Crypto AD | `full_rounds_crypto` | TCP 9011 Curveball, 9012 Padding Oracle, 9013 ECDSA Nonce |

Mỗi vòng có **10 phút xem đề**, sau đó **10 tick × 5 phút thi**. ForcAD đặt và nhận flag khi đã vào tick thi. Vòng 2 giữ đội, token và điểm đã có ở vòng 1.

## Import vào CyberRangeCZ

Đưa **nội dung bên trong `labs/full_rounds/`** vào gốc repo Git mà CyberRangeCZ sẽ đọc. Hai điểm vào là `topology.yml` và `provisioning/playbook.yml`. Giữ cùng các thư mục `app/`, `checker/`, `provisioning/` và `round2/` vì Ansible tải mã từ các đường dẫn tương đối này. Pool dùng image và flavor của topology Meko Boutique.

Tạo **Sandbox Definition** từ URL Git, chọn revision chứa gói này rồi tạo pool. Worker đọc sẵn cấu hình đăng nhập từ `provisioning/group_vars/all.yml`. Tải `training-definition.json` lên **Linear Training Definitions → Upload** và liên kết với pool trong **Training Instance**. File JSON có một bước truy cập sandbox và hướng dẫn cho cả hai vòng. [Cấu trúc Sandbox Definition](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-definition/) · [Import Linear Training Definition](https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-definition/linear-training-definition/#2-upload-a-definition-from-json-file)

## ForcAD gọi checker

| Profile | Lệnh gọi trên VM `checker` |
| --- | --- |
| `full_rounds` | `sudo -n /usr/bin/python3 /opt/meko-checker/agent.py --config /etc/meko-checker/config.json` |
| `full_rounds_crypto` | `sudo -n /usr/bin/python3 /opt/crypto-checker/agent.py --config /etc/crypto-checker/config.json` |

Playbook cài cả hai agent và giữ giao thức JSON qua stdin/stdout cho `check`, `put` và `get`. Token Crypto được lấy từ cấu hình dịch vụ trên từng VM rồi ghi vào cấu hình riêng của agent Crypto. Các dịch vụ Crypto lắng nghe sau provisioning và nhận flag khi ForcAD gọi `put` ở vòng 2.

Sau khi cập nhật mã ForcAD, build lại các container bằng `docker compose up -d --build` trong `platform/ForcAD-demo`. Trên máy ForcAD, dùng **SSH Management Access** của sandbox vừa provision. File cấu hình SSH cần có alias `checker`. Chạy một collector cho cả hai vòng từ gốc workspace:

```powershell
$env:MEKO_SSH_CONFIG = 'C:/duong-dan/management-config'
$env:MEKO_LAB = 'full_rounds'
python platform/ForcAD-demo/collect_checker.py --rpc-only --labs 'full_rounds,full_rounds/round2'
```

## Bắt đầu và chuyển vòng

1. Đăng nhập admin ForcAD rồi trở về trang chính. Trong **Điều khiển round**, chọn lab cho từng vòng và bấm **Lưu cấu hình**. Mặc định là **Full Rounds Web** và **Full Rounds Crypto**. Nếu đã có lượt thi, dùng **Đóng và lưu hồ sơ** trước khi chọn cặp lab mới.
2. Bấm **Round 1** hoặc **Round 2**. Vòng được chọn bắt đầu 10 phút xem đề rồi tự mở tick 1. Có thể mở Round 2 trước.
3. Để đổi vòng khi đang thi, bấm **Dừng** và đợi các nút chọn vòng bật lại. Bấm vòng muốn chạy. Khi quay lại một vòng đã tạm dừng, đồng hồ chạy tiếp từ thời gian còn lại.
4. **Đóng và lưu hồ sơ** lưu cả hai vòng. **Bắt đầu lại từ tick 0** lưu lượt hiện tại, đặt lại hai vòng và chờ quản trị viên chọn vòng để bắt đầu.

Hai vòng cần hai profile checker khác nhau và dịch vụ của mỗi lab cần sẵn sàng trước khi chạy. ForcAD dùng tick nội bộ 1–10 và 11–20 để lưu lịch sử riêng. Bảng điểm cộng kết quả hai vòng khi chúng dùng cùng tập IP đội.

## Thông tin truy cập đội

| Cách truy cập | Thông tin đăng nhập |
| --- | --- |
| SSH hoặc **Open Console** | Tài khoản Linux trùng tên VM (`team1`, `team2`, `team3`) và mật khẩu SSH của đội, theo Meko Boutique gốc. |
| **Open GUI**, nếu BTC bật | Nhập mật khẩu VNC riêng của đội. Phiên XFCE chạy sẵn dưới tài khoản Linux của đội. |

Trong mạng sandbox, Team 1 có thể chạy `ssh team1@10.90.0.11` và nhập mật khẩu SSH. Nếu dùng file SSH do CyberRangeCZ cấp, chọn alias VM của đội và truyền `-l team1` để SSH dùng đúng tài khoản Linux.

Cấu hình cơ bản trong `provisioning/group_vars/all.yml` dùng nguyên ba mục và giá trị của Meko Boutique gốc, gồm `meko_team_passwords`, `meko_staff_secret` và `meko_addresses`. Web và checker cùng dùng khóa staff trong file này. Địa chỉ đội được dùng cho cả Web và Crypto. Đây là cấu hình mặc định của lab cô lập.

Khi chạy Ansible thủ công, dùng `ansible-playbook -i inventory.yml provisioning/playbook.yml`. Có thể truyền `--extra-vars '@.secrets/access.yml'` để ghi đè giá trị mặc định cho một pool cụ thể.

Để cài **Open GUI**, cấp thêm `MEKO_TEAM1_VNC_PASSWORD` đến `MEKO_TEAM3_VNC_PASSWORD` cho worker hoặc truyền thêm `--extra-vars '@.secrets/gui-access.yml'` khi chạy thủ công. Cả ba mật khẩu VNC cần khác nhau và gồm đúng tám chữ cái hoặc chữ số ASCII. Image Kali cần bật **GUI Access** và Guacamole phải tới được TCP `5900` trên VM. [Sandbox Access của CyberRangeCZ](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/#web-based-access)

## Kiểm tra cục bộ

Trong Python có Flask, PyYAML, ecdsa và pycryptodome, chạy `python -m unittest discover -s tests` từ gốc gói.
