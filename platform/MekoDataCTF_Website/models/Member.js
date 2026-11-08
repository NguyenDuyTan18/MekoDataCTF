const db = require('../config/database');

const Member = {
  listByTeam(teamId) {
    return db
      .prepare('SELECT * FROM members WHERE team_id = ? ORDER BY position, id')
      .all(teamId);
  },

  findById(id) {
    return db.prepare('SELECT * FROM members WHERE id = ?').get(id);
  },

  findByUser(userId) {
    return db.prepare('SELECT * FROM members WHERE user_id = ?').get(userId);
  },

  findByStudentId(studentId) {
    return db.prepare('SELECT * FROM members WHERE student_id = ? COLLATE NOCASE').get(studentId);
  },

  countByTeam(teamId) {
    return db.prepare('SELECT COUNT(*) AS n FROM members WHERE team_id = ?').get(teamId).n;
  },

  // Thêm tài khoản vào đội. Nếu đội trưởng đã nhập tay người này (cùng MSSV, chưa có tài khoản) thì nhận lại dòng đó.
  addUser(teamId, user, isLeader = false) {
    const legacy = this.findByStudentId(user.student_id);
    if (legacy && legacy.user_id === null && legacy.team_id === teamId) {
      db.prepare('UPDATE members SET user_id = ?, full_name = ?, is_leader = ? WHERE id = ?')
        .run(user.id, user.full_name, isLeader ? 1 : legacy.is_leader, legacy.id);
      return legacy.id;
    }
    const { pos } = db.prepare('SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM members WHERE team_id = ?').get(teamId);
    return db
      .prepare('INSERT INTO members (team_id, user_id, full_name, student_id, is_leader, position) VALUES (?, ?, ?, ?, ?, ?)')
      .run(teamId, user.id, user.full_name, user.student_id, isLeader ? 1 : 0, pos).lastInsertRowid;
  },

  remove(id) {
    db.prepare('DELETE FROM members WHERE id = ?').run(id);
  },

  count() {
    return db.prepare('SELECT COUNT(*) AS n FROM members').get().n;
  },
};

module.exports = Member;
