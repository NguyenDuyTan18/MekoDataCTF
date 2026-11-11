# Mô hình SLA mới — sub-check liên tục (CyberRangeCZ-style)

## Vì sao đổi

**Trước:** ForcAD chỉ check **1 lần/tick** (cuối tick). Service có thể DOWN gần hết tick nhưng nếu
đúng khoảnh khắc check nó UP thì vẫn **ăn trọn SLA** — không công bằng, ngược với CyberRangeCZ.

**Sau (mô hình CyberRangeCZ):** trong mỗi tick (vẫn 5 phút) có các **sub-check mỗi ~30s**
(`probe_seconds`). Chỉ cần **1 sub-check DOWN** trong tick là **mất TOÀN BỘ SLA của tick đó**.

## Cơ chế

- `lab_profile`: thêm `probe_seconds` (mặc định **30** cho cả round1 và meko_boutique).
- Bảng `MekodataTickHealth(team_id, tick, probes, downs, last_status)` — theo dõi cả tick.
- Trong phase `running` ([competition.py](backend/lib/storage/competition.py) `pump`): mỗi `probe_seconds`
  chạy `run_health_probes()` = **full `check()` chức năng** cho mọi (đội × task). Đội nào có task
  không UP → cộng 1 `downs` cho `(đội, tick)`.
- Cuối tick (phase `checking`): `points = 1` **chỉ khi** lần check cuối UP **và** `downs = 0`.
  Bất kỳ `downs > 0` → **SLA tick = 0**.
- Chỉ ảnh hưởng **SLA/defense**, không đụng attack. Bảng mới nằm trong reset (`_clear_scores`)
  và snapshot archive.

> Sub-check dùng `check()` (chức năng: đăng ký, đặt hàng, tìm kiếm…), **không** GET flag — vì đầu
> tick flag chưa chắc đã đặt. Bắt được cả lỗi chức năng do vá hỏng, không chỉ service chết.

## Kích hoạt

Code mount vào container; đã **restart `forcad-demo-ticker-1`** → `ensure_schema` tạo bảng/cột mới.
Probe **tự chạy khi round ở phase `running`** (prepare + start một round là có). Lúc viết, cuộc thi
đang `archived` nên probe chưa chạy; vòng tiếp theo sẽ kích hoạt.

## Tinh chỉnh

- Đổi nhịp probe: sửa `probe_seconds` trong `lab_profile.py` (vd 25) rồi restart ticker.
- **Tải SSH:** mỗi probe chạy `len(teams) × len(tasks)` lần `check()` qua collector/SSH (meko =
  3×5 = 15) mỗi ~30s. Nếu nặng/chậm hơn `probe_seconds`, probe sẽ giãn ra tự nhiên (pump đơn
  luồng, đặt mốc trước khi probe). Muốn nhẹ hơn: tăng `probe_seconds` hoặc đổi probe sang chỉ gọi
  `/health` (sửa `health_probe`).
- **Collector phải đang chạy** (BAT-FLAG.bat), nếu không mọi probe sẽ DOWN (110) và mọi đội mất SLA.
