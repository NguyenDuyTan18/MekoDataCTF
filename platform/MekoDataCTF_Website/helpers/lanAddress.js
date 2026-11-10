const dgram = require('dgram');
const os = require('os');

// Card mạng ảo/VPN: không phải mạng LAN mà thí sinh dùng để truy cập.
const VIRTUAL_RE = /vEthernet|WSL|Hyper-V|VMware|VirtualBox|vboxnet|Tailscale|ZeroTier|Hamachi|docker|br-|veth|virbr|Loopback|utun|tun|tap/i;
const isLinkLocal = (ip) => ip.startsWith('169.254.');
const isPrivate = (ip) => /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(ip);

function candidates() {
  const list = [];
  for (const [name, addrs] of Object.entries(os.networkInterfaces())) {
    for (const a of addrs || []) {
      if (a.family !== 'IPv4' && a.family !== 4) continue;
      if (a.internal || isLinkLocal(a.address)) continue;
      list.push({ name, address: a.address, virtual: VIRTUAL_RE.test(name) });
    }
  }
  return list;
}

// IP nguồn mà hệ điều hành chọn cho tuyến mặc định: "connect" một socket UDP (không gửi gói nào).
function defaultRouteIp(probe = '8.8.8.8') {
  return new Promise((resolve) => {
    const socket = dgram.createSocket('udp4');
    const done = (ip) => { try { socket.close(); } catch (_) { /* đã đóng */ } resolve(ip); };
    socket.on('error', () => done(null));
    try {
      socket.connect(53, probe, () => {
        try { done(socket.address().address); } catch (_) { done(null); }
      });
    } catch (_) {
      done(null);
    }
  });
}

/**
 * Tìm IP LAN của máy đang chạy. Thứ tự:
 *  1. PUBLIC_HOST trong .env (ghi đè thủ công, ví dụ khi máy có nhiều mạng).
 *  2. IP của card đi ra tuyến mặc định, nếu là card thật.
 *  3. Card thật có IP private (Wi-Fi/Ethernet), rồi tới bất kỳ card nào còn lại (LAN không có Internet).
 * Trả về { address, name, all } — address null nếu máy không có mạng.
 */
async function detectLanAddress() {
  const all = candidates();
  if (process.env.PUBLIC_HOST) return { address: process.env.PUBLIC_HOST, name: 'PUBLIC_HOST', all };
  const routed = await defaultRouteIp();
  const hit = all.find((c) => c.address === routed && !c.virtual);
  if (hit) return { ...hit, all };
  const pick = all.find((c) => !c.virtual && isPrivate(c.address)) || all.find((c) => !c.virtual) || all[0];
  return pick ? { ...pick, all } : { address: null, name: null, all };
}

module.exports = { detectLanAddress };
