# Phân chia ba phân hệ luận văn — cả ba cùng phát triển backend

Cập nhật: 08/11/2026. Điều chỉnh theo yêu cầu cả ba cùng đóng góp cho dự án và đều có phần backend thực chất. Căn cứ: cấu trúc mã nguồn, docs/LUONG-CAC-FILE.md và docs/MEKO-FORCAD-THAY-DOI.md.

Chia theo miền nghiệp vụ xuyên suốt từ dữ liệu, xử lý backend, API đến giao diện hoặc triển khai liên quan. Cả ba cùng tham gia backend ForcAD. Đây là phương án phân công, không xác nhận tác giả của mã đã có hoặc khẳng định mọi chức năng đề xuất đã được triển khai.

## 1. Ba phân hệ đề xuất

| Người | Phân hệ luận văn | Backend phụ trách chính | Đầu ra liên quan |
|---|---|---|---|
| 1 | Quản lý danh tính, đội thi và vòng đời cuộc thi | Xác thực/phân quyền, dữ liệu đội, đồng bộ token, API quản trị, kiểm tra lệnh điều khiển thi | Đăng ký, quản trị đội/giải và màn hình điều khiển |
| 2 | Tiếp nhận flag, chấm điểm và công bố kết quả | Xác thực flag, xử lý nộp trùng/đồng thời, luật điểm/SLA, truy vấn và API kết quả | Giao diện nộp flag, bảng điểm trực tiếp và thống kê |
| 3 | Điều phối tác vụ, kiểm tra dịch vụ và tích hợp lab | Lịch tick, điều phối put/check/get, RPC/collector, agent/checker, backend dịch vụ lab | Môi trường thi, kết quả kiểm tra dịch vụ và triển khai/khôi phục |

Cả ba đều có logic backend, dữ liệu, giao tiếp API hoặc RPC và kiểm thử riêng. Người 3 sở hữu backend điều phối trong ForcAD cùng backend checker/lab.

## 2. Phạm vi mỗi người

### Người 1 — Quản lý danh tính, đội thi và vòng đời cuộc thi

- Thiết kế dữ liệu người dùng, đội, thành viên, cấu hình và quyền quản trị.
- Backend đăng ký/đăng nhập, phiên, phân quyền, token và thu hồi phiên khi đổi token.
- Ghép danh tính đội, đồng bộ token website → ForcAD và xử lý lỗi đồng bộ.
- API quản trị đội; xác thực lệnh chuẩn bị/bắt đầu/tạm dừng/tiếp tục/kết thúc và điều kiện chuyển trạng thái.
- Giao diện đăng ký, quản trị và điều khiển tương ứng.

Mã liên quan: auth/team/admin, model và middleware tương ứng trong platform/MekoDataCTF_Website/; services/forcadSync.js; API đội/điều khiển tại platform/ForcAD-demo/backend/services/admin/; backend/lib/storage/round_control.py và phần thao tác vòng đời liên quan; giao diện điều khiển ForcAD.

Nghiệm thu: quyền đội trưởng/thành viên/BTC đúng; token cũ bị thu hồi theo thiết kế; ánh xạ đội đúng; lệnh sai quyền hoặc sai trạng thái bị từ chối; lệnh hợp lệ tạo trạng thái mà bộ điều phối thực thi được.

Tên hướng luận văn: Thiết kế và phát triển phân hệ quản lý danh tính, đội thi và vòng đời cuộc thi cho nền tảng Attack–Defense CTF.

### Người 2 — Tiếp nhận flag, chấm điểm và công bố kết quả

- Thiết kế luồng tiếp nhận flag và dữ liệu phục vụ điểm/kết quả.
- Kiểm tra token, chủ sở hữu, tuổi flag, nộp trùng và nộp đồng thời.
- Tùy biến luật điểm tấn công, phòng thủ, first-blood, SLA và chuẩn hóa; phân biệt rõ phần kế thừa.
- API kết quả công khai, lọc dữ liệu, cache và truyền trạng thái trực tiếp tới website.
- Backend chuyển tiếp nộp flag lấy danh tính từ phiên; giao diện bảng điểm/nộp flag.

Mã liên quan: platform/ForcAD-demo/backend/lib/flags/, backend/services/http_receiver/, backend/lib/storage/attacks.py, phần chấm điểm trong backend/lib/storage/round1.py, API kết quả trong backend/services/api/; services/arenaService.js, routes/scoreboard.js và giao diện scoreboard của website.

Nghiệm thu: bộ dữ liệu tính tay khớp điểm; nộp trùng/đồng thời không cộng ngoài luật; flag của chính đội hoặc quá hạn được xử lý đúng; bảng điểm khớp backend; dữ liệu công khai không chứa flag/token riêng; thử được mất kết nối và khôi phục cập nhật.

Tên hướng luận văn: Thiết kế và phát triển phân hệ tiếp nhận flag, chấm điểm tự động và công bố kết quả cho nền tảng Attack–Defense CTF.

### Người 3 — Điều phối tác vụ, kiểm tra dịch vụ và tích hợp lab

- Thiết kế backend lịch tick và điều phối đặt/kiểm tra/đọc flag theo trạng thái điều khiển của người 1.
- Xử lý timeout, kết quả kiểm tra, pause/resume và phục hồi khi tiến trình lỗi.
- Adapter RPC, collector SSH và agent/checker nghiệp vụ trên VM.
- Tích hợp backend lab: nhận/lưu flag, locator, dữ liệu từng đội và kiểm tra tính toàn vẹn.
- Topology/provisioning, đóng gói, triển khai và khôi phục một lab chính meko_boutique.
- Hoàn thiện thử thách hiện có và kiểm chứng bản vá trong phạm vi đã chốt; ghi rõ app/checker kế thừa.

