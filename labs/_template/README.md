# Khung tạo lab mới

Một lab gồm 3 phần. Phần **platform** (ForcAD, website) và **shared** dùng chung, không cần sửa.

```
labs/<ten-lab>/
├── lab.json     # đội, IP, host SSH, task — nguồn cấu hình duy nhất
├── sandbox/     # Sandbox Definition CyberRange (topology.yml, provisioning/, app/, checker/)
└── service/     # dịch vụ có lỗ hổng + agent + deploy.py/recycle.py + test
platform/ForcAD-demo/checkers/<ten-lab>/   # checker ForcAD (bắt buộc nằm trong thư mục mount /checkers)
```

## Các bước

1. Chép `labs/_template/lab.json` sang `labs/<ten-lab>/lab.json`, sửa `name` và `tasks`. Giá trị `name` phải trùng tên thư mục checker trong ForcAD. Danh sách `teams` sinh từ các đội đăng ký trên website:
   ```powershell
   cd platform/MekoDataCTF_Website
   npm run export:lab -- --write <ten-lab> --subnet 10.80.0 --start 11
   ```
   **Quy ước tên:** tên đội đăng ký → slug (bỏ dấu, a-z 0-9 '-', ví dụ "Hà Nội #1" → `ha-noi-1`). Slug này vừa là tên đội ForcAD vừa là tên máy ảo. `host` để trống thì lấy bằng `name`. Muốn đặt tên khác, sửa ô "Tên đội trên ForcAD" ở trang quản trị đội.
2. Chép `labs/round1/sandbox/` sang `labs/<ten-lab>/sandbox/`. Sửa `topology.yml`, `provisioning/group_vars/all.yml`, `checker/web_targets.json` cho khớp với `lab.json`. Ba file này do CyberRange/Ansible đọc trực tiếp nên vẫn phải tự sửa.
3. Chép `labs/round1/service/` sang `labs/<ten-lab>/service/` rồi thay `webservice.py`/`agent.py` bằng dịch vụ mới. `deploy.py` và `recycle.py` tự đọc `lab.json` của thư mục cha, nên không cần sửa danh sách đội hay IP.
4. Chép `platform/ForcAD-demo/checkers/round1/` sang `checkers/<ten-lab>/`. File `common.py` dùng lại nguyên vẹn; mỗi task chỉ là một file `<task>.py` gọi `main('<task>')`.
   ⚠️ Vòng đời Round 1 trên dashboard (Chuẩn bị/Lưu/Tái tạo) nằm trong `platform/ForcAD-demo/backend/lib/storage/round1.py`. File này vẫn viết cứng `PREFIX = '/checkers/round1/'`, các task `idor/sqli/upload` và 4 IP `10.80.0.11–14`. Lab mới chỉ chạy được trên dashboard mà không sửa backend khi giữ nguyên 4 IP và tên task này, **và** đặt `"name": "round1"` (checker nằm ở `checkers/round1/`, thay cho checker cũ). Nếu khác, phải sửa `round1.py` (và `round_control.py`) rồi build lại container backend.
5. Tạo đội trên ForcAD **đúng các tên trong `lab.json`** (kèm IP). Website đang chạy sẽ tự đẩy token sang trong vòng 60 giây (xem [docs/DONG-BO-TOKEN-FORCAD.md](../../docs/DONG-BO-TOKEN-FORCAD.md)). Sau đó form nộp flag tự khóa ô "Đội của bạn" theo đúng đội.
6. Chạy collector cho lab đó: `$env:MEKO_LAB = '<ten-lab>'; python platform/ForcAD-demo/collect_checker.py`. Nếu không đặt `MEKO_LAB` thì mặc định là `round1`.

Nếu dùng file SSH khác `ops/pool101/management-config`, đặt `MEKO_SSH_CONFIG` (đường dẫn tương đối tính từ gốc workspace, hoặc đường dẫn tuyệt đối).

## Khai báo lịch thi cho lab mới

Thêm một mục vào `PROFILES` trong `platform/ForcAD-demo/backend/lib/storage/lab_profile.py`, thêm nút Chuẩn bị trong
`front/public/round-control.js`, rồi build lại `nginx`. Không cần sửa `round1.py` hay `round_schedule.py`.

| Trường | Ý nghĩa | Ví dụ Meko Boutique |
|---|---|---|
| `tasks` | Mỗi task một flag cho mỗi đội mỗi tick | 5 task, tức 5 flag |
| `round_time` | Độ dài một tick, tính bằng giây | 300 |
| `ticks_per_round` | Số tick trong round | 10 |
| `check_seconds` | Lớn hơn 0: chạy `check` trong tick, round đúng giờ. Bằng 0: chạy sau tick | 60 |
| `drain_ticks` | Số tick nhận flag thêm sau tick cuối | 0 |

Thời lượng round là `round_time × (ticks_per_round + drain_ticks)`. `check_seconds` phải đủ cho `check` và `get`
của mọi cặp đội, task, và nhỏ hơn `round_time` ít nhất 60 giây.
