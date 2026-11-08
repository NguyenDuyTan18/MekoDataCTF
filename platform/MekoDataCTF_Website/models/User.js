const bcrypt = require('bcryptjs');
const db = require('../config/database');

const User = {
  findById(id) {
    return db.prepare('SELECT id, email, role, full_name, student_id, created_at FROM users WHERE id = ?').get(id);
  },

  findByEmail(email) {
    return db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  },

  create({ email, password, role = 'contestant', fullName = '', studentId = '' }) {
    const hash = bcrypt.hashSync(password, 10);
    const info = db
      .prepare('INSERT INTO users (email, password_hash, role, full_name, student_id) VALUES (?, ?, ?, ?, ?)')
      .run(email, hash, role, fullName, studentId);
    return this.findById(info.lastInsertRowid);
  },

  setPassword(id, password) {
    db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(bcrypt.hashSync(password, 10), id);
  },

  setProfile(id, { fullName, studentId }) {
    db.prepare('UPDATE users SET full_name = ?, student_id = ? WHERE id = ?').run(fullName, studentId, id);
  },

  verifyPassword(user, password) {
    return bcrypt.compareSync(password, user.password_hash);
  },

  // MSSV đã có tài khoản khác dùng. Thành viên do đội trưởng nhập tay (chưa có tài khoản) vẫn đăng ký được;
  // khi vào đúng đội đó, dòng cũ được nhận lại (Member.addUser).
  isStudentIdTaken(studentId) {
    return !!db.prepare('SELECT 1 FROM users WHERE student_id = ? COLLATE NOCASE').get(studentId);
  },

  countContestants() {
    return db.prepare("SELECT COUNT(*) AS n FROM users WHERE role = 'contestant'").get().n;
  },
};

module.exports = User;
