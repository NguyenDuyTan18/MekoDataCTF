# Đồng bộ token đội: Website → ForcAD

## Tóm tắt

- Mỗi đội có **một token** 16 ký tự. Thành viên dùng token để đăng nhập website, còn website dùng token để nộp flag sang ForcAD.
- **Website là nơi cấp token.** ForcAD phải lưu đúng token đó thì mới cộng điểm. Nếu lệch, ForcAD từ chối mọi flag của đội.
- Từ 02/11/2026, website **tự đồng bộ**. BTC không cần chạy lệnh tay, chỉ cần website đang chạy và đọc được tài khoản admin ForcAD (xem mục 3).

---

## 1. Khi nào website tự đồng bộ

| Sự kiện | Đồng bộ lúc nào |
|---|---|
| Website khởi động | Ngay lập tức |
| Định kỳ | Mỗi 60 giây (`FORCAD_SYNC_INTERVAL`) |
| Đội trưởng **tạo đội** (đội có token mới) | Ngay sau khi lưu |
| Đội trưởng **đổi tên đội** (tên ForcAD theo slug có thể đổi) | Ngay sau khi lưu |
| BTC bấm **Cấp token mới** | Ngay. Trang chờ đồng bộ xong mới tải lại |
| BTC sửa **"Tên đội trên ForcAD"** | Ngay. Trang chờ đồng bộ xong mới tải lại |
| **`recycle.py`** tái tạo lab (ForcAD sinh lại token cho mọi đội) | Ngay cuối script, kèm lượt định kỳ làm dự phòng |
| BTC **thêm đội trên ForcAD**, hoặc **dựng ForcAD mới** từ đầu | Ở lượt định kỳ tiếp theo, tối đa 60 giây |
| Bấm **"Bắt đầu lại từ tick 0"** trên dashboard | Không cần, vì token giữ nguyên |

Mỗi lượt chỉ ghi những đội **đang lệch** token. Đội đã khớp thì không bị đụng tới.

---

## 2. Website ghép đội với ForcAD thế nào

Với mỗi đội website, ForcAD được dò theo thứ tự sau và lấy tên đầu tiên khớp:

1. **"Tên đội trên ForcAD"** do BTC khai ở trang quản trị đội. Nếu đã khai thì chỉ dùng tên này.
2. **Slug** của tên đội: bỏ dấu, chữ thường, chỉ giữ `a-z 0-9 -`. Ví dụ "Hà Nội #1" thành `ha-noi-1`. Đây cũng là tên máy ảo trong lab.
3. **Tên gốc** của đội.

Website sẽ **không ghi** token và báo lỗi trong các trường hợp:
- không tìm thấy đội ForcAD nào khớp;
- đội ForcAD đó đã ghép với một đội website khác;
- token đang thuộc một đội ForcAD khác.

Đội ForcAD không ghép với đội website nào thì giữ nguyên token của nó.

Các bước ghi token, ở mức kỹ thuật:
1. Đăng nhập `POST /api/admin/login/`.
2. Lấy danh sách đội qua `GET /api/admin/teams/`.
3. Với mỗi đội lệch token, gọi `PUT /api/admin/teams/<id>/`, giữ nguyên tên, IP và trạng thái, chỉ đổi `token`.
4. ForcAD (`update_team` trong `backend/lib/storage/teams.py`) xóa token cũ khỏi Redis, nên token cũ **mất hiệu lực ngay**, rồi ghi token mới.

---

## 3. Cấu hình

Website cần tài khoản admin ForcAD. Có hai cách cung cấp:

- **Mặc định, không cần làm gì:** website tự đọc mục `admin:` trong `platform/ForcAD-demo/config.yml`. Mật khẩu không bị chép sang file khác.
- **Khai rõ** trong `platform/MekoDataCTF_Website/.env`. Dùng cách này khi ForcAD chạy ở máy khác hoặc thư mục khác:

```ini
FORCAD_URL=http://127.0.0.1:18080
FORCAD_ADMIN_USER=forcad
FORCAD_ADMIN_PASSWORD=<admin.password trong config.yml của ForcAD>
# FORCAD_CONFIG=../ForcAD-demo/config.yml   # hoặc chỉ đường dẫn tới config.yml
FORCAD_SYNC_INTERVAL=60                      # giây; 0 = tắt lượt định kỳ
```

