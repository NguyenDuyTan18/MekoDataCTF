<template>
    <div>
        <div class="page-head">
            <div>
                <p class="page-kicker">Bảng điều khiển BTC</p>
                <h1 class="page-title">Bảng điểm quản trị</h1>
            </div>
            <div class="page-actions">
                <a class="btn" href="/"><i class="fas fa-sliders-h" /> Điều khiển round</a>
                <a class="btn" href="/submit.html"><i class="fas fa-flag" /> Bản đồ flag</a>
                <span class="page-sep" />
                <button class="btn" @click="createTask">
                    <i class="fas fa-plus" /> Thêm dịch vụ
                </button>
                <button class="btn btn-primary" @click="createTeam">
                    <i class="fas fa-plus" /> Thêm đội
                </button>
            </div>
        </div>
        <p class="page-hint">
            <i class="fas fa-edit" /> cạnh tên đội hoặc dịch vụ để sửa (token, IP,
            bật/tắt). <i class="fas fa-history" /> trong từng ô để xem lịch sử
            checker của đội ở dịch vụ đó.
        </p>
        <statuses />
        <admin-scoreboard />
    </div>
</template>

<script>
import AdminScoreboard from '@/components/Admin/Scoreboard.vue';
import Statuses from '@/components/General/Statuses.vue';

export default {
    components: {
        AdminScoreboard,
        Statuses,
    },

    methods: {
        createTask: async function () {
            this.$router.push({ name: 'createTask' }).catch(() => {});
        },

        createTeam: async function () {
            this.$router.push({ name: 'createTeam' }).catch(() => {});
        },
    },
};
</script>

<style lang="scss" scoped>
.page-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}

.page-kicker {
    margin: 0 0 2px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-teal);
}

.page-title {
    margin: 0;
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--text);
}

.page-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;

    a.btn {
        text-decoration: none;
    }
}

.page-sep {
    width: 1px;
    height: 24px;
    background: var(--line-strong);
    margin: 0 4px;
}

.page-hint {
    margin: -8px 0 18px;
    font-size: 12.5px;
    color: var(--text-dim);
}
</style>
