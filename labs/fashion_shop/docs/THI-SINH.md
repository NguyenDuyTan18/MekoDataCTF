# Hướng dẫn thí sinh · Meko Boutique

**Meko Boutique** là một website thương mại thời trang tiếng Việt. Trong bài lab này, mỗi đội
vận hành một bản cửa hàng riêng và tìm cách khai thác năm nhóm lỗ hổng web trên cửa hàng của
các đội khác, đồng thời vá lỗ hổng trên cửa hàng của mình để bảo vệ flag.

> Tài liệu này **không chứa lời giải**. Mục tiêu là để bạn tự khảo sát ứng dụng.

## Truy cập

- Mỗi đội có một VM Kali riêng. Đăng nhập **SSH bằng mật khẩu** với tài khoản đội (ví dụ `team1`);
  mật khẩu do giảng viên cấp. Có thể mở desktop qua console của nền tảng CyberRangeCZ.
- Website của các đội chạy trên cổng 80:
  - Team 1: `http://10.90.0.11/`
  - Team 2: `http://10.90.0.12/`
  - Team 3: `http://10.90.0.13/`
- Xem thêm `~/lab-addresses.txt` trên VM của bạn.

## Làm quen cửa hàng

1. Mở trang chủ, duyệt danh mục, tìm kiếm và xem chi tiết sản phẩm.
2. **Tạo tài khoản** rồi **đăng nhập**. Mật khẩu tối thiểu 10 ký tự.
3. Thử các chức năng: giỏ hàng, mã giảm giá, đặt hàng, xem lịch sử đơn hàng và hóa đơn.
4. Khám phá: **bộ sưu tập** và ô tìm bộ sưu tập, **bộ sưu tập cá nhân**, **studio phối đồ**
   (tải lên tệp mô tả JSON), khu **hội viên**, và khu **nhân viên** (`/staff/login`).

## Năm nhóm thử thách

Mỗi cửa hàng ẩn **năm flag** dạng `FLAG{...}`, mỗi flag gắn với một nhóm lỗ hổng. Flag **đổi theo
chu kỳ** (mặc định mỗi 120 giây), nên hãy nộp flag mới nhất.

| # | Khu vực nghiệp vụ | Gợi ý khảo sát |
|---|---|---|
| 1 | Tìm kiếm **bộ sưu tập** | Ô lọc bộ sưu tập theo tên xử lý chuỗi nhập vào ra sao? |
| 2 | **Hóa đơn** đơn hàng | Đường dẫn hóa đơn gắn với số đơn. Thử các số đơn khác. |
| 3 | **Studio phối đồ** | Tệp mô tả bộ phối trỏ tới một tệp xem trước. Nội dung trường đường dẫn đi tới đâu? |
| 4 | **Hạng hội viên** | Khu ưu đãi đọc hạng từ thẻ hội viên trong cookie. Thẻ đó được kiểm tra thế nào? |
| 5 | **Bản xuất dữ liệu vận hành** | Có tệp vận hành nào bị để công khai? Xem `robots.txt`. |

## Phòng thủ

- Mã nguồn chạy trên VM của bạn tại `/opt/meko-boutique`. Bạn có thể bật **bản vá** cho từng
  nhóm lỗ hổng (xem hướng dẫn vận hành của giảng viên) để chặn khai thác mà vẫn giữ cho các
  chức năng mua sắm hợp lệ hoạt động bình thường.
- Sau khi vá, hãy tự kiểm tra: đăng ký, mua hàng, xem hóa đơn của **chính mình**, tạo bộ phối
  hợp lệ, và tìm kiếm bộ sưu tập vẫn phải chạy đúng.

## Quy tắc

- Chỉ tấn công các VM trong phạm vi lab. Không tấn công hạ tầng nền tảng hay ra ngoài Internet.
- Các thao tác chỉ nhằm mục đích học tập trong môi trường cô lập.