Nếu không có mật khẩu, website vẫn chạy bình thường nhưng tắt đồng bộ. Log khởi động sẽ báo `[forcad-sync] Tắt: …`.

---

## 4. Xem trạng thái

- **Trang quản trị → chi tiết đội → mục "Đồng bộ token ForcAD":**
  - ✓ xanh: token đã khớp, hoặc vừa được ghi.
  - ✗ đỏ: chưa ghép được. Dòng này kèm lý do và tên đội ForcAD cần có.
  - Có hiện thời điểm của lượt đồng bộ gần nhất.
- **Log của website:** dòng `[forcad-sync] (<lý do>)` chỉ in khi kết quả thay đổi, nên log không bị đầy.
- **Form nộp flag trên World Arena:** nếu đội chưa ghép được, form hiện cảnh báo đỏ.

---

## 5. Chạy tay (không bắt buộc)

Dùng khi website không chạy, hoặc khi muốn xem trước kế hoạch:

```powershell
cd platform/MekoDataCTF_Website
npm run sync:forcad               # chỉ xem, không ghi gì
npm run sync:forcad -- --apply    # ghi ngay
```

Mã thoát của lệnh:
- `0`: mọi đội đều ổn.
- `1`: có đội chưa ghép được (vẫn ghi cho các đội còn lại).
- `2`: không kết nối hoặc không đăng nhập được ForcAD.

---

## 6. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Đội nộp flag bị ForcAD từ chối, trang đội báo ✗ "Chưa có đội ForcAD tên …" | Tên đội website không khớp đội nào trên ForcAD | Khai "Tên đội trên ForcAD" (ví dụ `team01`), hoặc tạo đội ForcAD đúng tên slug |
| ✗ "Đội ForcAD đã ghép với đội website khác" | Hai đội website trỏ cùng một đội ForcAD | Sửa "Tên đội trên ForcAD" của một trong hai đội |
| ✗ "Token đang thuộc đội ForcAD khác" | Trước đó token bị gán nhầm cho đội khác trên ForcAD | Bấm Cấp token mới cho đội website đó |
| Trang báo "Lỗi kết nối ForcAD" | ForcAD tắt, sai `FORCAD_URL`, hoặc sai mật khẩu | Bật ForcAD, kiểm tra `.env` hoặc `config.yml`. Lượt sau sẽ tự sửa |
| "Chưa đồng bộ lần nào" | Website không đọc được tài khoản admin | Xem mục 3 |
| Sau `recycle.py`, các đội bị từ chối trong vài giây | ForcAD vừa sinh token mới | Script tự đồng bộ ngay; nếu không có `node` thì lượt định kỳ sẽ sửa |

---

## 7. Mã nguồn liên quan

| File | Vai trò |
|---|---|
| `platform/MekoDataCTF_Website/services/forcadSync.js` | Logic đồng bộ: `syncTokens`, `requestSync` (gọi sau thay đổi), `start` (khởi động và định kỳ), `statusOf` (trạng thái cho trang quản trị) |
| `scripts/sync-forcad-tokens.js` | Lệnh chạy tay, dùng lại service trên |
| `app.js` | Gọi `forcadSync.start()` khi website lắng nghe |
| `controllers/teamController.js`, `controllers/adminController.js` | Gọi `requestSync` sau khi tạo/sửa đội, cấp token, đổi tên ForcAD |
| `views/admin/team.ejs`, `public/css/admin.css`, `locales/*.json` | Hiển thị trạng thái đồng bộ |
| `models/Team.js` | `slugOf`, `forcadNameOf`, `forcadCandidates`: quy tắc ghép tên |
| `labs/round1/service/recycle.py` | `sync_website_tokens()`: đồng bộ ngay sau khi tái tạo |
| `platform/ForcAD-demo/backend/lib/storage/teams.py` | `update_team`: thu hồi token cũ trong Redis |

Việc chưa tự động: **xóa đội trên website** không xóa token ở ForcAD. Đội ForcAD đó vẫn giữ token cũ cho tới khi BTC tắt hoặc sửa đội trên ForcAD.
