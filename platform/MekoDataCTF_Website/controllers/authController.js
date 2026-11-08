const User = require('../models/User');
const Setting = require('../models/Setting');

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const STUDENT_ID_RE = /^[A-Za-z0-9]{4,15}$/;

// Chỉ cho phép chuyển hướng nội bộ sau khi đăng nhập
function safeNext(next) {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') ? next : null;
}

function loginView(res, req, { status = 200, email = '', next = '', errors = [] } = {}) {
  res.status(status).render('auth/login', { title: req.t('auth.loginTitle'), email, next, errors });
}

exports.showLogin = (req, res) => {
  loginView(res, req, { next: req.query.next || '' });
};

exports.login = (req, res) => {
  const email = String(req.body.email || '').trim().toLowerCase();
  const password = String(req.body.password || '');
  const user = User.findByEmail(email);

  if (!user || !User.verifyPassword(user, password)) {
    return loginView(res, req, { status: 401, email, next: req.body.next || '', errors: [req.t('auth.invalidCredentials')] });
  }

  req.session.regenerate((err) => {
    if (err) throw err;
    req.session.userId = user.id;
    req.flash('success', req.t('auth.loggedIn'));
    res.redirect(safeNext(req.body.next) || (user.role === 'admin' ? '/admin' : '/team'));
  });
};

function registerView(res, req, { status = 200, form = {}, errors = [] } = {}) {
  res.status(status).render('auth/register', {
    title: req.t('auth.registerTitle'),
    form: { email: '', fullName: '', studentId: '', ...form },
    registrationOpen: Setting.isRegistrationOpen(),
    errors,
  });
}

exports.showRegister = (req, res) => registerView(res, req);

// Mỗi thí sinh (đội trưởng hay thành viên) tự tạo tài khoản với họ tên, MSSV; sau đó chọn Tạo đội hoặc Vào đội.
exports.register = (req, res) => {
  const form = {
    email: String(req.body.email || '').trim().toLowerCase(),
    fullName: String(req.body.fullName || '').trim().replace(/\s+/g, ' ').slice(0, 80),
    studentId: String(req.body.studentId || '').trim().toUpperCase(),
  };
  const password = String(req.body.password || '');
  const confirm = String(req.body.confirmPassword || '');

  const errors = [];
  if (!Setting.isRegistrationOpen()) errors.push(req.t('auth.registrationClosed'));
  if (!EMAIL_RE.test(form.email) || form.email.length > 120) errors.push(req.t('auth.invalidEmail'));
  if (form.fullName.length < 2) errors.push(req.t('auth.fullNameRequired'));
  if (!STUDENT_ID_RE.test(form.studentId)) errors.push(req.t('auth.studentIdInvalid'));
  if (password.length < 8) errors.push(req.t('auth.passwordTooShort'));
  if (password !== confirm) errors.push(req.t('auth.passwordMismatch'));
  if (errors.length === 0 && User.findByEmail(form.email)) errors.push(req.t('auth.emailTaken'));
  if (errors.length === 0 && User.isStudentIdTaken(form.studentId)) errors.push(req.t('auth.studentIdTaken'));
  if (errors.length) return registerView(res, req, { status: 400, form, errors });

  let user;
  try {
    user = User.create({ email: form.email, password, fullName: form.fullName, studentId: form.studentId });
  } catch (err) {
    // Hai yêu cầu đăng ký cùng email/MSSV gửi cùng lúc
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) {
      return registerView(res, req, { status: 409, form, errors: [req.t('auth.emailOrStudentTaken')] });
    }
    throw err;
  }
  req.session.regenerate((err) => {
    if (err) throw err;
    req.session.userId = user.id;
    req.flash('success', req.t('auth.registered'));
    res.redirect('/team');
  });
};

exports.logout = (req, res) => {
  const t = req.t;
  req.session.regenerate(() => {
    req.flash('success', t('auth.loggedOut'));
    res.redirect('/');
  });
};
