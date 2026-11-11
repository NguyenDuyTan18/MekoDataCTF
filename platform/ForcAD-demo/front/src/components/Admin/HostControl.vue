<template>
    <section class="host">
        <div class="host-head">
            <div>
                <p class="host-kicker">Máy chủ · {{ info.pool || 'pool' }} · {{ info.labs || '' }}</p>
                <h2 class="host-title">Hệ thống bộ cờ</h2>
            </div>
            <div class="host-actions">
                <button
                    class="btn"
                    :class="collectorOn ? 'btn-stop' : 'btn-primary'"
                    :disabled="busy || offline"
                    @click="toggleFlagSystem"
                >
                    <i :class="collectorOn ? 'fas fa-stop' : 'fas fa-flag'" />
                    {{ collectorOn ? 'Dừng bộ cờ' : 'Bật bộ cờ' }}
                </button>
                <button
                    class="btn"
                    :class="{ 'btn-stop': gatewayOn }"
                    :disabled="busy || offline"
                    @click="toggleGateway"
                >
                    <i :class="gatewayOn ? 'fas fa-stop' : 'fas fa-network-wired'" />
                    {{ gatewayOn ? 'Dừng gateway' : 'Thêm gateway trung gian' }}
                </button>
            </div>
        </div>

        <p v-if="error" class="host-error" role="alert">{{ error }}</p>
        <p v-if="info.config_error" class="host-error" role="alert">
            Cấu hình lỗi: {{ info.config_error }} — sửa khoi-dong/cau-hinh.conf
            (xem nhanh: python khoi-dong/meko.py config).
        </p>

        <div v-if="!offline && loaded" class="host-grid">
            <div class="host-cell">
                <small>Dịch vụ cờ</small>
                <b :class="servicesOk ? 'ok' : 'bad'">
                    {{ servicesUp }} / {{ servicesTotal }} đang chạy
                </b>
                <span v-if="!servicesOk && downList" class="hint">Chưa chạy: {{ downList }}</span>
            </div>
            <div class="host-cell">
                <small>Collector</small>
                <b :class="collectorOn ? 'ok' : 'bad'">
                    {{ collectorOn ? 'Đang chạy' : 'Đã dừng' }}
                </b>
                <span v-if="collectorOn" class="hint">PID {{ info.collector.pids.join(', ') }}</span>
            </div>
            <div class="host-cell">
                <small>SSH tới máy chấm</small>
                <b :class="sshClass">{{ sshText }}</b>
                <span class="hint">{{ sshHint }}</span>
            </div>
            <div class="host-cell">
                <small>Thao tác gần nhất</small>
                <b :class="jobClass">{{ jobText }}</b>
                <span v-if="info.job && info.job.message" class="hint">{{ info.job.message }}</span>
            </div>
        </div>

        <details v-if="!offline && gatewayOn && gatewayPorts.length" class="host-log">
            <summary>Cổng gateway trung gian ({{ gatewayPorts.length }} dịch vụ VM)</summary>
            <pre>{{ gatewayPorts.map(p => p.url + '  ->  ' + p.target).join('\n') }}</pre>
        </details>
        <details v-if="!offline && info.collector && info.collector.log.length" class="host-log">
            <summary>Nhật ký collector (15 dòng cuối)</summary>
            <pre>{{ info.collector.log.join('\n') }}</pre>
        </details>
    </section>
</template>

