<template>
    <div class="login-page">
        <form-wrapper
            narrow
            kicker="MekoDataCTF · Ban tổ chức"
            title="Đăng nhập quản trị"
            submit-label="Đăng nhập"
            :submit-callback="submitCallback"
        >
            <label class="fw-field">
                Tên đăng nhập
                <input
                    v-model.trim="username"
                    type="text"
                    name="username"
                    autocomplete="username"
                    autofocus
                    required
                />
            </label>
            <label class="fw-field">
                Mật khẩu
                <input
                    v-model="password"
                    type="password"
                    name="password"
                    autocomplete="current-password"
                    required
                />
            </label>
            <template #footer>
                <router-link to="/" class="login-back">← Về trang chính</router-link>
            </template>
        </form-wrapper>
        <p class="login-hint">
            Tài khoản quản trị nằm trong block <code>admin:</code> của
            <code>config.yml</code>.
        </p>
    </div>
</template>

<script>
import FormWrapper from '@/components/Lib/FormWrapper.vue';

export default {
    components: {
        FormWrapper,
    },

    data: function () {
        return {
            username: '',
            password: '',
        };
    },

    methods: {
        submitCallback: async function () {
            await this.$http.post('/admin/login/', {
                username: this.username,
                password: this.password,
            });
            // Quay về trang được yêu cầu trước khi bị chuyển sang đăng nhập (nếu có).
            const next = this.$route.query.next;
            if (typeof next === 'string' && next.startsWith('/')) {
                window.location.assign(next);
                return;
            }
            this.$router.push({ name: 'admin' }).catch(() => {});
        },
    },
};
</script>

<style lang="scss" scoped>
.login-page {
    padding-top: 8vh;
}

.login-back {
    margin-right: auto;
    font-size: 13px;
    color: var(--text-dim);
    text-decoration: none;

    &:hover {
        color: var(--accent-teal);
    }
}

.login-hint {
    max-width: 400px;
    margin: 14px auto 0;
    text-align: center;
    font-size: 12px;
    color: var(--text-dim);

    code {
        font-family: var(--mono);
        color: #c4ccdd;
    }
}
</style>
