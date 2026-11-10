# Vòng 2 · Crypto AD

Ba dịch vụ nhận JSON qua TCP, mỗi yêu cầu trên một dòng.

| Challenge | Cổng | Chủ đề |
| --- | ---: | --- |
| Curveball | 9011 | Xác thực tham số đường cong P-256 |
| Padding Oracle | 9012 | Xử lý lỗi khi giải mã AES-CBC |
| ECDSA Nonce | 9013 | Sử dụng nonce khi ký ECDSA |

Trên VM đội, đọc `~/crypto-lab/host_port.txt` để chọn đối thủ. Ví dụ, từ `team1` kết nối Curveball của `team2`.

```bash
nc 10.90.0.12 9011
```

Gửi `{"op":"info"}` để xem các thao tác của dịch vụ và `{"op":"targets"}` để xem các bản ghi đã được đặt flag. Danh sách ban đầu trống khi dịch vụ mới khởi động. Chờ BTC mở vòng 2 và nộp flag qua scoreboard do BTC cung cấp.

Source trên VM nằm ở `/opt/meko-crypto/`. Sau khi vá trên VM đội mình, khởi động lại đúng dịch vụ. Ví dụ, `sudo systemctl restart meko-crypto@curveball.service`.
