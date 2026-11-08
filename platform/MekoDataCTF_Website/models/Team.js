const crypto = require('crypto');
const db = require('../config/database');
const Member = require('./Member');

// Cùng định dạng token đội của ForcAD (secrets.token_hex(8)) để đẩy sang ForcAD được nguyên trạng.
const TOKEN_RE = /^[0-9a-f]{16}$/;
const newToken = () => crypto.randomBytes(8).toString('hex');

const Team = {
  TOKEN_RE,

  // Vào đội bằng token đội (64 bit ngẫu nhiên; chống dò bằng giới hạn số lần thử ở teamController.join).
  findByToken(token) {
    const value = String(token || '').trim().toLowerCase();
    if (!TOKEN_RE.test(value)) return null;
    const row = db.prepare('SELECT id FROM teams WHERE token = ?').get(value);
    return row ? this.findById(row.id) : null;
  },

  // Cấp token mới (BTC dùng khi token bị lộ). Token cũ mất hiệu lực ngay khi nộp flag qua website;
  // cần chạy lại scripts/sync-forcad-tokens.js để ForcAD nhận token mới.
  regenerateToken(id) {
    const token = newToken();
    db.prepare("UPDATE teams SET token = ?, updated_at = datetime('now') WHERE id = ?").run(token, id);
    return token;
  },

  setForcadName(id, forcadName) {
    db.prepare("UPDATE teams SET forcad_name = ?, updated_at = datetime('now') WHERE id = ?").run(forcadName, id);
  },

  // Khóa chung của đội: tên đội ForcAD và tên máy ảo trong lab (labs/<lab>/lab.json → teams[].name/host).
  // Bỏ dấu tiếng Việt, chữ thường, chỉ a-z 0-9 và '-', tối đa 32 ký tự → hợp lệ làm hostname. Vd. "Hà Nội #1" → "ha-noi-1".
  slugOf(name) {
    return String(name || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 32).replace(/-+$/, '');
  },

  // Tên đội dùng để khớp với ForcAD: tên đã khai báo riêng, nếu trống thì dùng slug của tên đội.
  forcadNameOf(team) {
    return (team.forcad_name || '').trim() || this.slugOf(team.name);
  },

  // Các tên (chữ thường) được coi là cùng đội trên ForcAD. Tên khai riêng thì chỉ dùng tên đó;
  // nếu không thì slug, rồi tên gốc (tương thích đội ForcAD tạo trước khi có quy ước slug).
  forcadCandidates(team) {
    const explicit = (team.forcad_name || '').trim();
    const names = explicit ? [explicit] : [this.slugOf(team.name), String(team.name || '').trim()];
    return [...new Set(names.map((n) => n.toLowerCase()).filter(Boolean))];
  },
  findById(id) {
    const team = db
      .prepare('SELECT t.*, u.email FROM teams t JOIN users u ON u.id = t.user_id WHERE t.id = ?')
      .get(id);
    if (team) team.members = Member.listByTeam(team.id);
    return team;
  },

  // Bản rút gọn (không nạp thành viên), dùng ở trang quản trị.
  findBasic(id) {
    return db.prepare('SELECT id, name, token, forcad_name FROM teams WHERE id = ?').get(id);
  },

  // Đội do tài khoản này làm đội trưởng.
  findByUser(userId) {
    const team = db.prepare('SELECT * FROM teams WHERE user_id = ?').get(userId);
    if (team) team.members = Member.listByTeam(team.id);
    return team;
  },

  // Đội của một tài khoản: { team, role: 'captain' | 'member' } hoặc null nếu chưa vào đội nào.
  findForUser(userId) {
    const own = db.prepare('SELECT id FROM teams WHERE user_id = ?').get(userId);
    if (own) return { team: this.findById(own.id), role: 'captain' };
    const member = Member.findByUser(userId);
    return member ? { team: this.findById(member.team_id), role: 'member' } : null;
  },

  isNameTaken(name, excludeTeamId = 0) {
    return !!db.prepare('SELECT 1 FROM teams WHERE name = ? AND id != ?').get(name, excludeTeamId);
  },

  // Tạo đội: người tạo là đội trưởng và là thành viên đầu tiên.
  createForCaptain: db.transaction((captain, { name, school, phone }) => {
    const info = db
      .prepare('INSERT INTO teams (user_id, name, school, phone, token) VALUES (?, ?, ?, ?, ?)')
      .run(captain.id, name, school, phone, newToken());
    Member.addUser(info.lastInsertRowid, captain, true);
    return info.lastInsertRowid;
  }),

  // Vào đội bằng token đội; kiểm tra sĩ số trong cùng giao dịch để hai người vào cùng lúc không vượt giới hạn.
  // Trả về null nếu thành công, hoặc mã lỗi 'full'.
  join: db.transaction((teamId, user, maxMembers) => {
    if (Member.countByTeam(teamId) >= maxMembers) return 'full';
    Member.addUser(teamId, user, false);
    return null;
  }),

  update(teamId, { name, school, phone }) {
    db.prepare(
      "UPDATE teams SET name = ?, school = ?, phone = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(name, school, phone, teamId);
  },

  delete(id) {
    db.prepare('DELETE FROM teams WHERE id = ?').run(id);
  },

  listAll(search = '') {
    const q = `%${search}%`;
    return db
      .prepare(
        `SELECT t.*, u.email,
                (SELECT COUNT(*) FROM members m WHERE m.team_id = t.id) AS member_count
           FROM teams t JOIN users u ON u.id = t.user_id
          WHERE t.name LIKE ? OR u.email LIKE ? OR t.school LIKE ?
             OR EXISTS (SELECT 1 FROM members m WHERE m.team_id = t.id
                         AND (m.full_name LIKE ? OR m.student_id LIKE ?))
          ORDER BY t.created_at DESC`
      )
      .all(q, q, q, q, q);
  },

  listAllWithMembers() {
    const teams = db
      .prepare(
        'SELECT t.*, u.email FROM teams t JOIN users u ON u.id = t.user_id ORDER BY t.created_at'
      )
      .all();
    teams.forEach((t) => (t.members = Member.listByTeam(t.id)));
    return teams;
  },

  count() {
    return db.prepare('SELECT COUNT(*) AS n FROM teams').get().n;
  },
};

module.exports = Team;
