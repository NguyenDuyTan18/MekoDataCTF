<template>
    <form-wrapper
        v-if="team !== null"
        kicker="Quản lý đội"
        :title="message"
        :success-message="teamId ? 'Đã lưu thay đổi.' : ''"
        :submit-callback="submitForm"
    >
        <template #actions>
            <router-link to="/admin/" class="btn">← Danh sách</router-link>
        </template>
        <p class="fw-section">Thông tin đội</p>
        <label class="fw-field">
            Tên đội
            <input v-model.trim="team.name" type="text" required />
        </label>
        <label class="fw-field fw-mono">
            IP dịch vụ
            <input
                v-model.trim="team.ip"
                type="text"
                placeholder="10.90.0.11"
                required
            />
            <small>Checker và đội khác tấn công vào địa chỉ này.</small>
        </label>
        <label class="fw-field fw-field--wide fw-mono">
            Token nộp flag
            <span class="token-row">
                <input v-model.trim="team.token" type="text" required />
                <button type="button" class="btn" @click="generateToken">
                    Tạo mới
                </button>
            </span>
            <small>Đội dùng token này ở trang Nộp flag. Đổi token thì token cũ hết hiệu lực.</small>
        </label>
        <p class="fw-section">Trạng thái</p>
        <label class="fw-check">
            <input
                type="checkbox"
                :checked="team.active"
                @change="team.active = $event.target.checked"
            />
            <span>Đang thi<small>Tắt thì đội bị ẩn khỏi bảng điểm và không được chấm.</small></span>
        </label>
        <label class="fw-check">
            <input
                type="checkbox"
                :checked="team.highlighted"
                @change="team.highlighted = $event.target.checked"
            />
            <span>Làm nổi bật<small>Tô sáng dòng của đội trên bảng điểm.</small></span>
        </label>
    </form-wrapper>
</template>

<script>
import FormWrapper from '@/components/Lib/FormWrapper.vue';

export default {
    components: { FormWrapper },

    data: function () {
        return {
            error: null,
            team: null,
            teamId: null,
            message: null,
        };
    },

    watch: {
        $route: async function () {
            await this.updateData();
        },
    },

    created: async function () {
        await this.updateData();
    },

    methods: {
        updateData: async function () {
            this.teamId = this.$route.params.id;
            if (!this.teamId) {
                this.team = {
                    name: '',
                    ip: '',
                    token: '',
                    highlighted: false,
                    active: true,
                };
                this.message = 'Thêm đội mới';
            } else {
                const { data: team } = await this.$http.get(
                    `/admin/teams/${this.teamId}/`
                );
                this.team = team;
                this.message = `${this.team.name} · #${this.team.id}`;
            }
        },
        generateToken: function () {
            const bytes = new Uint8Array(8);
            window.crypto.getRandomValues(bytes);
            this.team.token = Array.from(bytes, (b) =>
                b.toString(16).padStart(2, '0')
            ).join('');
        },
        submitForm: async function () {
            if (!this.teamId) {
                const { data: team } = await this.$http.post(
                    '/admin/teams/',
                    this.team
                );
                this.$router
                    .push({ name: 'teamAdmin', params: { id: team.id } })
                    .catch(() => {});
            } else {
                const { data: team } = await this.$http.put(
                    `/admin/teams/${this.teamId}/`,
                    this.team
                );
                this.team = team;
                await this.updateData();
            }
        },
    },
};
</script>

<style lang="scss" scoped>
.token-row {
    display: flex;
    gap: 8px;

    input {
        flex: 1;
    }
}
</style>
