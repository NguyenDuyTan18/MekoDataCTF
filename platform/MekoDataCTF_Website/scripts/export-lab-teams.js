// Sinh danh sách đội cho labs/<lab>/lab.json từ các đội đã đăng ký trên website.
// Quy ước: tên đội ForcAD = tên máy ảo = Team.forcadNameOf(team) (tên khai riêng, nếu trống thì slug tên đội).
//
//   node scripts/export-lab-teams.js                                # in JSON teams, không ghi gì
//   node scripts/export-lab-teams.js --subnet 10.90.0 --start 11    # đổi dải IP (mặc định 10.80.0, bắt đầu .11)
//   node scripts/export-lab-teams.js --write round2                 # ghi đè mục "teams" trong labs/round2/lab.json
//
// Sau khi ghi: đặt tên VM trong sandbox/topology.yml, tạo đội ForcAD đúng các tên này,
// rồi chạy scripts/sync-forcad-tokens.js --apply để ForcAD nhận token của website.
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const Team = require('../models/Team');

const HOSTNAME_RE = /^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$/;
const arg = (flag, fallback) => {
  const i = process.argv.indexOf(flag);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

function main() {
  const subnet = arg('--subnet', '10.80.0');
  const start = Number(arg('--start', '11'));
  const lab = arg('--write', '');
  if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(subnet) || !Number.isInteger(start) || start < 1) {
    console.error('--subnet phải có dạng a.b.c, --start là số nguyên dương.');
    return 2;
  }

  const teams = Team.listAll().sort((a, b) => a.id - b.id);
  if (start + teams.length - 1 > 254) {
    console.error(`Dải ${subnet}.${start} không đủ chỗ cho ${teams.length} đội.`);
    return 2;
  }
  let problems = 0;
  const seen = new Map();
  const result = teams.map((team, i) => {
    const name = Team.forcadNameOf(team);
    if (!HOSTNAME_RE.test(name)) {
      console.error(`✗ ${team.name}: "${name}" không dùng được làm tên máy ảo (chỉ a-z 0-9 '-', tối đa 32 ký tự). Khai "Tên đội trên ForcAD" ở trang quản trị.`);
      problems += 1;
    } else if (seen.has(name)) {
      console.error(`✗ ${team.name}: trùng tên "${name}" với đội ${seen.get(name)}. Khai "Tên đội trên ForcAD" khác cho một trong hai đội.`);
      problems += 1;
    }
    seen.set(name, team.name);
    return { name, host: name, ip: `${subnet}.${start + i}` };
  });
  if (problems) return 1;

  if (!lab) {
    console.log(JSON.stringify(result, null, 2));
    return 0;
  }
  if (!/^[a-z0-9][a-z0-9_-]*$/.test(lab)) {
    console.error('--write nhận tên thư mục lab, vd. round2.');
    return 2;
  }
  const file = path.resolve(__dirname, '..', '..', '..', 'labs', lab, 'lab.json');
  if (!fs.existsSync(file)) {
    console.error(`Không thấy ${file}. Chép labs/_template/lab.json sang trước.`);
    return 2;
  }
  const config = JSON.parse(fs.readFileSync(file, 'utf8'));
  config.teams = result;
  fs.writeFileSync(file, JSON.stringify(config, null, 2) + '\n');
  console.log(`Đã ghi ${result.length} đội vào ${file}`);
  return 0;
}

process.exitCode = main();
