<template>
    <form class="fw" :class="{ 'fw--narrow': narrow }" @submit.prevent="handleSubmit">
        <div class="fw-head">
            <div>
                <p v-if="kicker" class="fw-kicker">{{ kicker }}</p>
                <h1 class="fw-title">{{ title }}</h1>
            </div>
            <slot name="actions" />
        </div>
        <div class="fw-body">
            <slot />
        </div>
        <p v-if="error !== null" class="fw-error" role="alert">
            {{ error }}
        </p>
        <p v-else-if="success" class="fw-success" role="status">
            {{ success }}
        </p>
        <div class="fw-foot">
            <slot name="footer" />
            <button type="submit" class="btn btn-primary" :disabled="busy">
                {{ busy ? 'Đang xử lý…' : submitLabel }}
            </button>
        </div>
    </form>
</template>

<script>
// Rút thông báo dễ đọc từ lỗi axios: ưu tiên {error} hoặc chuỗi backend trả về.
function readableError(e) {
    const data = e && e.response && e.response.data;
    if (data && typeof data === 'object' && data.error) return String(data.error);
    if (typeof data === 'string' && data.trim() && data.length < 300) return data;
    if (e && e.response && e.response.status === 401) return 'Sai tên đăng nhập hoặc mật khẩu.';
    if (e && e.response && e.response.status === 403) return 'Không có quyền thực hiện thao tác này.';
    if (e && e.response) return `Máy chủ trả lỗi HTTP ${e.response.status}.`;
    return (e && e.message) || 'Không kết nối được máy chủ.';
}

export default {
    props: {
        title: {
            type: String,
            required: true,
        },
        kicker: {
            type: String,
            default: '',
        },
        submitLabel: {
            type: String,
            default: 'Lưu',
        },
        successMessage: {
            type: String,
            default: '',
        },
        narrow: Boolean,
        submitCallback: {
            type: Function,
            required: true,
        },
    },

    data: function () {
        return {
            error: null,
            success: '',
            busy: false,
        };
    },

    methods: {
        handleSubmit: async function () {
            this.busy = true;
            this.error = null;
            this.success = '';
            try {
                await this.submitCallback();
                this.success = this.successMessage;
            } catch (e) {
                console.error(e);
                this.error = readableError(e);
            } finally {
                this.busy = false;
            }
        },
    },
};
</script>

<style lang="scss">
/* Không scoped: các trường (.fw-field…) nằm trong slot của component cha. */
.fw {
    max-width: 760px;
    margin: 0 auto;
    background: var(--panel);
    border: 1px solid #2a3344;
    border-radius: 12px;
    overflow: hidden;

    &--narrow {
        max-width: 400px;
    }
}

.fw-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 20px;
    background: var(--panel-hi);
    border-bottom: 1px solid #2a3344;
}

.fw-kicker {
    margin: 0;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--label);
}

.fw-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #f1f4fa;
}

.fw-body {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 16px;
    padding: 18px 20px;

    .fw--narrow & {
        grid-template-columns: 1fr;
    }
}

.fw-section {
    grid-column: 1 / -1;
    margin: 6px 0 -4px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--label);

    &:first-child {
        border-top: 0;
        padding-top: 0;
        margin-top: 0;
    }
}

.fw-field {
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 0;
    font-size: 12.5px;
    color: #9aa6bd;

    &--wide {
        grid-column: 1 / -1;
    }

    input:not([type='checkbox']),
    select {
        width: 100%;
    }

    small {
        color: var(--text-dim);
        font-size: 11.5px;
    }
}

.fw-mono input {
    font-family: var(--mono);
}

.fw-check {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #11161f;
    cursor: pointer;
    font-size: 13px;
    color: var(--text);

    input {
        margin: 2px 0 0;
        width: 16px;
        height: 16px;
        accent-color: var(--accent);
    }

    small {
        display: block;
        color: var(--text-dim);
        font-size: 11.5px;
    }
}

.fw-error,
.fw-success {
    margin: 0 20px 4px;
    padding: 9px 12px;
    border-radius: 8px;
    font-size: 13px;
}

.fw-error {
    color: #fecaca;
    background: #2a1719;
    border: 1px solid #4a2326;
}

.fw-success {
    color: #bbf7d0;
    background: #12281d;
    border: 1px solid #1f4a33;
}

.fw-foot {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    padding: 14px 20px;
    border-top: 1px solid var(--line);
    background: #11161f;

    .btn-primary {
        min-width: 110px;
        justify-content: center;
    }

    .btn:disabled {
        opacity: 0.55;
        cursor: wait;
    }
}

@media (max-width: 640px) {
    .fw-body {
        grid-template-columns: 1fr;
    }
}
</style>
