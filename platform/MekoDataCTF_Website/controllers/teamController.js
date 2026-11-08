const Team = require('../models/Team');
const Member = require('../models/Member');
const User = require('../models/User');
const Setting = require('../models/Setting');
const { sessionTeam } = require('../middlewares/auth');
const forcadSync = require('../services/forcadSync');

const STUDENT_ID_RE = /^[A-Za-z0-9]{4,15}$/;
const PHONE_RE = /^[0-9+\s().-]{8,20}$/;

// Giới hạn nhập sai token theo tài khoản để không dò được token của đội khác.
const JOIN_MAX_FAILS = 10;
const JOIN_WINDOW_MS = 10 * 60 * 1000;
const joinFails = new Map(); // userId -> { count, resetAt }

function joinBlocked(userId) {
  const entry = joinFails.get(userId);
  if (!entry) return false;
  if (Date.now() > entry.resetAt) {
    joinFails.delete(userId);
    return false;
  }
  return entry.count >= JOIN_MAX_FAILS;
}

function recordJoinFail(userId) {
  const entry = joinFails.get(userId);
  if (!entry || Date.now() > entry.resetAt) joinFails.set(userId, { count: 1, resetAt: Date.now() + JOIN_WINDOW_MS });
  else entry.count += 1;
}

function parseTeamForm(body) {
  return {
    name: String(body.name || '').trim(),
    school: String(body.school || '').trim().slice(0, 120),
    phone: String(body.phone || '').trim(),
  };
}

function validateTeam(req, data, teamId = 0) {
  const t = req.t;
  const errors = [];
  if (data.name.length < 2 || data.name.length > 50) errors.push(t('team.errors.nameRequired'));
  else if (Team.isNameTaken(data.name, teamId)) errors.push(t('team.errors.nameTaken'));
  if (data.phone && !PHONE_RE.test(data.phone)) errors.push(t('team.errors.phone'));
  return errors;
}

const profileComplete = (user) => !!(user.full_name && user.student_id);

// MSSV của tài khoản đã được đội trưởng một đội KHÁC nhập tay → không vào/tạo đội khác được.
function studentIdBlocked(user, teamId = 0) {
  const row = Member.findByStudentId(user.student_id);
  return !!row && row.user_id !== user.id && !(row.user_id === null && row.team_id === teamId);
}

// Đóng đăng ký thì không tạo/vào/rời/sửa đội nữa.
function ensureOpen(req, res) {
  if (Setting.isRegistrationOpen()) return true;
  req.flash('error', req.t('team.locked'));
  res.redirect('/team');
  return false;
}

function chooseView(req, res, { status = 200, createData, joinCode = '', errors = [], joinErrors = [] } = {}) {
  res.status(status).render('team/choose', {
    title: req.t('team.chooseTitle'),
    createData: createData || { name: '', school: '', phone: '' },
    joinCode,
    errors,
    joinErrors,
    profileOk: profileComplete(req.user),
    registrationOpen: Setting.isRegistrationOpen(),
  });
}

exports.show = (req, res) => {
  const session = sessionTeam(req);
  if (!session) return chooseView(req, res);
  const isCaptain = session.role === 'captain';
  const open = Setting.isRegistrationOpen();
  const minMembers = Number(Setting.all().min_members) || 1;
  res.render('team/show', {
    title: req.t('team.title'),
    team: session.team,
    isCaptain,
    canEdit: open,
    minMembers,
    maxMembers: Setting.MAX_MEMBERS,
    userId: req.user.id,
  });
};

// Tài khoản cũ (tạo trước khi đăng ký có họ tên/MSSV) bổ sung thông tin trước khi tạo/vào đội.
exports.saveProfile = (req, res) => {
  if (sessionTeam(req) || profileComplete(req.user)) return res.redirect('/team');
  const fullName = String(req.body.fullName || '').trim().replace(/\s+/g, ' ').slice(0, 80);
  const studentId = String(req.body.studentId || '').trim().toUpperCase();
  const errors = [];
  if (fullName.length < 2) errors.push(req.t('auth.fullNameRequired'));
  if (!STUDENT_ID_RE.test(studentId)) errors.push(req.t('auth.studentIdInvalid'));
  else if (User.isStudentIdTaken(studentId)) errors.push(req.t('auth.studentIdTaken'));
  if (errors.length) return chooseView(req, res, { status: 400, errors });
  try {
    User.setProfile(req.user.id, { fullName, studentId });
  } catch (err) {
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) return chooseView(req, res, { status: 409, errors: [req.t('auth.studentIdTaken')] });
    throw err;
  }
  res.redirect('/team');
};

