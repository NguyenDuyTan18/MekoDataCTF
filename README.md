# MEKOSHARING workspace

Workspace chia thành hai lớp. **platform** và **shared** dùng chung cho mọi bài lab. **labs** chứa riêng từng bài. Khi tạo lab mới, chỉ cần thêm một thư mục dưới `labs/`, xem [labs/_template/README.md](labs/_template/README.md). Thay đổi đợt sắp xếp lại, luồng gọi giữa các file và cách chạy từng file: [docs/TAI-CAU-TRUC-WORKSPACE.md](docs/TAI-CAU-TRUC-WORKSPACE.md). Token đội tự đồng bộ website → ForcAD: [docs/DONG-BO-TOKEN-FORCAD.md](docs/DONG-BO-TOKEN-FORCAD.md).

```
atk_def_platform/
├── platform/                      # Dùng lại cho mọi lab
│   ├── ForcAD-demo/               # Game engine A/D + scoreboard (Docker Compose, project "forcad-demo")
│   │   ├── checkers/<lab>/        # Checker ForcAD của từng lab (mount vào /checkers)
│   │   └── collect_checker.py     # Cầu nối ForcAD ↔ VM checker qua SSH, đọc labs/<lab>/lab.json
│   └── MekoDataCTF_Website/       # Website đăng ký đội (Node.js)
├── labs/
│   ├── _template/                 # Khung + hướng dẫn tạo lab mới
│   └── round1/                    # Lab IDOR/SQLi/Upload
│       ├── lab.json               # Nguồn cấu hình duy nhất: đội, IP, host, task, file SSH
│       ├── sandbox/               # Sandbox Definition CyberRange (topology, provisioning, app, checker)
│       └── service/               # Web lab có lỗ hổng, agent, deploy/recycle, test
├── shared/
│   ├── labconfig.py               # Đọc lab.json, dựng lệnh SSH chung
│   └── service-checker/           # Checker ServiceDesk độc lập
├── ops/pool101/                   # SSH vận hành Pool 101 (bí mật)
├── tools/                         # modeling, scenarios, rendering, documents, Understand-Anything
├── models/mekodatactf/            # Mô hình StarUML .mdj
├── docs/                          # Hướng dẫn, giải thích luồng
├── assets/references/             # Ảnh/tài nguyên đầu vào cho script
├── artifacts/                     # Bản phát hành, báo cáo xuất ra
└── adjust_settings.md             # Bảng tra cứu: chỉnh thông số nào ở đâu
```

Các script dùng đường dẫn tính theo vị trí file, không bắt buộc chạy từ thư mục gốc. Ví dụ: `python tools/rendering/verify_concrete_render.py` (cần StarUML API hoạt động tại `127.0.0.1:58321`). Một số script tạo mô hình còn cần file nguồn riêng từ máy tác giả; khi chạy trên máy khác, cần cấu hình lại đường dẫn nguồn trong script.

Biến môi trường dùng chung:

- `MEKO_LAB`: lab đang chạy, mặc định là `round1`. Dùng cho `collect_checker.py`.
- `MEKO_SSH_CONFIG`: ghi đè giá trị `ssh_config` trong `lab.json`.

## Bản đồ mã nguồn MekoDataCTF

Understand-Anything lưu bản đồ tiếng Việt tại `.ua/` và `platform/MekoDataCTF_Website/.ua/`. Hai bản đồ này được tạo **trước** khi sắp xếp lại thư mục, nên cần phân tích lại để đường dẫn khớp. Mở dashboard bằng `powershell -ExecutionPolicy Bypass -File .\tools\start-understand-dashboard.ps1`, rồi truy cập **Dashboard URL** có token được in trong terminal. Xem [hướng dẫn chạy và cập nhật bản đồ](docs/HUONG-DAN-UNDERSTAND-ANYTHING.md).
