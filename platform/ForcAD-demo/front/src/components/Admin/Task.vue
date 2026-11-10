<template>
    <form-wrapper
        v-if="task !== null"
        kicker="Quản lý dịch vụ"
        :title="message"
        :success-message="taskId ? 'Đã lưu thay đổi.' : ''"
        :submit-callback="submitForm"
    >
        <template #actions>
            <router-link to="/admin/" class="btn">← Danh sách</router-link>
        </template>
        <p class="fw-section">Thông tin</p>
        <label class="fw-field">
            Tên dịch vụ
            <input v-model.trim="task.name" type="text" />
        </label>
        <label class="fw-field fw-mono">
            Đường dẫn checker
            <input v-model.trim="task.checker" type="text" />
            <small>Ví dụ /checkers/meko_boutique/sqli.py</small>
        </label>
        <label class="fw-field fw-mono">
            Kiểu checker
            <input v-model.trim="task.checker_type" type="text" />
            <small>hackerdom, hackerdom_pfr…</small>
        </label>
        <label class="fw-field fw-mono">
            Env path
            <input v-model.trim="task.env_path" type="text" />
        </label>
        <p class="fw-section">Checker</p>
        <label class="fw-field">
            Số lần PUT mỗi tick
            <input v-model.number="task.puts" type="number" />
        </label>
        <label class="fw-field">
            Số lần GET mỗi tick
            <input v-model.number="task.gets" type="number" />
        </label>
        <label class="fw-field">
            Số vị trí đặt flag
            <input v-model.number="task.places" type="number" />
        </label>
        <label class="fw-field">
            Timeout checker (giây)
            <input v-model.number="task.checker_timeout" type="number" />
        </label>
        <label class="fw-field">
            Chu kỳ GET (giây)
            <input v-model.number="task.get_period" type="number" />
        </label>
        <label class="fw-field">
            Điểm mặc định
            <input v-model.number="task.default_score" type="number" />
        </label>
        <p class="fw-section">Trạng thái</p>
        <label class="fw-check fw-field--wide">
            <input
                type="checkbox"
                :checked="task.active"
                @change="task.active = $event.target.checked"
            />
            <span>Đang hoạt động<small>Tắt thì checker không chạy và dịch vụ bị ẩn khỏi bảng điểm.</small></span>
        </label>
    </form-wrapper>
</template>

<script>
import FormWrapper from '@/components/Lib/FormWrapper.vue';

export default {
    components: { FormWrapper },

    data: function () {
        return {
            task: null,
            taskId: null,
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
            this.taskId = this.$route.params.id;
            if (!this.taskId) {
                this.task = {
                    name: '',
                    checker: '',
                    gets: 1,
                    puts: 1,
                    places: 1,
                    checker_timeout: 20,
                    checker_type: 'hackerdom',
                    env_path: '',
                    get_period: 10,
                    default_score: 2500,
                    active: true,
                };
                this.message = 'Thêm dịch vụ mới';
            } else {
                const { data: task } = await this.$http.get(
                    `/admin/tasks/${this.taskId}/`
                );
                this.task = task;
                this.message = `${this.task.name} · #${this.task.id}`;
            }
        },
        submitForm: async function () {
            if (!this.taskId) {
                const { data: task } = await this.$http.post(
                    '/admin/tasks/',
                    this.task
                );
                this.$router
                    .push({ name: 'taskAdmin', params: { id: task.id } })
                    .catch(() => {});
            } else {
                const { data: task } = await this.$http.put(
                    `/admin/tasks/${this.taskId}/`,
                    this.task
                );
                this.task = task;
                await this.updateData();
            }
        },
    },
};
</script>

<style lang="scss" scoped></style>
