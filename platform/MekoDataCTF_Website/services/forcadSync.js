// Đồng bộ token đội website → ForcAD. Website là nơi cấp token; ForcAD phải giữ cùng token thì mới nhận flag.
//
// Dùng chung cho:
// - scripts/sync-forcad-tokens.js: chạy tay, xem trước hoặc --apply.
// - Đồng bộ tự động trong app (start/requestSync): khi website khởi động, định kỳ FORCAD_SYNC_INTERVAL giây
//   (bắt các thay đổi phía ForcAD: thêm đội, ForcAD mới, recycle.py sinh lại token) và ngay sau khi
//   website tạo/sửa đội, cấp token mới hoặc đổi "Tên đội trên ForcAD".
//
// Ghép đội theo Team.forcadCandidates: tên khai riêng → slug tên đội → tên gốc.
const fs = require('fs');
const path = require('path');
const Team = require('../models/Team');

const ORIGIN = process.env.FORCAD_URL || 'http://127.0.0.1:18080';
const CONFIG_FILE = process.env.FORCAD_CONFIG || path.join(__dirname, '..', '..', 'ForcAD-demo', 'config.yml');
const INTERVAL = Number(process.env.FORCAD_SYNC_INTERVAL ?? 60) * 1000;

// Tài khoản admin ForcAD: lấy từ biến môi trường; nếu thiếu mật khẩu thì đọc mục "admin:" trong config.yml
// của ForcAD, để không phải chép mật khẩu sang .env của website.
function credentials() {
  let username = process.env.FORCAD_ADMIN_USER || '';
  let password = process.env.FORCAD_ADMIN_PASSWORD || '';
  if (!password) {
    try {
      const block = (fs.readFileSync(CONFIG_FILE, 'utf8').match(/^admin:[ \t]*\r?\n((?:[ \t]+.*(?:\r?\n|$))+)/m) || [])[1] || '';
      const field = (key) => ((block.match(new RegExp(`^[ \\t]+${key}:[ \\t]*(.*?)[ \\t]*\\r?$`, 'm')) || [])[1] || '')
        .replace(/^(['"])(.*)\1$/, '$2');
      password = field('password');
      username = username || field('username');
    } catch (_) { /* không có config.yml: chỉ dùng biến môi trường */ }
  }
  return { username: username || 'forcad', password };
}

async function login(username, password) {
  const res = await fetch(new URL('/api/admin/login/', ORIGIN), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    redirect: 'error',
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`Đăng nhập ForcAD thất bại (HTTP ${res.status}). Kiểm tra tài khoản quản trị.`);
  const session = (res.headers.get('set-cookie') || '').match(/session=([^;]+)/);
  if (!session) throw new Error('ForcAD không trả cookie phiên quản trị.');
  return (apiPath, init = {}) => fetch(new URL('/api/admin/' + apiPath, ORIGIN), {
    ...init,
    headers: { 'Content-Type': 'application/json', Cookie: `session=${session[1]}` },
    redirect: 'error',
    signal: AbortSignal.timeout(8000),
  });
}

// Trả về { code, results, lines }. results[i] = { teamId, team, forcad, state } với state:
// ok | written | pending (chưa --apply) | unmatched | taken (đội ForcAD đã ghép đội khác) | clash (token thuộc đội khác) | failed.
// Lỗi kết nối/đăng nhập được ném ra.
async function syncTokens({ apply = false, log = console.log } = {}) {
  const { username, password } = credentials();
  if (!password) throw new Error(`Thiếu FORCAD_ADMIN_PASSWORD và không đọc được mục admin trong ${CONFIG_FILE}.`);
  const api = await login(username, password);

  const list = await api('teams/');
  if (!list.ok) throw new Error(`Không đọc được danh sách đội ForcAD (HTTP ${list.status}).`);
  const forcadTeams = (await list.json()).filter((t) => t.active);
  const byName = new Map(forcadTeams.map((t) => [String(t.name).trim().toLowerCase(), t]));
  const websiteTeams = Team.listAll();

  const results = [];
  const lines = [];
  const say = (line) => { lines.push(line); log(line); };
  const matched = new Set();
  for (const team of websiteTeams) {
    const target = Team.forcadNameOf(team);
    const forcad = Team.forcadCandidates(team).map((name) => byName.get(name)).find(Boolean);
    const result = { teamId: team.id, team: team.name, forcad: forcad ? forcad.name : target };
    results.push(result);
    if (!forcad) {
      result.state = 'unmatched';
      say(`✗ ${team.name}: chưa có đội "${target}" (đang hoạt động) trên ForcAD`);
      continue;
    }
    if (matched.has(forcad.id)) {
      result.state = 'taken';
      say(`✗ ${team.name}: đội ForcAD "${forcad.name}" đã ghép với đội website khác`);
      continue;
    }
    matched.add(forcad.id);
    // Không để hai đội ForcAD trùng token: ForcAD tra đội theo token khi nhận flag.
    const clash = forcadTeams.find((t) => t.id !== forcad.id && t.token === team.token);
    if (clash) {
      result.state = 'clash';
      say(`✗ ${team.name}: token đang thuộc đội ForcAD "${clash.name}"`);
      continue;
    }
    if (forcad.token === team.token) {
      result.state = 'ok';
      say(`✓ ${team.name} → ${forcad.name}: token đã khớp`);
      continue;
    }
    if (!apply) {
      result.state = 'pending';
      say(`→ ${team.name} → ${forcad.name}: sẽ ghi token (chạy lại với --apply)`);
      continue;
    }
    const res = await api(`teams/${forcad.id}/`, { method: 'PUT', body: JSON.stringify({ ...forcad, token: team.token }) });
    result.state = res.ok ? 'written' : 'failed';
    say(res.ok ? `→ ${team.name} → ${forcad.name}: đã ghi token` : `✗ ${team.name}: ForcAD từ chối cập nhật (HTTP ${res.status})`);
  }
  for (const forcad of forcadTeams) {
    if (!matched.has(forcad.id)) say(`· Đội ForcAD "${forcad.name}" không ghép với đội website nào (giữ token của ForcAD)`);
  }

  const count = (...states) => results.filter((r) => states.includes(r.state)).length;
  const problems = count('unmatched', 'taken', 'clash', 'failed');
  say(`\n${websiteTeams.length} đội website · ${forcadTeams.length} đội ForcAD đang hoạt động · `
    + `${apply ? `đã ghi ${count('written')}` : `cần ghi ${count('pending')}`} · ${problems} vấn đề`);
  return { code: problems ? 1 : 0, results, lines };
}

/* ---------- Đồng bộ tự động trong app ---------- */
let running = null;
let again = false;
let lastLog = '';
let status = { at: null, error: '', results: [] };

// Gọi sau mọi thay đổi có thể làm lệch token. Không chờ, không ném lỗi; các yêu cầu dồn lúc đang chạy gộp thành một lượt nữa.
function requestSync(reason = 'manual') {
  if (!credentials().password) return Promise.resolve();
  if (running) { again = true; return running; }
  running = (async () => {
    let lines;
    try {
      const report = await syncTokens({ apply: true, log: () => {} });
      status = { at: new Date(), error: '', results: report.results };
      lines = report.lines;
    } catch (err) {
      status = { at: new Date(), error: err.message, results: status.results };
      lines = ['Không đồng bộ được: ' + err.message];
    }
    // Chỉ in khi kết quả đổi, để lượt định kỳ không làm đầy log.
    const text = lines.join('\n');
    if (text !== lastLog) { console.log(`[forcad-sync] (${reason})\n${text}`); lastLog = text; }
  })().finally(() => {
    running = null;
    if (again) { again = false; requestSync('pending'); }
  });
  return running;
}

function start() {
  if (!credentials().password) {
    console.warn('[forcad-sync] Tắt: không có mật khẩu admin ForcAD (FORCAD_ADMIN_PASSWORD hoặc ' + CONFIG_FILE + ').');
    return;
  }
  requestSync('startup');
  if (INTERVAL > 0) setInterval(() => requestSync('interval'), INTERVAL).unref();
}

// Kết quả lượt gần nhất của một đội website (cho trang quản trị).
function statusOf(teamId) {
  return { at: status.at, error: status.error, result: status.results.find((r) => r.teamId === teamId) || null };
}

module.exports = { syncTokens, requestSync, start, statusOf, credentials };
