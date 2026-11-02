# Understand-Anything cho MekoDataCTF

Đã cài Understand-Anything vào `tools/understand-anything` và đăng ký 9 skill cho Codex bằng trình cài đặt PowerShell chính thức. Bản đồ mặc định tại `.ua/` phân tích **toàn bộ workspace atk_def_platform**: website, ForcAD, các lab, checker, provisioning, công cụ, tài liệu và mô hình. Bản đồ riêng của website tại `platform/MekoDataCTF_Website/.ua/` vẫn được giữ.

Nguồn: https://github.com/Egonex-AI/Understand-Anything

Phiên bản skill: **2.9.8**. Commit nguồn đã dùng: `4e6d3299017a7432da15957874992837a315c5b4`.

## 1. Mở dashboard đã tạo

Mở PowerShell tại workspace rồi chạy:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform
powershell -ExecutionPolicy Bypass -File .\tools\start-understand-dashboard.ps1
```

Giữ terminal mở. Truy cập dòng **Dashboard URL** mà terminal in ra, bao gồm cả `?token=...`. Mỗi lần khởi động có thể có token mới. Dashboard chỉ nghe trên `127.0.0.1:5173`. Dừng bằng `Ctrl+C`.

Nếu cổng đang được dùng, mở URL của phiên đang chạy hoặc chọn cổng khác:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-understand-dashboard.ps1 -Port 5174
```

Dashboard chạy độc lập với website Meko ở `http://localhost:3000`; không cần khởi động website để đọc bản đồ. Chọn node để xem mô tả, quan hệ và mã nguồn; dùng tìm kiếm và chế độ tour để đọc theo lộ trình.

Muốn xem lại riêng website, chỉ định thư mục và cổng khác:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-understand-dashboard.ps1 -ProjectPath MekoDataCTF_Website -Port 5174
```

Nếu dashboard báo **working-tree changes** với tệp `.understandignore`, đó là bộ lọc vừa tạo còn chưa commit. Lần phân tích này đã dùng bộ lọc đó; không cần commit chỉ để mở dashboard. Nếu danh sách cảnh báo có mã nguồn khác, chạy lại phân tích trước khi dùng kết quả cho đánh giá tác động.

## 2. Phân tích lại sau khi sửa code

Khởi động lại Codex để nhận các skill vừa cài. Trong chat Codex tại workspace này nhập:

```text
$understand . --language vi
```

Skill dùng bản đồ và fingerprints để cập nhật phần thay đổi. Nếu muốn dựng lại toàn bộ, nhập:

```text
$understand . --full --language vi
```

Mở dashboard bằng skill:

```text
$understand-dashboard .
```

Các dòng bắt đầu bằng `$understand` là lệnh **trong chat Codex**, không dán vào PowerShell. Nếu skill chưa được nhận diện, yêu cầu bằng lời: “Dùng skill understand để phân tích toàn bộ workspace bằng tiếng Việt”.

## 3. Hỏi về mã nguồn

Trong workspace `atk_def_platform`, nhập trong chat:

```text
$understand-chat Giải thích cách website, ForcAD và checker kết nối với nhau
$understand-explain platform/MekoDataCTF_Website/controllers/authController.js
```

Có thể mở `MekoDataCTF_Website` làm workspace con nếu chỉ muốn hỏi bản đồ website. Phân tích bằng AI chạy trong phiên Codex và dùng hạn mức của phiên; dashboard xem bản đồ đã lưu không cần gọi AI.

## 4. Kiểm tra bản đồ

```powershell
node .\tools\verify-understand-graph.mjs
```

Lệnh kiểm tra schema chính thức, độ phủ inventory, đường dẫn và dòng mã nguồn, các quan hệ import, lớp kiến trúc và tour. Nó kiểm tra cấu trúc bản đồ; mô tả nghiệp vụ vẫn cần được đối chiếu khi code thay đổi.

Giới hạn của bộ phân tích: một số định dạng như EJS/CSS/Vue/PowerShell/StarUML không có parser cấu trúc đầy đủ; CommonJS dạng `exports.x = ...` hoặc method trong object cũng có thể chưa được tách đủ. Những phần này được đọc từ nguồn và mô tả ở node tệp; mô hình StarUML được xem như JSON để đọc phần tử và sơ đồ. Bản đồ có đủ tệp thuộc inventory đã chọn, nhưng không phải danh sách đầy đủ mọi hàm. Các tệp nhị phân, credentials, database, runtime và bộ công cụ Understand-Anything đã cài được loại khỏi phân tích; xem `.ua/scope-report.json` để biết độ phủ từng thư mục.

## Dữ liệu và cài lại thư viện

- `.ua/knowledge-graph.json`: bản đồ toàn workspace.
- `.ua/config.json`: ngôn ngữ `vi`; không tự cập nhật qua Git hook.
- `.ua/fingerprints.json` và `.ua/meta.json`: mốc cho lần cập nhật sau.
- `.ua/scope-report.json`: thống kê phạm vi theo thư mục và các nhóm bị loại.
- `.understandignore`: loại credentials, database, dependencies, ảnh/font và dữ liệu sinh tự động khỏi phân tích.
- `platform/MekoDataCTF_Website/.ua/`: bản đồ website riêng từ lần phân tích trước; kiểm tra bằng `node .\tools\verify-understand-graph.mjs MekoDataCTF_Website`.
- Bản checkout công cụ và các tệp tạm được bỏ qua trong Git. Không xóa hoặc di chuyển checkout nếu còn muốn dùng các skill đã liên kết tới nó.

Nếu mất `node_modules`, dùng Node.js >=22 và pnpm >=10 rồi chạy:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform\tools\understand-anything
pnpm install --frozen-lockfile
pnpm --filter @understand-anything/core build
```

Nếu cần đăng ký lại skill từ bản checkout hiện có:

```powershell
cd C:\Users\Admin\Desktop\MekoData_Ky\atk_def_platform
$env:UA_DIR = (Resolve-Path .\tools\understand-anything).Path
& .\tools\understand-anything\install.ps1 codex
```

Trình cài đặt chính thức có thể cập nhật checkout từ GitHub trước khi liên kết skill. Sau khi cập nhật công cụ, chạy lại `pnpm install --frozen-lockfile` và kiểm tra lại bản đồ.