Mã liên quan: platform/ForcAD-demo/backend/services/ticker/, backend/lib/storage/round_schedule.py, phần điều phối trong backend/lib/storage/round1.py, checkers/meko_boutique/, collect_checker.py, shared/labconfig.py; app/checker và provisioning tại labs/meko_boutique/.

Nghiệm thu: put/check/get đủ chu trình; flag lưu/đọc đúng đội và locator; lịch tick và pause/resume khớp đặc tả; phân biệt lỗi dịch vụ với lỗi checker/cầu nối; bản vá giữ chức năng hợp lệ; dựng và khôi phục được môi trường ba đội. Báo cáo riêng kiểm thử local và nghiệm thu CyberRange thực tế.

Tên hướng luận văn: Thiết kế và phát triển phân hệ điều phối tác vụ, kiểm tra dịch vụ và tích hợp môi trường thực hành cho nền tảng Attack–Defense CTF.

## 3. Backend dùng chung và ranh giới tích hợp

Một số file hiện chứa nhiều miền nghiệp vụ. Phân công theo hàm/luồng xử lý và phối hợp khi sửa file chung; chỉ tách module khi thực sự cần và có kiểm thử phù hợp.

| Điểm giao | Trách nhiệm |
|---|---|
| Điều khiển thi | Người 1 xác thực lệnh/quản lý trạng thái; người 3 thực thi lịch/tác vụ; người 2 áp dụng cửa sổ nhận flag và truy vấn kết quả tương ứng |
| round1.py | Người 1: thao tác vòng đời liên quan; người 2: scores(), record_attack(), luật SLA; người 3: pump(), schedule_puts(), verify(), kết quả checker |
| Danh tính/token | Người 1 cấp/ghép/đồng bộ; người 2 kiểm tra khi nhận flag; người 3 dùng ánh xạ đội/task để gọi đúng dịch vụ |
| SLA | Người 3 cung cấp kết quả đội/task/tick; người 2 quy đổi thành điểm; cả hai kiểm thử lỗi |
| Cấu hình lab | Người 3 quản lý lab.json và loader; người 1 cung cấp danh sách/ánh xạ đội; người 2 xác định dữ liệu task cần chấm |
| Schema chung | Mỗi người thiết kế dữ liệu thuộc miền mình; cả ba kiểm tra tương thích trước khi đổi schema và hợp nhất |

Bảng này là phân công đề xuất, không mô tả các hàm hiện có như thể đã được tách riêng.

## 4. Tiêu chí công bằng

Áp dụng cùng thang 100 điểm đánh giá đóng góp cho mỗi người:

| Tiêu chí | Trọng số | Bằng chứng |
|---|---:|---|
| Phân tích và thiết kế backend/dữ liệu | 20 | Yêu cầu, sơ đồ, dữ liệu và quyết định kỹ thuật |
| Logic backend tự xây dựng/tùy biến và tích hợp | 35 | Diff, nghiệp vụ, giao tiếp và xử lý lỗi |
| Kiểm thử và đánh giá thực nghiệm | 25 | Ca thành công, ca lỗi, tính đúng và số đo phù hợp |
| Tài liệu và khả năng tái lập | 10 | Hướng dẫn chạy, cấu hình mẫu và xử lý sự cố |
| Demo cá nhân và tích hợp chung | 10 | Demo luồng sở hữu, giải thích backend và kiểm tra đầu nối |

1. Mỗi người phải có thiết kế dữ liệu, logic backend, API/RPC, xử lý lỗi, kiểm thử và phần báo cáo do mình thực hiện.
2. Ưu tiên backend cốt lõi trước khi mở rộng giao diện hoặc thêm lab. Không yêu cầu người 3 viết lại mọi lab hay người 2 viết lại ForcAD.
3. Ước lượng giờ theo đầu việc, rà soát hằng tuần. Nếu tổng công sức dự báo lệch trên 15% so với trung bình nhóm, chuyển gói việc có đầu ra rõ ràng hoặc giảm phạm vi tương ứng.
4. Nếu lab/provisioning làm người 3 quá tải, giao một số gói hoàn thiện thử thách cho người 1/2 và ghi đúng tác giả; người 3 vẫn sở hữu backend điều phối/checker.
5. Cả ba cùng duyệt dữ liệu và hợp đồng giao tiếp, kiểm thử tích hợp và chạy demo chung. Mỗi gói việc có người phụ trách chính và bằng chứng; đóng góp chung cần mô tả cụ thể.
6. Với phần đã hoàn thành, đối chiếu lịch sử và sản phẩm thực tế; không phân lại tác giả để cân bằng hình thức. Không lấy số dòng code, số commit hoặc số trang làm thước đo chính.

## 5. Demo cá nhân và demo chung

| Người | Demo riêng |
|---|---|
| 1 | Tạo/ghép đội → phân quyền → đổi token → đồng bộ → điều khiển thi và kiểm tra quyền/trạng thái |
| 2 | Nộp flag đúng/lặp/quá hạn → nộp đồng thời → đối chiếu điểm tính tay → xem kết quả trực tiếp |
| 3 | Dựng lab → đặt/kiểm tra/đọc flag → tạo lỗi dịch vụ/checker → kiểm tra kết quả → khôi phục và tiếp tục lịch thi |

Demo chung dùng một phiên thi ba đội qua website → engine → checker → lab → kết quả. Mỗi người bàn giao mã đóng góp, thiết kế, kết quả kiểm thử, hướng dẫn chạy và phần báo cáo riêng.

Chưa có số giờ hoặc năng lực từng thành viên để kết luận khối lượng thực tế ngang nhau; tiêu chí trên là cơ chế đo và điều chỉnh khi thực hiện.
