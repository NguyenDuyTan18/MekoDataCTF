// Đồng bộ token đội từ website sang ForcAD bằng tay (logic ở services/forcadSync.js).
// Website đang chạy đã tự đồng bộ khi khởi động, định kỳ và sau mỗi thay đổi đội; script này dùng để
// xem trước kế hoạch hoặc ép đồng bộ ngay khi website không chạy.
//
//   node scripts/sync-forcad-tokens.js            # chỉ xem kế hoạch, không ghi gì
//   node scripts/sync-forcad-tokens.js --apply    # ghi token sang ForcAD
//
// Biến môi trường: FORCAD_URL (mặc định http://127.0.0.1:18080), FORCAD_ADMIN_USER, FORCAD_ADMIN_PASSWORD
// (nếu thiếu thì đọc mục admin trong ../ForcAD-demo/config.yml hoặc FORCAD_CONFIG), DB_FILE (tùy chọn).
require('dotenv').config();
const { syncTokens } = require('../services/forcadSync');

// Đặt exitCode thay vì process.exit(): để kết nối HTTP đóng xong rồi mới thoát
// (gọi process.exit() khi socket còn mở làm Node trên Windows báo lỗi assert của libuv).
syncTokens({ apply: process.argv.includes('--apply') }).then((report) => { process.exitCode = report.code; }, (err) => {
  console.error('Không đồng bộ được:', err.message);
  process.exitCode = 2;
});