exports.create = (req, res) => {
  if (sessionTeam(req)) return res.redirect('/team');
  if (!ensureOpen(req, res)) return;
  const data = parseTeamForm(req.body);
  const errors = profileComplete(req.user) ? validateTeam(req, data) : [req.t('team.errors.profileMissing')];
  if (!errors.length && studentIdBlocked(req.user)) errors.push(req.t('team.errors.studentIdElsewhere'));
  if (errors.length) return chooseView(req, res, { status: 400, createData: data, errors });

  try {
    Team.createForCaptain(req.user, data);
  } catch (err) {
    // Hai đội gửi cùng tên cùng lúc, hoặc tài khoản vừa vào đội khác ở tab khác
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) {
      return chooseView(req, res, { status: 409, createData: data, errors: [req.t('team.errors.nameTaken')] });
    }
    throw err;
  }
  req.flash('success', req.t('team.created'));
  // Đội mới có token mới → đẩy sang ForcAD.
  forcadSync.requestSync('team-saved');
  res.redirect('/team');
};

exports.join = (req, res) => {
  if (sessionTeam(req)) return res.redirect('/team');
  if (!ensureOpen(req, res)) return;
  const joinCode = String(req.body.token || '').trim().slice(0, 32);
  const fail = (key, status = 400, params) => chooseView(req, res, { status, joinCode, joinErrors: [req.t(key, params)] });

  if (!profileComplete(req.user)) return fail('team.errors.profileMissing');
  if (joinBlocked(req.user.id)) return fail('team.errors.joinTooMany', 429);
  const team = Team.findByToken(joinCode);
  if (!team) {
    recordJoinFail(req.user.id);
    return fail('team.errors.tokenInvalid', 404);
  }
  joinFails.delete(req.user.id);
  if (studentIdBlocked(req.user, team.id)) return fail('team.errors.studentIdElsewhere', 409);

  let result;
  try {
    result = Team.join(team.id, req.user, Setting.MAX_MEMBERS);
  } catch (err) {
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) return res.redirect('/team');   // đã vào đội ở tab khác
    throw err;
  }
  if (result === 'full') return fail('team.errors.teamFull', 409, { max: Setting.MAX_MEMBERS });
  req.flash('success', req.t('team.joined', { team: team.name }));
  res.redirect('/team');
};

function formView(req, res, { team, data, errors = [], status = 200 }) {
  res.status(status).render('team/form', { title: req.t('team.editTitle'), team, data, errors });
}

exports.edit = (req, res) => {
  if (!ensureOpen(req, res)) return;
  const { team } = sessionTeam(req);
  formView(req, res, { team, data: { name: team.name, school: team.school, phone: team.phone } });
};

exports.save = (req, res) => {
  if (!ensureOpen(req, res)) return;
  const { team } = sessionTeam(req);
  const data = parseTeamForm(req.body);
  const errors = validateTeam(req, data, team.id);
  if (errors.length) return formView(req, res, { team, data, errors, status: 400 });
  try {
    Team.update(team.id, data);
  } catch (err) {
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) {
      return formView(req, res, { team, data, errors: [req.t('team.errors.nameTaken')], status: 409 });
    }
    throw err;
  }
  req.flash('success', req.t('team.updated'));
  // Đổi tên đội có thể đổi đội ForcAD được ghép (slug).
  forcadSync.requestSync('team-saved');
  res.redirect('/team');
};

exports.removeMember = (req, res) => {
  if (!ensureOpen(req, res)) return;
  const { team } = sessionTeam(req);
  const member = Member.findById(Number(req.params.id));
  if (!member || member.team_id !== team.id || member.user_id === req.user.id) {
    req.flash('error', req.t('team.errors.memberNotFound'));
    return res.redirect('/team');
  }
  Member.remove(member.id);
  req.flash('success', req.t('team.memberRemoved', { name: member.full_name }));
  res.redirect('/team');
};

exports.leave = (req, res) => {
  const session = sessionTeam(req);
  if (!session) return res.redirect('/team');
  if (session.role === 'captain') {
    req.flash('error', req.t('team.errors.captainCannotLeave'));
    return res.redirect('/team');
  }
  if (!ensureOpen(req, res)) return;
  const member = Member.findByUser(req.user.id);
  if (member) Member.remove(member.id);
  req.flash('success', req.t('team.left', { team: session.team.name }));
  res.redirect('/team');
};

// Đội trưởng giải tán đội: xóa đội và toàn bộ danh sách thành viên; các tài khoản vẫn còn và có thể tạo/vào đội khác.
exports.disband = (req, res) => {
  if (!ensureOpen(req, res)) return;
  const { team } = sessionTeam(req);
  Team.delete(team.id);
  req.flash('success', req.t('team.disbanded', { team: team.name }));
  res.redirect('/team');
};
