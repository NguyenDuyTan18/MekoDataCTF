<template>
    <component :is="layout">
        <router-view />
    </component>
</template>

<script>
import '@/assets/table.scss';

export default {
    computed: {
        layout() {
            return this.$route.meta.layout || 'default-layout';
        },
    },
};
</script>

<style lang="scss">
*,
*::before,
*::after {
    box-sizing: border-box;
}

html,
body {
    height: 100%;
    margin: 0;
}

body {
    background:
        var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 15px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
}

a {
    color: var(--accent-teal);
}

button {
    font-family: inherit;
}

/* Nút dùng chung cho các trang quản trị */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 9px 16px;
    border-radius: 9px;
    border: 1px solid var(--line-strong);
    background: var(--panel);
    color: var(--text);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;

    &:hover {
        background: var(--panel-hi);
        border-color: var(--accent-teal);
    }

    &:focus-visible {
        outline: 2px solid var(--accent-teal);
        outline-offset: 2px;
    }
}

.btn-primary {
    background: var(--accent-strong);
    border-color: var(--accent-strong);
    color: #fff;

    &:hover {
        background: #1d4fd7;
        border-color: #1d4fd7;
        color: #fff;
    }
}

/* Bảng/khung của các trang quản trị cũ dùng nền sáng mặc định */
input,
select,
textarea {
    font-family: inherit;
    font-size: 0.95rem;
    padding: 9px 12px;
    border-radius: 8px;
    border: 1px solid var(--line-strong);
    background: #11161f;
    color: var(--text);

    &:focus {
        outline: none;
        border-color: var(--accent-teal);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
    }
}
</style>
