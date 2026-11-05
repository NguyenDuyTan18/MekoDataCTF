# Trích LVTN-main: SSH bằng mật khẩu cho thí sinh

Nguồn đọc trực tiếp: `LVTN-main.zip`. Chỉ trích hướng dẫn; chưa sửa playbook, topology, tài khoản, mật khẩu hoặc VM của bất kỳ lab nào.

## 1. Phần đã có trong LVTN-main

| Nội dung | Vị trí trong ZIP |
|---|---|
| Tài khoản, cấu hình client và đường đi SSH | `LVTN-main/README.md`, mục Team login, dòng 28–75 |
| Tạo user, bật password-only và xóa authorized_keys | `LVTN-main/provisioning/playbook.yml`, dòng 176–239 |
| Ánh xạ mật khẩu theo VM | `LVTN-main/provisioning/group_vars/all.yml`, biến `lab_team_passwords` |
| Role tạo tài khoản | `LVTN-main/provisioning/requirements.yml`, role `user-access` v1.0.0 |

Mỗi VM đội có tài khoản `user-access`; mật khẩu lấy theo tên host, không dùng một mật khẩu chung. README hướng dẫn phát riêng mật khẩu tương ứng cho từng đội. Không sao chép các mật khẩu mẫu trong ZIP sang môi trường thi.

Đoạn biến trong playbook nguồn:

```yaml
vars:
  user_access_username: user-access
  user_access_password: '{{ lab_team_passwords[inventory_hostname] }}'
  user_access_shell: /bin/bash
  user_access_sudo: false
```

Role `user-access` được gọi với `no_log: true`. Playbook kiểm tra mỗi host có mật khẩu, cài `openssh-server`, rồi tạo tài khoản. Nguồn chỉ kiểm tra mật khẩu không rỗng, chưa có kiểm tra độ mạnh hoặc phát hiện mật khẩu trùng giữa các đội.

## 2. Cấu hình server: chỉ tài khoản thí sinh dùng password-only

Nguồn đặt cấu hình tại `/etc/ssh/sshd_config.d/00-idor-lab.conf`:

```sshconfig
Match User user-access
    PasswordAuthentication yes
    PubkeyAuthentication no
    AuthenticationMethods password
    AllowTcpForwarding yes
Match all
```

Sau đó xóa `/home/user-access/.ssh/authorized_keys`. Playbook thêm Include cho thư mục drop-in vào đầu `/etc/ssh/sshd_config` và dùng handler reload dịch vụ `ssh`.

Các thiết lập trên áp dụng cho `user-access`; không chuyển toàn bộ tài khoản quản trị sang mật khẩu. `AllowTcpForwarding yes` là thiết lập của nguồn để hỗ trợ tunnel; cần quyết định riêng nếu mô hình triển khai không cần chức năng này.

## 3. Thí sinh kết nối như thế nào?

Nếu máy thí sinh có đường mạng hợp lệ tới VM đội:

```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no user-access@10.80.0.11
```

Nhập mật khẩu đội khi SSH hỏi. Không đưa mật khẩu vào câu lệnh. `10.80.0.11` là IP attacker1 của LVTN-main, không phải IP lab bán quần áo.

Nếu phải đi qua mạng quản lý CyberRange, README mô tả:

```text
Máy truy cập → landing host (key) → man (key) → VM đội (password)
```

Mẫu cấu hình tương ứng, thay toàn bộ dấu `<...>` bằng thông tin của allocation hiện tại:

```sshconfig
Host landing
    HostName <landing-host>
    User <landing-user>
    IdentityFile <duong-dan-key-do-ban-to-chuc-quan-ly>
    IdentitiesOnly yes

Host man
    HostName <man-ip>
    User user
    IdentityFile <duong-dan-key-do-ban-to-chuc-quan-ly>
    IdentitiesOnly yes
    ProxyJump landing

Host team01
    HostName 10.80.0.11
    User user-access
    PreferredAuthentications password
    PubkeyAuthentication no
    ProxyJump man
```

Chạy trên máy đang giữ cấu hình và có quyền sử dụng key trung gian:

