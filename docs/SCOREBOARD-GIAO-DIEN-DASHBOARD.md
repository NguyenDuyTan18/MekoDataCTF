# Đổi giao diện `/scoreboard` sang dashboard

Ngày 05/11/2026, trang `/scoreboard` đổi từ bản đồ World Arena sang giao diện dashboard tàu vũ trụ, lấy từ `crypto-lab/dashboard` của repo [louisnguyen2005/atk_def_platform](https://github.com/louisnguyen2005/atk_def_platform).

Chỉ giao diện thay đổi. Dữ liệu vẫn lấy từ ForcAD, nộp flag và đăng nhập đội giữ nguyên.

## 1. Phần giữ nguyên

| Phần | Vị trí |
|---|---|
| Gom dữ liệu ForcAD, cache, SSE, ETag | `services/arenaService.js` |
| API `/scoreboard/stream`, `/state`, `/data/*`, `/submit` | `routes/scoreboard.js` |
| Lấy dữ liệu trên trình duyệt, tự chuyển sang AJAX khi SSE lỗi | `public/js/arena.js` |
| Ghép đội với ForcAD, token theo phiên đăng nhập, CSRF | `middlewares/`, `models/Team.js` |
| Đồng bộ token website sang ForcAD | `services/forcadSync.js` |

Trang này không dùng controller crypto ở cổng 8088.

## 2. Phần đã thay đổi

Đường dẫn tính từ `platform/MekoDataCTF_Website/`.

| File | Thay đổi |
|---|---|
| `views/scoreboard.ejs` | Viết lại theo bố cục dashboard, không dùng layout chung của website |
| `routes/scoreboard.js` | Thêm `layout:false` khi render |
| `public/arena-ui/` (mới) | CSS, sân đấu 3D và 2D, Three.js, ảnh; lấy từ repo gốc và chỉnh như mục 3 |
| `public/arena-ui/scoreboard.css` (mới) | Bảng service theo số service của lab, 4 thẻ luật điểm, khung nhật ký |
| `public/js/scoreboard-ui.js` (mới) | Thay `world.js`: nhật ký, trạng thái service, form nộp flag, đổi dữ liệu ForcAD thành sự kiện cho sân đấu |
| `public/js/arena.js` | Chỉ đổi phần hiển thị: thứ tự cột, kiểu ô bảng điểm, đồng hồ `--:--` khi không chạy, tick dạng `T4/10` |
| `app.js` | Tắt `upgrade-insecure-requests` khi không chạy production |

**Lý do sửa `app.js`:** khi mở bằng IP LAN qua HTTP, chỉ thị này buộc trình duyệt tải CSS và JS bằng HTTPS, nên trang mất toàn bộ giao diện. Production vẫn giữ chỉ thị này.

## 3. Chỉnh sửa trong code lấy từ repo gốc

- Đổi đường dẫn asset từ `/crypto/assets/` sang `/arena-ui/`.
- Tên lỗ hổng trong `TASK_LABEL` đổi sang của Meko Boutique. Lab khác hiện tên service gốc.
- Khiên nhận chữ hiển thị từ sự kiện: `chặn flag` hoặc `giữ dịch vụ`.
- Màu tên đội trong feed gán bằng JavaScript, vì CSP của website chặn `style="..."` trong HTML.

## 4. Sân đấu dùng dữ liệu ForcAD thế nào

| Dữ liệu ForcAD | Hiệu ứng |
|---|---|
| Capture mới | Tàu tấn công bắn tàu bị chiếm flag, hiện `+1 ATK` và `−1 DEF` |
| Điểm SLA của đội tăng | Bật khiên, hiện chênh lệch SLA thật |
| Flag bị chặn (`defends`) | Bật khiên đội bị nhắm, hiện `BLOCKED` |

Tab đang ẩn chỉ ghi nhận sự kiện, không diễn bù. Mỗi lần cập nhật diễn tối đa 12 đòn (`MAX_FX`).

Sân đấu sắp xếp đội bằng `localeCompare`, nên `scoreboard-ui.js` đổi id đội của ForcAD sang chuỗi.

## 5. Khác với giao diện cũ và dashboard gốc

- **Đã bỏ khỏi trang:** navbar website, bản đồ và 12 con giáp, nút tắt hiệu ứng động.
- **Đã bỏ so với dashboard gốc:** khung Organizer, form nhập token, thẻ "Ba bài crypto".
- **Thêm so với dashboard gốc:** 4 thẻ luật điểm, "Nhật ký chiến trường", "Checker chronicle".

`public/js/world.js`, `public/css/world.css` và `public/css/arena.css` không còn được dùng, nhưng chưa xóa. Muốn quay về giao diện cũ thì khôi phục `views/scoreboard.ejs`, `routes/scoreboard.js` và `public/js/arena.js` từ git.

## 6. Trạng thái kiểm chứng

Đã chạy ngày 05/11/2026 trên bản website riêng, với ForcAD giả và database tạm:

| Tình huống | Kết quả |
|---|---|
| Bảng điểm, tick, đồng hồ, 5 service | Đạt |
| Capture mới làm tàu bắn, nhật ký và điểm cập nhật | Đạt |
| Nộp flag, ForcAD giả nhận đúng token của đội đăng nhập | Đạt |
| Cảnh báo đội chưa ghép | Đạt |
| Chưa đăng nhập: có nút đăng nhập, không có form | Đạt |
| ForcAD ngừng phản hồi: báo mất kết nối, giữ bảng điểm | Đạt |
| Sân đấu 3D, sân đấu 2D (`?arena=2d`) | Có hiển thị; 2D chỉ thử với dữ liệu mẫu của dashboard gốc, trước khi nối ForcAD |
| Mở bằng IP LAN trên cùng máy | Đạt, thử trước khi nối ForcAD |
| ForcAD thật | **Chưa chạy** |
| Mở từ máy khác trong LAN | **Chưa chạy**; có thể phải mở cổng 3000 trên tường lửa |

## 7. Vấn đề còn lại

1. **Thẻ luật điểm ghi ±100 nhưng điểm thật là ±1.** `record_attack` trong `round1.py` cộng +1/−1 và SLA +1. Chữ 100 đến từ `RULES`, có từ giao diện cũ và chỉ là chú giải. Sân đấu và bảng điểm hiện điểm thật. Cần chốt sửa `RULES` hay sửa backend (xem `adjust_settings.md` mục 8.3).
2. **Tên đội chưa khớp lab.** Website có `hehe`, `team04`, `team1`; `labs/meko_boutique/lab.json` có `team1`, `team2`, `team3`. Chỉ `team1` ghép được. Sửa bằng cách điền "Tên đội trên ForcAD" hoặc tạo đội đúng tên. Token chưa đồng bộ vì Docker đang tắt lúc ghi tài liệu này.
3. **Xếp hạng trên sân đấu không có đồng hạng.** Nhãn trên tàu luôn là #1, #2, #3 khi các đội bằng điểm; bảng điểm vẫn đồng hạng đúng.
4. **Dòng EXPIRED màu xanh.** Kết quả nộp flag dùng chung một màu cho mọi trạng thái.
5. **Cảnh báo Three.js về tọa độ NaN.** Console có `computeBoundingSphere(): Computed radius is NaN`. Chưa tìm ra nguồn, chưa thấy ảnh hưởng đến hình.
