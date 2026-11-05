# Chạy Meko Boutique với ForcAD

Tài liệu nội bộ cho người vận hành.

## Lịch thi

Một round đúng 50 phút: 10 tick, mỗi tick 5 phút, mỗi đội nhận 5 flag mỗi tick (một flag cho mỗi task).
Khai báo trong `backend/lib/storage/lab_profile.py`: `round_time: 300`, `ticks_per_round: 10`,
`check_seconds: 60`, `drain_ticks: 0`. Flag nộp được ở tick tạo và 2 tick tiếp theo (`flag_lifetime: 2`).

Lịch được neo vào lúc bắt đầu round. Bước kiểm tra chạy trong 60 giây cuối của tick và đội vẫn nộp flag
được trong lúc đó. Nếu kiểm tra chậm, tick sau bắt đầu trễ nhưng vẫn kết thúc đúng giờ, nên chỉ tick cuối
mới có thể làm round dài hơn. Tạm dừng dời toàn bộ lịch, round vẫn đủ thời lượng.
Giá trị này được ghi vào ForcAD khi bấm **Chuẩn bị**; đổi sau đó phải chuẩn bị lại cuộc thi.

## Một tick diễn ra thế nào

1. **Mở tick:** ForcAD tăng số tick, nạp lại cache flag, đặt hạn 5 phút.
2. **Nạp flag:** mỗi cặp đội và task nhận một flag mới qua `put`. `put` lỗi được thử lại sau 10 giây trong suốt tick, dùng đúng flag đó.
3. **Tấn công:** đội đọc `/api/client/attack_data/`, khai thác và nộp flag trong suốt 5 phút.
4. **Phút thứ 4:** ngừng nạp flag, chờ `put` đang chạy xong.
5. **Kiểm tra:** với mỗi cặp đội và task, chạy `check` rồi `get` flag của tick này và 2 tick trước.
6. **Chấm SLA:** đội được +1 nếu cả 5 task đều UP. Hết 5 phút thì mở tick mới.
7. **Hết tick 10:** dừng nhận flag và kết thúc round ở phút thứ 50.

Code app và bản vá của đội không đổi theo tick, chỉ dữ liệu được thêm vào.

## Đổi lab trên cùng một database

Nếu database đang ở lab khác: dừng cuộc thi, bấm **Đóng và lưu hồ sơ**, tải JSON về máy, rồi bấm nút
**Chuẩn bị** của lab mới. Điểm và flag của lượt cũ bị xóa khỏi bảng thi, hồ sơ vẫn còn trong
`MekodataArchives`.

## Đường đi của checker

```text
ForcAD (Docker) → checkers/meko_boutique/<loại>.py → thư mục rpc/
  → platform/ForcAD-demo/collect_checker.py (Windows, giữ SSH key)
  → SSH quản trị → VM checker: /opt/meko-checker/agent.py
  → HTTP trong LAN lab → web của đội
```

## Các bước

1. Đưa nội dung `sandbox/` vào repository Sandbox Definition, tạo pool mới trên CyberRangeCZ.
2. Tải management SSH access của pool về `ops/pool139/`, đặt tên `management-config`. Nếu dùng
   thư mục khác, sửa `ssh_config` trong `lab.json`.
3. Kiểm tra SSH từ thư mục gốc workspace:

   ```powershell
   ssh -F .\ops\pool139\management-config checker "hostname"
   ```

4. Khởi động lại các container ForcAD để nạp code backend. Build lại `nginx` để có nút mới.
5. Chạy collector và giữ cửa sổ này mở:

   ```powershell
   $env:MEKO_LAB = 'meko_boutique'
   python platform/ForcAD-demo/collect_checker.py
   ```

6. Trên trang điều khiển round, bấm **Chuẩn bị Meko Boutique (5 task)**, sau đó bấm **Bắt đầu**.
   Bước chuẩn bị tự tạo `team1`–`team3` nếu chưa có và tắt các task, đội của lab khác.

## Kiểm tra nhanh trên VM checker

```bash
echo '{"task":"idor","action":"check","ip":"10.90.0.11"}' | \
  sudo python3 /opt/meko-checker/agent.py --config /etc/meko-checker/config.json
```

Kết quả `"status": 101` nghĩa là UP.

## Xử lý lỗi

| Hiện tượng | Kiểm tra |
|---|---|
| `SSH collector unavailable` | Collector có đang chạy với `MEKO_LAB=meko_boutique` không |
| `Sandbox agent unavailable` | SSH tới `checker`, đường dẫn `ssh_config`, quyền `sudo -n` của user quản trị |
| Mọi loại đều DOWN | Web của đội và đường mạng từ VM checker tới `10.90.0.x` |
| Chỉ JWT và Backup lỗi | Mật khẩu staff trong `/etc/meko-checker/config.json` và `staff.env` của đội |
