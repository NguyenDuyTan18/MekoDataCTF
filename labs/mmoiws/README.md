# Một sandbox cho Meko Boutique và Crypto AD

Thư mục `sandbox/` là Sandbox Definition dùng chung. Topology giữ `team1`–`team3` và `checker` của Meko Boutique. Mỗi đội dùng cùng URL ở cả hai vòng, ví dụ `http://10.90.0.11/` cho `team1`. Apache nhận cổng 80 và chuyển tới app hiện hành trên `127.0.0.1:8080`.

| Vòng | Profile ForcAD | App trên VM đội |
| --- | --- | --- |
| 1 | `meko_boutique` | `meko-boutique.service` |
| 2 | `mmoiws` | `crypto-ad.service` |

## Chuẩn bị trước khi thi

- Sandbox mới chạy `sandbox/provisioning/playbook.yml` để cài Meko Boutique và cài sẵn Crypto AD. Trên pool Meko đã provision, có thể chạy riêng `crypto-install.yml` với inventory hiện có để cài thêm Crypto AD. Playbook này nạp unit và điều kiện kích hoạt nhưng không khởi động app Crypto.
- `lab.json` dùng cấu hình SSH của `ops/pool139/management-config`. Đổi đường dẫn nếu inventory thuộc pool khác. Dùng các alias `team1`, `team2`, `team3` và `checker` của pool cho Ansible.
- Nạp lại mã ForcAD mới trước trận để ticker ghi thời điểm kết thúc vòng 1 và API biết profile vòng 2. Trên máy Linux, đặt quyền thực thi cho `platform/ForcAD-demo/checkers/mmoiws/crypto.py` nếu chưa có.
- Chạy collector Meko như hiện tại. Mở một cửa sổ riêng cho collector Crypto AD trên máy chạy ForcAD.

```powershell
$env:MEKO_LAB = 'mmoiws'
python platform/ForcAD-demo/collect_checker.py --rpc-only
```

## Hẹn chuyển vòng

Chạy lệnh sau từ gốc repo, trên máy truy cập được admin API, thư mục RPC và inventory Ansible. Trên Windows có thể gọi `wsl.exe -- ansible-playbook` sau `--activate` nếu Ansible chạy trong WSL; dùng đường dẫn theo WSL cho inventory và playbook.

```sh
python platform/ForcAD-demo/switch_round.py --to mmoiws --yes --start --activate ansible-playbook -i inventory.ini labs/mmoiws/sandbox/provisioning/activate-round2.yml
```

Giữ tiến trình này mở. Nó chờ vòng Meko Boutique kết thúc và nghỉ đủ 600 giây, lưu vòng 1, rồi chạy playbook. Playbook dừng Meko trên tất cả VM, bật Crypto AD ở cùng cổng và kiểm tra dịch vụ từ máy `checker`. Script xác nhận collector trả UP cho từng đội rồi chuẩn bị và bật vòng 2. Nếu một bước kiểm tra thất bại, vòng 2 chờ xử lý. Khi chạy lại, mốc nghỉ lấy từ thời điểm vòng 1 kết thúc đã lưu trong ForcAD.

## Crypto AD

Mã gốc `chall.py`, `aes.py` và `core.c` ở `sandbox/crypto_ad/`. Bản web dùng AES 6 vòng, oracle `/encrypt` và dữ liệu bitmap gốc. ForcAD đặt flag mã hóa riêng theo locator. Trang `/` trả challenge hiện tại và `/public/<locator>` trả dữ liệu của flag đó. Endpoint `/bitmap/<group>/<structure>` trả HTTP 202 khi đang sinh file; yêu cầu lại để tải sau khi hoàn thành. Bitmap dùng AES-NI và tốn khoảng 512 MiB mỗi file.

Chạy kiểm thử cục bộ bằng `python -m unittest discover -s labs/mmoiws -p 'test_*.py'` với Flask đã cài.
