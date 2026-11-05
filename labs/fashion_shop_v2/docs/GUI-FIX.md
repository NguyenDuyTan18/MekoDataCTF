# Sửa Open GUI bị Waiting for server

Đối chiếu source người dùng cung cấp tại https://github.com/NguyenThanhDatttttttt/MekoDataCTF04-11/commit/0dc84cf16a7bc5a56c15ff544049192c14ad094a . Repo đó là Fashion Shop cũ. Bản sao sửa tương ứng nằm riêng trong `artifacts/MekoDataCTF04-11-gui-fix`; source cũ trong `labs/fashion_shop` được giữ nguyên.

V2 trước đây tạo tài khoản nhưng thiếu desktop/VNC. Bản sửa bổ sung XFCE và TigerVNC qua `provisioning/desktop.yml`, bật mặc định và chạy trước triển khai web. Desktop của team1–team4 chạy dưới đúng tài khoản đội. Backend cửa hàng và desktop là hai service riêng: `meko-boutique`, `meko-desktop`.

VNC mặc định cổng 5900, display X :9 và `localhost=no`; display :9 không có nghĩa cổng 5909 vì unit đặt `-rfbport 5900` rõ ràng. Xác thực VncAuth luôn bật. Mật khẩu VNC 8 ký tự riêng được lưu ổn định trong `/etc/meko-boutique/gui-credentials.json`, root-only. SSH password đầy đủ vẫn ở `credentials.json`. Có thể cấp mapping private `meko_trainee_vnc_passwords` gồm password VNC 8 ký tự ASCII chữ/số cho mỗi đội.

Reprovision từ ZIP/revision mới. Hoặc quản trị viên chạy riêng trong gốc Sandbox Definition bằng inventory thực:

```bash
ansible-playbook -i /duong-dan/inventory provisioning/gui-repair.yml
```

Entry point này không phụ thuộc health của website hay Apache. Không sử dụng playbook này với inventory của lab cũ. Để chọn một đội dùng `--limit 'team1:gateway'` và giữ gateway trong inventory.

Provisioning kiểm tra XFCE, banner RFB, đăng nhập VNC và nhận frame từ VM local rồi gateway. Nếu đường gateway lỗi sau khi local đã tốt, service được giữ chạy; lỗi chỉ rõ tầng cần kiểm tra. Listener không xác định hoặc thuộc SSH/web/network không bị dừng tự động.

Trên VM, qua tài khoản management:

```bash
sudo systemctl status meko-desktop --no-pager
sudo journalctl -u meko-desktop -n 100 --no-pager
sudo ss -ltnp '( sport = :5900 )'
read -rsp 'VNC password: ' GUI_PASS; printf '\n'
printf '%s\n' "$GUI_PASS" | sudo /usr/bin/python3 /usr/local/libexec/meko-check-vnc --host 127.0.0.1 --port 5900
unset GUI_PASS
```

Open GUI sử dụng VNC: nếu portal hỏi username, nhập tên đội, còn password là **VNC password**, không phải SSH password. VncAuth xác thực bằng password, không kiểm tra username. Nút Open Console dùng SSH và password SSH.

Nếu hai probe VNC đều đạt mà portal vẫn Waiting for server, cần log guacd và endpoint IP/cổng mà Guacamole thực sự sử dụng. Mạng gateway không phải đường kết nối guacd đầy đủ. Image GUI Access chỉ quyết định việc có nút GUI; không thay việc kiểm tra route, tunnel, security group, endpoint và password.

Chưa chạy Open GUI trên pool thật. Tài liệu chính thức: https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/ .
