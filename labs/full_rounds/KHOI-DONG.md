# Khởi động Full Rounds — từng bước

Thứ tự bắt buộc: **ForcAD → schema → collector → mở round**. Collector phải chạy
trước khi tick 1 mở, nếu không checker trả `110 "SSH collector unavailable"` và không có flag.

Mọi lệnh chạy từ gốc workspace: `c:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform`.

## 0. Yêu cầu trước

- Docker Desktop đang bật.
- Pool đã provision; file SSH management nằm ở `ops/pool141/management-config` và có alias `checker`.
- Mật khẩu admin đọc trong `platform/ForcAD-demo/config.yml` (block `admin:`).
- Trang điều khiển: http://127.0.0.1:18080/

## 1. Bật ForcAD

```powershell
cd platform/ForcAD-demo
docker compose up -d --build
cd ../..
```

## 2. Cài/cập nhật schema round

```powershell
docker compose -f platform/ForcAD-demo/docker-compose.yml exec -T ticker python /app/scripts/setup_round1.py
```

Chờ thấy `Round 1 schema installed`. Nếu báo *database system is starting up*, đợi vài giây rồi chạy lại.

## 3. Bật collector (mở CỬA SỔ RIÊNG, giữ mở suốt buổi)

```powershell
$env:MEKO_SSH_CONFIG = 'C:/Users/Admin/Desktop/MekoData_Ky/atk_def_platform/ops/pool141/management-config'
$env:MEKO_LAB = 'full_rounds'
python platform/ForcAD-demo/collect_checker.py --rpc-only --labs 'full_rounds,full_rounds/round2'
```

Một collector phục vụ cả hai vòng. Chỉ chạy **một** collector — nếu đã có tiến trình chạy,
collector thứ hai báo `Cannot acquire collector lock` là đúng (đã có cái đang chạy).

Kiểm tra collector đang chạy:
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*collect_checker*' } | Select-Object ProcessId,CommandLine
```

## 4. Mở Round 1

Cách nhanh (qua admin API, không cần bấm web):
```powershell
python platform/ForcAD-demo/switch_round.py --to full_rounds --yes --start
```

Hoặc trên web http://127.0.0.1:18080/ : đăng nhập admin → **Điều khiển round** →
chọn **Full Rounds Web** / **Full Rounds Crypto** → **Lưu cấu hình** → bấm **Round 1**.

Sau khi mở: `phase=preview` nghĩa là đang 10 phút xem đề, hết giờ tự mở tick 1
(10 tick × 5 phút). Xem trạng thái bất cứ lúc nào:
```powershell
python platform/ForcAD-demo/switch_round.py --to full_rounds
```

## 5. Chuyển sang Round 2 (Crypto)

Bấm **Dừng** trên web rồi bấm **Round 2**, hoặc:
```powershell
python platform/ForcAD-demo/switch_round.py --to full_rounds_crypto --yes --start
```
Round 2 giữ đội, token và điểm của Round 1. Collector ở bước 3 không cần khởi động lại.

## 6. Kết thúc

Trên web bấm **Đóng và lưu hồ sơ** (lưu cả hai vòng). Đóng cửa sổ collector.
`docker compose -f platform/ForcAD-demo/docker-compose.yml stop` nếu muốn tắt hệ thống.

## Thí sinh đăng nhập

- SSH: `ssh team1@10.90.0.11` (tương tự team2 `.12`, team3 `.13`) + mật khẩu đội.
- Open GUI (nếu BTC bật): mật khẩu VNC trong `.secrets/gui-access.yml`.
