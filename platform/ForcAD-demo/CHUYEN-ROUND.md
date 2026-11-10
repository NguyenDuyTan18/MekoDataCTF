# Chuyển round / đổi lab — Runbook

Hệ thống vốn **đa lab**: lifecycle `MekodataRound1` chạy bất kỳ lab nào khai trong
[`backend/lib/storage/lab_profile.py`](backend/lib/storage/lab_profile.py). "Chuyển round" =
**archive lab đang chạy → prepare lab mới → start**. Không cần sửa engine.

## Công cụ

Chuyển round chạy **qua HTTP admin API — KHÔNG cần docker**. Script chạy trên host bằng
Python chuẩn (không cần cài gói).

- [`switch_round.py`](switch_round.py) — orchestrator 1 lệnh qua HTTP:
  `login → (stop) → archive → prepare(lab) → (start)`. Mặc định **DRY-RUN**; đọc creds admin từ
  `config.yml`; gốc mặc định `http://127.0.0.1:18080` (đổi bằng `--base`).
- [`CHUYEN-ROUND.bat`](CHUYEN-ROUND.bat) — wrapper 1-click (gọi DRY-RUN, in lệnh thực hiện thật).

> Vì sao không dùng docker nữa: backend chạy trong container, nhưng nó đã **mở sẵn HTTP admin
> API** ra cổng 18080. Script chỉ cần `login` lấy cookie `session` + gửi header `Origin` là gọi
> được các endpoint `round-control` / `round1/archive` / `round1/prepare` từ host.

## Chuyển round

> ⚠️ Điểm của round hiện tại được **lưu hồ sơ (archive)** trước; lab mới bắt đầu từ **0 điểm**.

1. **Xem kế hoạch (DRY-RUN, an toàn):**
   ```
   CHUYEN-ROUND.bat round1
   ```
   hoặc trực tiếp:
   ```
   python switch_round.py --to round1
   ```
2. **Thực hiện thật (tự dừng + chuyển + bật):**
   ```
   python switch_round.py --to round1 --yes --stop --start
   ```
   - `--stop`: tự dừng round đang chạy rồi **chờ checker xong** (tự poll tới khi phase `paused`).
   - `--start`: bật round mới luôn (bỏ đi nếu muốn bật sau bằng `BAT-ROUND.bat`).
   - `--base http://IP:PORT`: nếu admin không ở `127.0.0.1:18080`.
3. **Bật collector cho lab mới**: sửa `MEKO_LAB=<lab_moi>` trong `BAT-FLAG.bat` rồi chạy.
   (Collector phải khớp lab, nếu không PUT sẽ 110 — xem flag không sinh.)

Kiểm chứng: `/tick-status/` (cổng 18080) đổi sang task/đội của lab mới, điểm về 0 và tăng lại.

## "Chỉ cần đưa key SSH vào là chạy" — mô hình deploy

Chuỗi SSH: `local → pool gateway → man (ansible) → teamN`. Toàn bộ "danh tính pool" gói trong
**`ops/<pool>/management-config` + key + known-hosts**. Mọi thứ khác bake sẵn trong repo.

| Bake sẵn 1 lần (commit) | Thay đổi mỗi lần deploy |
|---|---|
| Service lab, checker, playbook ansible, entry `lab_profile`, `lab.json` | **Chỉ `ops/<pool>/` (config + key + known-hosts)** |
| Scoring (dùng chung) | (tuỳ chọn) biến `MEKO_SSH_CONFIG` để trỏ config khác |

Mỗi lab khai đường SSH trong `labs/<lab>/lab.json` (`"ssh_config": "ops/<pool>/management-config"`);
`labconfig.load()` đọc nó, `MEKO_SSH_CONFIG` ghi đè nếu cần. Vì vậy quy trình đưa pool mới vào:

1. **Thả `ops/<pool>/`** (management-config + key + known-hosts) do nền tảng cấp.
2. **Provision service lên VM**: `ansible-playbook` của lab (xem `labs/<lab>/sandbox/provisioning/`).
3. **Chuyển round** (4 bước ở trên).
4. **Bật collector** `MEKO_LAB=<lab>`.

### Quy ước đề xuất cho Round 2 (khi đã chốt nội dung)

- Lab round 2 đặt tên cố định (vd `round2`) trong `lab_profile.PROFILES`, `create_teams: true`
  (tự tạo đội từ IP, không cần seed trước).
- `lab.json` của nó trỏ `"ssh_config": "ops/pool-r2/management-config"` — **đưa key đúng thư mục
  đó là chạy**, không phải sửa code.
- Khi đó: `CHUYEN-ROUND.bat round2` → `... --to round2 --yes --start`.

## Ghi chú kỹ thuật

- `prepare(lab)` tự gọi `leave_archived_lab(lab)`: xoá điểm cuộc thi đã archive của lab cũ
  (snapshot vẫn giữ trong bảng `MekodataArchives`), đặt `real_round=0`, dựng teams/tasks lab mới.
- Không có chặn cứng nào cho việc đổi lab. Dòng "Round 2 chưa triển khai" trong
  `round_control.set_enabled` chỉ chặn khi *bật* một round đã `finished` mà **chưa** archive —
  luồng archive→prepare đi vòng qua nó một cách hợp lệ.
- Tải hồ sơ đã lưu: admin API `GET /api/admin/round1/archive/<archive_id>` (hoặc bảng `MekodataArchives`).
