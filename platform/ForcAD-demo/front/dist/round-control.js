(() => {
  if (location.pathname !== '/') return;

  // ---- Giao diện ----------------------------------------------------------
  // Bố cục: [Tiêu đề + trạng thái] → [Tình trạng hiện tại] → [Hành động chính]
  //         → [Vòng thi] → [Chuẩn bị lab] → [Vùng nguy hiểm] → [Liên kết]
  const style = document.createElement('style');
  style.textContent = `
  #rc-panel{box-sizing:border-box;margin:16px auto!important;max-width:1050px!important;padding:0!important;background:#141a24!important;border:1px solid #2a3344!important;border-radius:12px!important;color:#e6eaf2!important;font:14px/1.5 Inter,system-ui,Segoe UI,Arial,sans-serif;overflow:hidden}
  #rc-panel *{box-sizing:border-box}
  #rc-panel [hidden]{display:none!important}
  #rc-panel .rc-head{display:flex;align-items:center;gap:12px;padding:14px 20px;background:#19202d;border-bottom:1px solid #2a3344}
  #rc-panel .rc-head h2{margin:0;font-size:16px;font-weight:600;flex:1;color:#f1f4fa}
  #rc-panel .rc-pill{display:inline-flex;align-items:center;gap:7px;padding:4px 11px;border-radius:999px;font-size:12px;font-weight:600;background:#262f40;color:#aab4c8;white-space:nowrap}
  #rc-panel .rc-pill::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
  #rc-panel .rc-pill[data-tone="run"]{background:#123224;color:#4ade80}
  #rc-panel .rc-pill[data-tone="pause"]{background:#3a2e12;color:#fbbf24}
  #rc-panel .rc-pill[data-tone="done"]{background:#1c2a45;color:#93c5fd}
  #rc-panel .rc-pill[data-tone="bad"]{background:#3a1c1f;color:#f87171}

  #rc-panel .rc-status{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:#222a39;border-bottom:1px solid #222a39}
  #rc-panel .rc-cell{background:#141a24;padding:12px 20px;min-width:0}
  #rc-panel .rc-cell small{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#7c8aa5;font-weight:600}
  #rc-panel .rc-cell b{display:block;font-size:15px;font-weight:600;color:#f1f4fa;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #rc-panel .rc-bar{height:5px;border-radius:3px;background:#262f40;margin-top:7px;overflow:hidden}
  #rc-panel .rc-bar i{display:block;height:100%;width:0;background:#3b82f6;transition:width .3s}

  #rc-panel .rc-group{padding:16px 20px;border-bottom:1px solid #222a39}
  #rc-panel .rc-group>h3{margin:0 0 4px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#7c8aa5;font-weight:600}
  #rc-panel .rc-group>p{margin:0 0 12px;font-size:12.5px;color:#8b96ab}
  #rc-panel .rc-row{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center}

  #rc-panel button{font:inherit;padding:8px 15px;border-radius:8px;border:1px solid #38445c;background:#222b3c;color:#e6eaf2;cursor:pointer;transition:background .12s,border-color .12s}
  #rc-panel button:hover:not(:disabled){background:#2c3850;border-color:#4a597a}
  #rc-panel button:disabled{opacity:.45;cursor:not-allowed}
  #rc-panel button:focus-visible,#rc-panel a:focus-visible,#rc-panel summary:focus-visible{outline:2px solid #60a5fa;outline-offset:2px}
  #rc-panel .rc-primary{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:600;padding:9px 22px}
  #rc-panel .rc-primary:hover:not(:disabled){background:#1d4fd7;border-color:#1d4fd7}
  #rc-panel .rc-stop{background:#b45309;border-color:#b45309;color:#fff;font-weight:600;padding:9px 22px}
  #rc-panel .rc-stop:hover:not(:disabled){background:#92400e;border-color:#92400e}
  #rc-panel .rc-danger{color:#fca5a5;border-color:#5b2b2b;background:#2a1d20}
  #rc-panel .rc-danger:hover:not(:disabled){background:#3a2326;border-color:#7a3a3a}

  #rc-panel .rc-slots{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  #rc-panel .rc-slot{display:flex;flex-direction:column;align-items:flex-start;gap:2px;text-align:left;padding:12px 14px}
  #rc-panel .rc-slot b{font-size:14px;font-weight:600}
  #rc-panel .rc-slot span{font-size:12.5px;color:#9aa6bd}
  #rc-panel .rc-slot[aria-pressed="true"]{border-color:#3b82f6;background:#172a4d;box-shadow:inset 3px 0 0 #3b82f6}
  #rc-panel .rc-slot[aria-pressed="true"] span{color:#bfdbfe}

  #rc-panel details{margin-top:12px;border:1px solid #2a3344;border-radius:8px;background:#11161f}
  #rc-panel summary{cursor:pointer;padding:9px 14px;font-size:13px;color:#c4ccdd;user-select:none}
  #rc-panel details form{padding:4px 14px 14px;gap:12px}
  #rc-panel select{font:inherit;padding:7px 10px;border-radius:7px;border:1px solid #38445c;background:#222b3c;color:#e6eaf2;min-width:200px}
  #rc-panel label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:#9aa6bd}
  #rc-panel form button{align-self:flex-end}

  #rc-panel .rc-note{margin:0;padding:12px 20px;white-space:pre-wrap;font-size:13px;color:#d6dcea;background:#15213a;border-bottom:1px solid #222a39;border-left:3px solid #3b82f6}
  #rc-panel .rc-note:empty{display:none}
  #rc-panel .rc-flash{margin:0;padding:10px 20px;font-size:13px;color:#fecaca;background:#2a1719;border-bottom:1px solid #4a2326}
  #rc-panel .rc-flash:empty{display:none}

  #rc-panel .rc-foot{display:flex;flex-wrap:wrap;align-items:center;gap:6px 18px;padding:12px 20px;background:#11161f;font-size:13px}
  #rc-panel .rc-foot .rc-help{flex:1 1 100%;font-size:12px;color:#7c8aa5}
  #rc-panel a{color:#7cc0ff;text-decoration:none}
  #rc-panel a:hover{text-decoration:underline}
  #rc-panel a.rc-loginbtn{display:inline-block;padding:9px 22px;border-radius:8px;background:#2563eb;color:#fff;font-weight:600}
  #rc-panel a.rc-loginbtn:hover{background:#1d4fd7;text-decoration:none}
  @media (max-width:720px){#rc-panel .rc-status{grid-template-columns:repeat(2,minmax(0,1fr))}#rc-panel .rc-slots{grid-template-columns:1fr}}
  `;
  document.head.appendChild(style);

  const el = (tag, props = {}, children = []) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  };
  const group = (title, hint) => {
    const box = el('div', {className: 'rc-group'}, [el('h3', {textContent: title})]);
    if (hint) box.append(el('p', {textContent: hint}));
    return box;
  };
  const mkbtn = (text, cls) => el('button', {type: 'button', textContent: text, className: cls || '', hidden: true});

  const panel = el('section', {id: 'rc-panel'});

  // Tiêu đề + trạng thái tổng
  const pill = el('span', {id: 'rc-state', className: 'rc-pill', textContent: 'Đang kiểm tra…'});
  panel.append(el('div', {className: 'rc-head'}, [el('h2', {textContent: 'Điều khiển round'}), pill]));

  // Tình trạng hiện tại
  const cell = label => {
    const value = el('b', {textContent: '—'});
    return [el('div', {className: 'rc-cell'}, [el('small', {textContent: label}), value]), value];
  };
  const [slotCell, slotVal] = cell('Vòng');
  const [labCell, labVal] = cell('Lab');
  const [phaseCell, phaseVal] = cell('Giai đoạn');
  const [tickCell, tickVal] = cell('Tick');
  const barFill = el('i');
  tickCell.append(el('div', {className: 'rc-bar'}, [barFill]));
  const status = el('div', {className: 'rc-status', hidden: true}, [slotCell, labCell, phaseCell, tickCell]);
  panel.append(status);

  // Thông báo lỗi tạm thời và ghi chú hồ sơ
  const flash = el('div', {className: 'rc-flash', role: 'alert'});
  const maintenance = el('div', {id: 'rc-maintenance', className: 'rc-note'});
  panel.append(flash, maintenance);

  // Hành động chính
  const start = mkbtn('Bắt đầu', 'rc-primary');
  const stop = mkbtn('Dừng', 'rc-stop');
  const restart = mkbtn('Bắt đầu lại từ tick 0');       // lưu hồ sơ, về tick 0, giữ đội/token/VM, chạy luôn
  const next = mkbtn('Chuyển sang bài kế tiếp', 'rc-primary');   // nhãn lấy từ data.next_lab_title
  const archive = mkbtn('Đóng và lưu hồ sơ');
  const login = el('a', {id: 'rc-login', href: '/admin/login/?next=/', textContent: 'Đăng nhập quản trị', className: 'rc-loginbtn', hidden: true});
  const actions = group('Hành động');
  actions.append(el('div', {className: 'rc-row'}, [start, stop, next, login, restart, archive]));
  panel.append(actions);

  // Vòng thi
  const slotButtons = [1, 2].map(n => el('button', {type: 'button', className: 'rc-slot'},
    [el('b', {textContent: 'Round ' + n}), el('span', {textContent: '—'})]));
  const labSelects = [1, 2].map(() => el('select'));
  const saveSlots = el('button', {type: 'submit', className: 'rc-primary', textContent: 'Lưu cấu hình'});
  const slotConfig = el('form', {id: 'rc-slot-config', className: 'rc-row'}, [
    el('label', {}, ['Lab cho Round 1', labSelects[0]]),
    el('label', {}, ['Lab cho Round 2', labSelects[1]]),
    saveSlots,
  ]);
  const slotDetails = el('details', {}, [el('summary', {textContent: 'Đổi lab cho từng vòng'}), slotConfig]);
  const roundPicker = group('Vòng thi', 'Bấm vào một vòng để chuyển sang vòng đó. Cần Dừng và chờ checker hoàn tất trước.');
  roundPicker.hidden = true;
  roundPicker.append(el('div', {id: 'rc-slots', className: 'rc-slots'}, slotButtons), slotDetails);
  panel.append(roundPicker);
  let renderedLabs = '';

  // Chuẩn bị lab (chế độ một lab)
  // Nút tự sinh từ data.prepare_labs (mỗi bài trong lab_profile.py, trừ bài nối sau bài khác).
  const setup = group('Chuẩn bị lab', 'Dựng đội và task cho lab được chọn. Chưa sinh flag cho tới khi bấm Bắt đầu.');
  const prepareRow = el('div', {className: 'rc-row'});
  setup.append(prepareRow);
  panel.append(setup);
  const prepareButtons = new Map();   // lab -> button
  let renderedPrepare = '';
  function renderPrepare(labs) {
    const key = JSON.stringify(labs || {});
    if (key === renderedPrepare) return;
    renderedPrepare = key;
    prepareButtons.clear();
    prepareRow.replaceChildren(...Object.entries(labs || {}).map(([lab, info]) => {
      const button = mkbtn(`${info.title} · ${info.tasks.length} task`);
      button.addEventListener('click', () => prepareLab(button, lab,
        `Chuẩn bị ${info.title} với ${info.tasks.length} task (${info.tasks.map(t => t.toUpperCase()).join(', ')})? ` +
        'Chỉ thực hiện khi bản health đã dừng và reset về 0, hoặc lab khác đã đóng và lưu hồ sơ ' +
        '(điểm, flag lượt đó sẽ bị xóa khỏi bảng thi, hồ sơ vẫn giữ). Chưa sinh flag cho đến khi bấm Bắt đầu.'));
      prepareButtons.set(lab, button);
      return button;
    }));
  }
  // show(lab) -> true để hiện nút của lab đó; bỏ trống = ẩn tất cả.
  const showPrepare = (show = () => false) => prepareButtons.forEach((button, lab) => { button.hidden = !show(lab); });
  let nextLab = null;

  // Vùng nguy hiểm
  const reset = mkbtn('Reset round và điểm', 'rc-danger');
  const danger = group('Vùng nguy hiểm', 'Đưa tick và điểm của các đội về 0, xóa lịch sử checker. Không lưu hồ sơ.');
  danger.append(el('div', {className: 'rc-row'}, [reset]));
  panel.append(danger);

  // Liên kết + hướng dẫn
  const download = el('a', {id: 'rc-download', textContent: '⬇ Tải hồ sơ JSON', hidden: true});
  const previous = el('a', {textContent: '⬇ Tải hồ sơ lượt trước', hidden: true});
  const submission = el('a', {href: '/submit.html', textContent: 'Bản đồ flag'});
  const management = el('a', {href: '/admin/', textContent: 'Quản lý đội / task'});
  const help = el('div', {id: 'rc-help', className: 'rc-help',
    textContent: 'Mỗi vòng có 10 phút xem đề rồi 10 tick, mỗi tick 5 phút. Bấm Dừng và chờ checker hoàn tất trước khi chọn vòng khác.'});
  panel.append(el('div', {className: 'rc-foot'}, [download, previous, submission, management, help]));

  document.body.insertBefore(panel, document.getElementById('app'));

  const PHASES = {ready: 'Sẵn sàng', preparing: 'Đang chuẩn bị', preview: 'Đang xem đề', running: 'Đang chạy',
    checking: 'Đang chấm', draining: 'Cửa sổ flag cuối', paused: 'Tạm dừng', finished: 'Đã kết thúc',
    archived: 'Đã lưu hồ sơ', recreating: 'Đang tái tạo'};
  const setPill = (text, tone) => { pill.textContent = text; pill.dataset.tone = tone || ''; };
  const showFlash = msg => { flash.textContent = msg || ''; };
  // Ẩn khối khi mọi nút bên trong đều ẩn, để bảng không có tiêu đề trống.
  const syncGroups = () => {
    [actions, setup, danger].forEach(box => {
      box.hidden = ![...box.querySelectorAll('button, a')].some(node => !node.hidden);
    });
  };

  let lastArchive = '';
  try { lastArchive = localStorage.getItem('rc-last-archive') || ''; } catch (_) {}
  let round1Mode = false;
  let slotMode = false;
  let busy = false;
  const hideAll = () => {
    start.hidden = stop.hidden = reset.hidden = roundPicker.hidden =
      next.hidden = archive.hidden = download.hidden = restart.hidden = previous.hidden = true;
    showPrepare();
  };

  // ---- Logic điều khiển (giữ nguyên hành vi và các lệnh gọi API) ----------
  async function refresh() {
    if (busy) return;
    try {
      const res = await fetch('/api/admin/round-control/', {credentials:'same-origin', cache:'no-store'});
      if (res.status === 403 || res.status === 401) {
        setPill('Cần đăng nhập quản trị', 'bad');
        hideAll(); status.hidden = true; login.hidden = false; syncGroups(); return;
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      if (busy) return;
      setPill(data.running ? 'Đang chạy' : 'Đã dừng', data.running ? 'run' : 'pause');
      login.hidden = true; start.hidden = data.running; stop.hidden = !data.running; reset.hidden = data.running;
      const r1 = data.round1 || {};
      renderPrepare(data.prepare_labs);
      const tick = data.display_tick ?? r1.tick;
      const slots = data.slots || {};
      slotMode = !!r1.slot;
      roundPicker.hidden = false;
      slotDetails.hidden = !data.can_configure_slots;
      const mapping = slotMode ? Object.fromEntries(Object.entries(slots).map(([key, row]) => [key, row.lab])) : data.default_slots;
      const mappingKey = JSON.stringify([mapping?.['1'], mapping?.['2'], data.labs]);
      if (mappingKey !== renderedLabs) {
        labSelects.forEach((select, index) => {
          select.replaceChildren(...Object.entries(data.labs || {}).map(([id, title]) => new Option(title, id)));
          select.value = mapping?.[String(index + 1)] || '';
        });
        renderedLabs = mappingKey;
      }
      slotButtons.forEach((button, index) => {
        const slot = index + 1;
        const entry = slots[slot];
        const name = data.labs?.[entry?.lab] || data.labs?.[mapping?.[String(slot)]];
        const phase = entry?.phase;
        const detail = phase === 'finished' ? 'Đã kết thúc' : phase === 'paused' ? 'Tạm dừng · bấm để tiếp tục'
          : slot === r1.slot ? 'Đang chọn' : phase ? PHASES[phase] || phase : 'Chưa bắt đầu';
        button.children[1].textContent = (name ? name + ' · ' : '') + detail;
        button.disabled = !data.can_start_slot || phase === 'finished';
        button.setAttribute('aria-pressed', String(slot === r1.slot));
      });
      nextLab = data.next_lab || null;
      next.hidden = data.running || r1.phase !== 'finished' || !nextLab;
      next.textContent = 'Chuyển sang Round 2 · ' + (data.next_lab_title || nextLab || '');
      start.textContent = r1.phase === 'paused' ? 'Tiếp tục' : data.preview_seconds && tick === 0 ? 'Bắt đầu xem đề' : 'Bắt đầu';
      if (slotMode) start.hidden = true;
      round1Mode = !!r1.configured;
      // Round 1: khi đã chạy ít nhất một tick, hoặc đã "Đóng và lưu hồ sơ" (dùng lại hồ sơ đó, không dọn VM).
      // Bản health: thay cho Reset rồi Bắt đầu.
      restart.hidden = data.running || (round1Mode
        ? !(['paused', 'finished', 'archived'].includes(r1.phase) ||
            (slotMode ? Object.values(slots).some(row => ['paused', 'finished'].includes(row.phase))
                      : (r1.phase === 'ready' && r1.tick > 0)))
        : ['archived', 'recreating'].includes(r1.phase));
      previous.hidden = !lastArchive || ['archived', 'recreating'].includes(r1.phase);
      if (lastArchive) previous.href = '/api/admin/round1/archive/' + encodeURIComponent(lastArchive) + '/';
      const canPrepare = !(data.running || r1.configured || ['archived','recreating'].includes(r1.phase));
      showPrepare(() => canPrepare);
      archive.hidden = data.running || !r1.configured || !['ready','paused','finished'].includes(r1.phase) ||
        (slotMode && !data.can_start_slot) || !!r1.archive_id;
      download.hidden = !['archived','recreating'].includes(r1.phase) || !r1.archive_id;
      if (download.hidden === false) {
        download.href = '/api/admin/round1/archive/' + encodeURIComponent(r1.archive_id) + '/';
        maintenance.textContent = slotMode
          ? `Đã lưu hai vòng vào hồ sơ ${r1.archive_id}. Bạn có thể tải JSON, chơi lại hoặc chọn cặp lab mới.`
          : `Đã đóng và lưu hồ sơ ${r1.archive_id}. Hãy tải JSON lưu ngoài máy trước khi dọn dữ liệu.\n• Chơi lại ngay, không dọn VM: bấm "Bắt đầu lại từ tick 0" (giữ đội và token).\n` +
            ((r1.lab || 'round1') === 'round1'
              ? `• Dọn sạch VM rồi chơi lại: sau khi dọn và kiểm tra đủ attacker1–4, chạy trong PowerShell tại workspace:\npython labs/round1/service/recycle.py --archive-id ${r1.archive_id}`
              : '• Dọn sạch VM rồi chơi lại: dựng lại máy các đội bằng playbook của bài, rồi bấm "Bắt đầu lại từ tick 0".');
      } else maintenance.textContent = '';

      // Ô tình trạng
      status.hidden = !r1.configured && !['archived', 'recreating'].includes(r1.phase);
      slotCell.hidden = !r1.slot;
      slotVal.textContent = r1.slot ? 'Round ' + r1.slot : '—';
      labVal.textContent = data.labs?.[r1.lab] || r1.lab || 'Round 1';
      phaseVal.textContent = PHASES[r1.phase] || r1.phase || '—';
      const total = data.ticks_per_round || 0;
      tickVal.textContent = total ? `${Math.max(0, tick ?? 0)} / ${total}` : String(tick ?? '—');
      barFill.style.width = total ? Math.min(100, Math.max(0, (tick || 0) / total * 100)) + '%' : '0';

      if (r1.configured) {
        reset.hidden = true;
        if (r1.phase === 'finished') { start.hidden = true; if (!data.running) setPill('Đã kết thúc', 'done'); }
        if (r1.phase === 'preview' && data.running) setPill('Đang xem đề', 'run');
      }
      if (r1.phase === 'archived') {
        start.hidden = stop.hidden = reset.hidden = true;
        // Đã lưu hồ sơ: cho phép chuyển sang lab khác, dữ liệu lượt cũ được xóa khỏi bảng thi.
        showPrepare(lab => !slotMode && lab !== (r1.lab || 'round1'));
        setPill('Đã đóng · dữ liệu đã lưu', 'done');
      }
      if (r1.phase === 'recreating') {
        start.hidden = stop.hidden = reset.hidden = roundPicker.hidden = next.hidden = archive.hidden = restart.hidden = true;
        showPrepare();
        download.hidden = false;
        setPill('Đang tái tạo', 'pause');
        maintenance.textContent = 'Đang hoàn tất tái tạo; chạy lại script cùng archive ID nếu cần.';
      }
      syncGroups();
    } catch (err) {
      setPill('Không kết nối được bộ điều khiển', 'bad');
      hideAll(); status.hidden = true; syncGroups();
    }
  }
  async function post(url, body) {
    const res = await fetch(url, {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'HTTP ' + res.status);
    return data;
  }
  async function updateSlots(body) {
    if (busy) return;
    busy = true; showFlash('');
    slotButtons.forEach(button => { button.disabled = true; });
    saveSlots.disabled = true;
    try {
      await post('/api/admin/round-control/slots/', body);
    } catch (err) { showFlash(err.message); }
    finally { busy = false; saveSlots.disabled = false; await refresh(); }
  }
  slotConfig.addEventListener('submit', event => {
    event.preventDefault();
    const [first, second] = labSelects.map(select => select.value);
    if (first === second) {
      showFlash('Chọn hai lab khác nhau.');
      return;
    }
    if (!download.hidden && !confirm('Dùng cặp lab này cho lượt mới? Kết quả cũ vẫn còn trong hồ sơ đã lưu.')) return;
    updateSlots({labs: {'1': first, '2': second}});
  });
  slotButtons.forEach((button, index) => {
    button.addEventListener('click', () => updateSlots({slot: index + 1}));
  });
  restart.addEventListener('click', async () => {
    const question = slotMode
      ? 'Bắt đầu lại từ tick 0?\n\n• Lưu hồ sơ lượt hiện tại, đưa cả hai vòng về tick 0 (giữ đội, token và lab đã chọn).\n• Sau đó TỰ MỞ Round 1: 10 phút xem đề rồi tick 1. Nhớ bật collector trước.\n• Cần dừng ít nhất 45 giây trước.'
      : round1Mode
      ? `Bắt đầu lại ${labVal.textContent} từ tick 0?\n\n• Hồ sơ lượt hiện tại được lưu vào PostgreSQL trước (nếu đã đóng và lưu thì dùng lại hồ sơ đó; tải lại được).\n• Xóa flag, điểm, lịch sử checker; giữ đội, token đội và task.\n• KHÔNG dọn dữ liệu trên VM đội (bản vá của đội vẫn còn). Muốn dọn VM: dùng "Đóng và lưu hồ sơ" rồi dựng lại máy đội.\n• Cần dừng ít nhất 45 giây trước.`
      : 'Reset tick và điểm về 0 rồi bắt đầu lại? Cần dừng ít nhất 30 giây trước.';
    if (!confirm(question)) return;
    busy = true; restart.disabled = true; showFlash('');
    try {
      if (round1Mode) {
        const data = await post('/api/admin/round1/restart/', {confirm:'RESTART ROUND1'});
        lastArchive = data.archive_id || '';
        try { localStorage.setItem('rc-last-archive', lastArchive); } catch (_) {}
      } else {
        await post('/api/admin/round-control/reset/', {confirm:'RESET'});
      }
      // Một bài: bật chạy. Hai vòng: đặt lại chỉ đưa về "Sẵn sàng", nên mở luôn Round 1 (trước đây phải tự bấm thẻ Round 1).
      if (slotMode) await post('/api/admin/round-control/slots/', {slot: 1});
      else await post('/api/admin/round-control/', {running:true});
      location.reload();
    } catch (err) { showFlash('Không bắt đầu lại được: ' + err.message); }
    finally { busy = false; restart.disabled = false; await refresh(); }
  });
  async function setRunning(running) {
    busy = true; start.disabled = stop.disabled = true; showFlash('');
    try {
      await post('/api/admin/round-control/', {running});
    } catch (err) { showFlash('Không đổi được trạng thái round: ' + err.message); }
    finally { busy = false; start.disabled = stop.disabled = false; await refresh(); }
  }
  start.addEventListener('click', () => setRunning(true));
  stop.addEventListener('click', () => setRunning(false));
  async function prepareLab(button, lab, question) {
    if (!confirm(question)) return;
    busy = true; button.disabled = true; showFlash('');
    try {
      await post('/api/admin/round1/prepare/', {confirm:'PREPARE ROUND1',lab});
      location.reload();
    } catch (err) { showFlash(err.message); }
    finally { busy = false; button.disabled = false; }
  }
  next.addEventListener('click', () => nextLab && prepareLab(next, nextLab, `Chuyển sang ${next.textContent.replace('Chuyển sang ', '')} và giữ điểm vòng trước? Sau khi chuyển, bấm Bắt đầu xem đề.`));
  archive.addEventListener('click', async () => {
    if (!confirm('Đóng cuộc thi và lưu flag, điểm vào hồ sơ PostgreSQL?')) return;
    busy = true; archive.disabled = true; showFlash('');
    try {
      await post('/api/admin/round1/archive/', {confirm:'ARCHIVE ROUND1'});
      location.reload();
    } catch (err) { showFlash('Không đóng được cuộc thi: ' + err.message); }
    finally { busy = false; archive.disabled = false; await refresh(); }
  });
  reset.addEventListener('click', async () => {
    if (!confirm('Reset về tick 0, điểm của các đội về 0 và xóa lịch sử kiểm tra ForcAD? Hãy dừng và chờ ít nhất 30 giây trước khi reset.')) return;
    busy = true; reset.disabled = true; showFlash('');
    try {
      await post('/api/admin/round-control/reset/', {confirm:'RESET'});
      alert('Đã reset tick và điểm của các đội về 0.');
      location.reload();
    } catch (err) { showFlash('Không reset được: ' + err.message); }
    finally { busy = false; reset.disabled = false; }
  });
  refresh(); setInterval(refresh, 5000);
})();
