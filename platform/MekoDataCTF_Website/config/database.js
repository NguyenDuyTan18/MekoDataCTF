const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const Database = require('better-sqlite3');

const dataDir = path.join(__dirname, '..', 'data');
fs.mkdirSync(dataDir, { recursive: true });

const db = new Database(process.env.DB_FILE || path.join(dataDir, 'mekodata.db'));
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8'));

// Nâng cấp DB cũ: schema.sql chỉ tạo bảng mới, không thêm cột vào bảng đã có.
const columnsOf = (table) => new Set(db.prepare(`PRAGMA table_info(${table})`).all().map((c) => c.name));
const teamColumns = columnsOf('teams');
if (!teamColumns.has('token')) db.exec('ALTER TABLE teams ADD COLUMN token TEXT');
if (!teamColumns.has('forcad_name')) db.exec("ALTER TABLE teams ADD COLUMN forcad_name TEXT NOT NULL DEFAULT ''");
db.exec('CREATE UNIQUE INDEX IF NOT EXISTS teams_token_idx ON teams(token)');

// Tài khoản cá nhân cho mọi thành viên: họ tên/MSSV nằm ở users, members.user_id nối thành viên với tài khoản.
const userColumns = columnsOf('users');
if (!userColumns.has('full_name')) db.exec("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''");
if (!userColumns.has('student_id')) db.exec("ALTER TABLE users ADD COLUMN student_id TEXT NOT NULL DEFAULT ''");
db.exec("CREATE UNIQUE INDEX IF NOT EXISTS users_student_idx ON users(student_id COLLATE NOCASE) WHERE student_id != ''");
if (!columnsOf('members').has('user_id')) {
  db.exec('ALTER TABLE members ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE');
}
// Mỗi tài khoản thuộc tối đa một đội.
db.exec('CREATE UNIQUE INDEX IF NOT EXISTS members_user_idx ON members(user_id) WHERE user_id IS NOT NULL');

// Đội đăng ký theo cách cũ (đội trưởng nhập tay thành viên): nối dòng đội trưởng với tài khoản đội trưởng
// và chép họ tên/MSSV sang tài khoản. Thành viên nhập tay khác giữ user_id NULL cho đến khi tự đăng ký và vào đội.
db.transaction(() => {
  db.exec(`UPDATE members SET user_id = (SELECT t.user_id FROM teams t WHERE t.id = members.team_id)
            WHERE is_leader = 1 AND user_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM members m JOIN teams t ON t.id = members.team_id WHERE m.user_id = t.user_id)`);
  db.exec(`UPDATE OR IGNORE users SET
             full_name  = (SELECT m.full_name  FROM members m WHERE m.user_id = users.id),
             student_id = (SELECT m.student_id FROM members m WHERE m.user_id = users.id)
            WHERE full_name = '' AND student_id = '' AND EXISTS (SELECT 1 FROM members m WHERE m.user_id = users.id)`);
})();

// Đội đăng ký trước khi có token: cấp token ngay để đăng nhập và nộp flag được.
const missing = db.prepare("SELECT id FROM teams WHERE token IS NULL OR token = ''").all();
if (missing.length) {
  const setToken = db.prepare('UPDATE teams SET token = ? WHERE id = ?');
  db.transaction(() => missing.forEach(({ id }) => setToken.run(crypto.randomBytes(8).toString('hex'), id)))();
}

module.exports = db;
