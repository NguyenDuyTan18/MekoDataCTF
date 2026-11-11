# Thư mục `checkers/` của ForcAD

ForcAD gọi một tệp ở đây cho mỗi lỗ hổng, mỗi đội, mỗi tick:

```
<lỗ hổng>.py check <ip>                          → dịch vụ còn chạy đúng không (SLA)
<lỗ hổng>.py put   <ip> <mã flag> <flag> 1       → cắm flag mới
<lỗ hổng>.py get   <ip> <dữ liệu riêng> <flag> 1 → flag cũ còn không (phòng thủ)
```

Mã thoát: `101` hoạt động · `102` hỏng dữ liệu · `103` sai chức năng · `104` sập · `110` lỗi bộ chấm.

Các tệp ở đây **không tự kiểm tra**. Chúng chỉ chuyển yêu cầu, vì Docker không tới được mạng của pool:

```
ForcAD → checkers/<bài>/<lỗ hổng>.py → hộp thư checkers/<bài>/rpc/
       → collect_checker.py (chạy trên máy host) → SSH → máy ảo checker
       → labs/<bài>/checker/meko_checker.py (logic kiểm tra thật) → kết quả quay lại
```

## Cấu trúc

| Thư mục | Vai trò |
|---|---|
| `_shared/forcad_rpc.py` | Phần chuyển yêu cầu dùng chung. **Không sửa.** |
| `_template/task.py` | Mẫu tệp cho một lỗ hổng. Chép ra, chỉ đổi tên tệp. |
| `full_rounds/` | Vòng 1 · Web (đang dùng) |
| `full_rounds_crypto/` | Vòng 2 · Crypto (đang dùng) |
| `meko_boutique/`, `mmoiws/`, `round1/`, `mekodata_bridge/` | Bài cũ, để nguyên. `meko_boutique/common.py` là bản cũ của `_shared/forcad_rpc.py`. |
| `<bài>/rpc/` | Hộp thư tạm, tự sinh. Không commit. |

## Thêm bài mới `X`

1. Tạo `checkers/X/`. Tên phải **trùng trường `"name"` trong `labs/X/lab.json`**, vì bộ thu đọc hộp thư ở `checkers/<name>/rpc/`.
2. Với mỗi lỗ hổng, chép `_template/task.py` thành `checkers/X/<lỗ hổng>.py`, ví dụ `xss.py`. Không sửa nội dung: tên lỗ hổng được lấy từ tên tệp.
3. Thêm vào `platform/ForcAD-demo/.gitignore`:
   ```
   !checkers/X/
   checkers/X/*
   !checkers/X/*.py
   ```
4. Viết logic kiểm tra thật ở `labs/X/checker/` (chép `agent.py`, `forcad.py`, `meko_checker.py` từ `labs/full_rounds/checker/`, rồi viết lại các lớp lỗ hổng).
5. Khai báo bài trong `backend/lib/storage/lab_profile.py`: `prefix` là `/checkers/X/`, `tasks` là các tên tệp ở bước 2.
6. Chạy bộ thu kèm bài mới: `python platform/ForcAD-demo/collect_checker.py --rpc-only --labs X`.

## Quy tắc

- Tên phải khớp ở bốn nơi: thư mục `checkers/X/`, `"name"` trong `lab.json`, `prefix`/`tasks` trong `lab_profile.py`, và tên tệp lỗ hổng.
- Không đổi tên hoặc di chuyển tệp lỗ hổng khi round đang chạy, vì ForcAD lưu cứng đường dẫn trong cơ sở dữ liệu.
- Không xóa `meko_boutique/common.py` khi chưa chắc không còn bài cũ nào dùng.