<script>
export default {
    data: function () {
        return {
            info: {},
            loaded: false,
            offline: false,
            error: null,
            sending: false,
            timer: null,
        };
    },

    computed: {
        collectorOn() {
            return !!(this.info.collector && this.info.collector.running);
        },
        gatewayOn() {
            return !!(this.info.gateway && this.info.gateway.running);
        },
        gatewayPorts() {
            return (this.info.gateway && this.info.gateway.ports) || [];
        },
        jobRunning() {
            return !!(this.info.job && this.info.job.state === 'running');
        },
        busy() {
            return this.sending || this.jobRunning;
        },
        serviceStates() {
            return this.info.services || {};
        },
        servicesTotal() {
            return Object.keys(this.serviceStates).length;
        },
        servicesUp() {
            return Object.values(this.serviceStates).filter((s) => s === 'running').length;
        },
        servicesOk() {
            return this.servicesTotal > 0 && this.servicesUp === this.servicesTotal;
        },
        downList() {
            return Object.entries(this.serviceStates)
                .filter(([, s]) => s !== 'running')
                .map(([name]) => name)
                .join(', ');
        },
        sshText() {
            const ssh = this.info.ssh || {};
            return ssh.ok === null || ssh.ok === undefined ? 'Đang kiểm tra…' : ssh.ok ? 'OK' : 'Lỗi';
        },
        sshClass() {
            const ssh = this.info.ssh || {};
            return ssh.ok ? 'ok' : ssh.ok === false ? 'bad' : '';
        },
        sshHint() {
            const ssh = this.info.ssh || {};
            if (!ssh.checked_at) return 'Tự kiểm tra mỗi phút';
            const ago = Math.max(0, Math.round(Date.now() / 1000 - ssh.checked_at));
            return (ssh.ok ? '' : ssh.message + ' · ') + `kiểm tra ${ago}s trước`;
        },
        jobText() {
            const job = this.info.job;
            if (!job) return '—';
            const state = { running: 'đang chạy…', done: 'xong', failed: 'lỗi' }[job.state] || job.state;
            return `${job.label}: ${state}`;
        },
        jobClass() {
            const job = this.info.job;
            return !job ? '' : job.state === 'done' ? 'ok' : job.state === 'failed' ? 'bad' : 'warn';
        },
    },

    created: function () {
        this.refresh();
    },

    beforeDestroy: function () {
        clearTimeout(this.timer);
    },

    methods: {
        refresh: async function () {
            clearTimeout(this.timer);
            try {
                const { data } = await this.$http.get('/admin/host/status/');
                this.info = data;
                this.offline = false;
                if (this.error && !this.sending) this.error = null;
            } catch (e) {
                const data = e.response && e.response.data;
                this.offline = !!(data && data.offline) || !e.response;
                this.error = (data && data.error) || 'Không lấy được trạng thái cầu nối.';
            } finally {
                this.loaded = true;
                this.timer = setTimeout(this.refresh, this.jobRunning ? 2000 : 5000);
            }
        },
        act: async function (action, question) {
            if (question && !confirm(question)) return;
            this.sending = true;
            this.error = null;
            try {
                await this.$http.post(`/admin/host/${action}/`);
            } catch (e) {
                const data = e.response && e.response.data;
                this.error = (data && data.error) || 'Không gửi được lệnh tới cầu nối.';
            } finally {
                this.sending = false;
                this.refresh();
            }
        },
        toggleFlagSystem: function () {
            // Một nút: chưa chạy -> bật dịch vụ cờ + collector; đang chạy -> dừng collector (giữ Docker/bảng điểm).
            if (this.collectorOn) {
                this.act('collector/stop', 'Dừng bộ cờ? Collector dừng nên checker KHÔNG cắm được cờ; nếu round đang chạy, các đội sẽ bị chấm sập. Bảng điểm vẫn chạy.');
            } else {
                this.act('flag-system/start', 'Bật bộ cờ: khởi động dịch vụ cờ (ticker, celery, bộ nhận cờ…) và collector?');
            }
        },
        toggleGateway: function () {
            // Tunnel SSH mở mỗi dịch vụ VM ra một cổng cục bộ (xem bảng cổng bên dưới).
            if (this.gatewayOn) {
                this.act('gateway/stop', 'Dừng gateway trung gian? Các cổng chuyển tiếp tới dịch vụ VM sẽ đóng.');
            } else {
                this.act('gateway/start', 'Mở gateway trung gian: tunnel SSH qua pool, mỗi dịch vụ VM một cổng cục bộ?');
            }
        },
    },
};
</script>

<style lang="scss" scoped>
.host {
    margin-bottom: 20px;
    background: var(--panel);
    border: 1px solid #2a3344;
    border-radius: 12px;
    overflow: hidden;
}

.host-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    padding: 14px 20px;
    background: var(--panel-hi);
    border-bottom: 1px solid #2a3344;
}

.host-kicker {
    margin: 0;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--label);
}

.host-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #f1f4fa;
}

.host-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
}

.btn-stop {
    background: #b45309;
    border-color: #b45309;
    color: #fff;

    &:hover {
        background: #92400e;
        border-color: #92400e;
    }
}

.host-error {
    margin: 0;
    padding: 10px 20px;
    font-size: 13px;
    color: #fecaca;
    background: #2a1719;
    border-bottom: 1px solid #4a2326;
}

.host-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    background: var(--line);
}

.host-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    padding: 12px 20px;
    background: var(--panel);

    small {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--label);
    }

    b {
        font-size: 15px;
        font-weight: 600;
        color: #f1f4fa;

        &.ok {
            color: var(--good);
        }

        &.bad {
            color: var(--bad);
        }

        &.warn {
            color: #fbbf24;
        }
    }

    .hint {
        font-size: 12px;
        color: var(--text-dim);
        overflow-wrap: anywhere;
    }
}

.host-log {
    border-top: 1px solid var(--line);

    summary {
        cursor: pointer;
        padding: 9px 20px;
        font-size: 13px;
        color: #c4ccdd;
    }

    pre {
        margin: 0;
        padding: 10px 20px 14px;
        max-height: 260px;
        overflow: auto;
        font: 12px/1.5 var(--mono);
        color: #c4ccdd;
        background: #11161f;
        white-space: pre-wrap;
    }
}

@media (max-width: 900px) {
    .host-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