```bash
ssh -F <duong-dan-config> team01
```

**Giới hạn của thiết kế nguồn:** chính README cảnh báo sandbox `user-key` có thể đăng nhập tài khoản nền tảng `user` trên nhiều VM. Vì vậy không phát toàn bộ ZIP truy cập hoặc key này cho các đội. Mẫu ProxyJump ở trên không tự giải quyết cách để mỗi thí sinh kết nối từ máy riêng mà không nhận key chung; người vận hành phải cấp đường truy cập hoặc tài khoản trung gian có giới hạn riêng. Mật khẩu khác nhau chỉ tách quyền của tài khoản `user-access`, không bảo đảm tách đội nếu còn đường đăng nhập khác.

## 4. Bỏ mật khẩu Kali mặc định: phần bổ sung, không có trong nguồn

Rà soát các file cấu hình/script dạng văn bản trong ZIP không tìm thấy tác vụ khóa tài khoản `kali` mặc định. Password-only cho `user-access` không vô hiệu hóa tài khoản `kali` hay các tài khoản có sẵn trong image.

Nếu sau này triển khai, nên khóa tài khoản `kali` khi không dùng, thay vì chỉ đổi mật khẩu sang một giá trị chung khác. Không dùng `passwd -d kali`: lệnh đó xóa mật khẩu, không phải khóa tài khoản.

Thứ tự thực hiện trên từng VM, bởi quản trị viên:

1. Xác nhận đăng nhập quản trị bằng tài khoản riêng vẫn hoạt động và có kênh khôi phục console. Không khóa `kali` nếu đây đang là tài khoản quản trị của image.
2. Tạo và kiểm tra đăng nhập `user-access` với mật khẩu riêng của đội ở một phiên SSH thứ hai.
3. Kiểm tra `getent passwd kali`. Nếu có tài khoản đó và không dùng cho quản trị, áp dụng ví dụ dưới đây. Đây là hướng dẫn thực hiện sau, chưa chạy trên máy nào.

```bash
sudo usermod --lock --expiredate 1 --shell /usr/sbin/nologin kali
```

Khóa password, đặt tài khoản hết hạn và đổi shell nhằm vô hiệu hóa đăng nhập tài khoản mặc định. Chỉ khóa password không bảo đảm chặn đăng nhập bằng key; cần kiểm tra cả chính sách SSH thực tế. Các phiên đang tồn tại cần được quản trị viên xem xét riêng.

## 5. Nghiệm thu trước khi phát cho thí sinh

Trên VM, quản trị viên kiểm tra cấu hình và giá trị hiệu lực cho tài khoản thí sinh:

```bash
sudo sshd -t
sudo sshd -T -C user=user-access,host=localhost,addr=127.0.0.1
```

Đối chiếu ba mục `passwordauthentication yes`, `pubkeyauthentication no`, `authenticationmethods password`. Nếu có Match theo địa chỉ hoặc tên máy, kiểm tra lại với địa chỉ nguồn thực tế.

- Tài khoản thí sinh đăng nhập được bằng mật khẩu đúng trên VM được giao.
- Mật khẩu của đội này không đăng nhập được vào tài khoản thí sinh trên VM đội khác.
- Tài khoản quản trị riêng vẫn hoạt động.
- Sau khi vô hiệu hóa Kali mặc định, thử đăng nhập tài khoản đó phải bị từ chối; không chỉ kiểm tra tên tác vụ hoặc trạng thái password.
- Không công bố bảng mật khẩu đầy đủ, key quản trị hoặc key nền tảng. Khi áp dụng thực tế, thay mật khẩu mẫu bằng bí mật riêng từng đội, lưu qua Ansible Vault hoặc nguồn bí mật của người vận hành; không commit plaintext.

## 6. Phạm vi đối với workspace hiện tại

Lab `fashion_shop` hiện khai báo bốn VM Debian, chưa có VM Kali và chưa áp dụng phần truy cập ở trên. Theo yêu cầu, lần này chỉ tạo tài liệu trích dẫn. Không chỉnh ZIP nguồn, Round 1, lab bán quần áo hoặc tài khoản trên máy đang chạy.
