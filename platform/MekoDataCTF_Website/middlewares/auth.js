const Team = require('../models/Team');

// Đội của phiên hiện tại: { team, role: 'captain' | 'member' }, hoặc null nếu chưa vào đội (hoặc là admin).
// Mọi thành viên đều đăng nhập bằng tài khoản email của riêng mình.
function sessionTeam(req) {
  if (!req.user || req.user.role !== 'contestant') return null;
  if (req.teamSession === undefined) req.teamSession = Team.findForUser(req.user.id);
  return req.teamSession;
}

function requireLogin(req, res, next) {
  if (req.user) return next();
  req.flash('error', req.t('auth.loginRequired'));
  res.redirect(`/login?next=${encodeURIComponent(req.originalUrl)}`);
}

// Thí sinh (không phải admin) đã đăng nhập.
function requireContestant(req, res, next) {
  if (!req.user) return requireLogin(req, res, next);
  if (req.user.role === 'contestant') return next();
  res.redirect('/admin');
}

// Chỉ đội trưởng được sửa đội, đổi mã mời, xóa thành viên, giải tán đội.
function requireCaptain(req, res, next) {
  if (!req.user) return requireLogin(req, res, next);
  const session = sessionTeam(req);
  if (session && session.role === 'captain') return next();
  req.flash('error', req.t('team.captainOnly'));
  res.redirect('/team');
}

function requireAdmin(req, res, next) {
  if (!req.user) return requireLogin(req, res, next);
  if (req.user.role === 'admin') return next();
  res.status(403).render('error', { title: '403', message: req.t('errors.forbidden') });
}

function requireGuest(req, res, next) {
  if (!req.user) return next();
  res.redirect(req.user.role === 'admin' ? '/admin' : '/team');
}

function requireSession(req, res, next) {
  if (req.user) return next();
  res.redirect('/');
}

module.exports = { sessionTeam, requireLogin, requireContestant, requireCaptain, requireAdmin, requireGuest, requireSession };
