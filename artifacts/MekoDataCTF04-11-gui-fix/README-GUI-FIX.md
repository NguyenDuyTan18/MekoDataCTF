# Bản sửa Open GUI · MekoDataCTF04-11

Source đối chiếu: https://github.com/NguyenThanhDatttttttt/MekoDataCTF04-11 tại commit `0dc84cf16a7bc5a56c15ff544049192c14ad094a`. Đây là bản sao sửa local; chưa push GitHub và chưa reprovision máy CyberRange.

## Lỗi source đã xác định

Playbook cũ chỉ cài/khởi động VNC sau khi website và tất cả HTTP peer checks thành công. Nếu triển khai web dừng trước đó, Open GUI không có VNC mới để kết nối. Bản sửa đưa desktop lên trước website, tách noVNC/Apache sang `browser-desktop.yml`, thêm `gui-repair.yml` để sửa GUI mà không cần web hoạt động. Listener dùng VncAuth, cổng 5900, XFCE chạy dưới `user-access`; password mapping hiện có được giữ nguyên.

Kiểm tra mới đăng nhập VNC và nhận một frame từ cả VM local và gateway. Khi đường gateway lỗi nhưng local đã tốt, VNC vẫn được giữ chạy để chẩn đoán mạng. Không dừng SSH, Apache hoặc dịch vụ mạng khi xử lý xung đột cổng; chỉ thay listener GUI đã xác minh.

## Áp dụng đúng repo bạn đã gửi

1. Giải nén `MekoDataCTF04-11-gui-patch.zip` vào gốc bản checkout repo này. Gói patch không có `group_vars/all.yml`, không ghi đè password riêng. Không chép source V2 vào repo Fashion Shop cũ.
2. Kiểm tra diff, tự commit/push lên revision bạn dùng khi đã sẵn sàng. Trong Sandbox Definition, chọn revision mới rồi reprovision. Chỉ sửa file trên máy local không cập nhật VM đang chạy.
3. Nếu quản trị viên chạy Ansible thủ công, dùng inventory thực do CyberRange tạo:

```bash
ansible-playbook -i /duong-dan/inventory provisioning/gui-repair.yml
```

Muốn sửa một đội, vẫn giữ gateway trong inventory và limit `--limit 'team1:gateway'`. Không dùng inventory giả hay IP ví dụ để tác động máy khác. Playbook này cấu hình account/VNC và có thể đổi listener native đã xác minh; chạy qua quyền quản trị CyberRange như provisioning thông thường.

4. Trong Open GUI nhập **password VNC của đúng đội** từ cấu hình đang dùng. Với VncAuth, username không xác thực ở lớp VNC; password SSH và VNC là hai loại khác nhau. Nếu Open GUI hiển thị trường username có thể điền `user-access`, nhưng password phải là VNC. Không đổi password theo phỏng đoán khi chưa biết endpoint portal đang trỏ tới đâu.

## Nếu vẫn thấy Waiting for server

Chạy các lệnh chỉ đọc dưới tài khoản management:

```bash
sudo systemctl status fashion-desktop --no-pager
sudo journalctl -u fashion-desktop -n 100 --no-pager
sudo ss -ltnp '( sport = :5900 )'
read -rsp 'VNC password: ' GUI_PASS; printf '\n'
printf '%s\n' "$GUI_PASS" | sudo /usr/bin/python3 /usr/local/libexec/fashion-check-vnc --host 127.0.0.1 --port 5900
unset GUI_PASS
```

Sau provision cần có hai task thành công: `Authenticate VNC and receive a desktop frame`, `Authenticate VNC from gateway and receive a desktop frame`. Banner RFB hoặc HTTP 200 một mình chưa đủ.

Nếu local và gateway đều nhận frame mà Open GUI vẫn chờ, cần kiểm tra **đích IP/cổng thực trong kết nối Guacamole**, đường tunnel/proxy và log guacd. Gateway thành công chưa chứng minh guacd kết nối được. Trên máy chạy guacd, kiểm tra TCP tới đúng target và xem log guacd lúc mở GUI (không gửi password/token). Không tự thay guacd thành localhost của container hoặc tắt VNC authentication.

Metadata image cần bật GUI Access để portal có nút Open GUI. Nếu nút đã hiện nhưng kết nối treo, bật metadata thêm không chứng minh đường VNC đã tốt. Tham khảo tài liệu chính thức: https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/ .

## Giới hạn kiểm chứng

Đã có regression tests cấu hình và protocol VNC bằng peer giả lập; các test không thay thế TigerVNC/XFCE/Guacamole thực. Chưa có kết nối pool của bạn, nên chưa xác nhận nguyên nhân cuối cùng hay tuyên bố Open GUI trên pool đã được sửa thành công.
