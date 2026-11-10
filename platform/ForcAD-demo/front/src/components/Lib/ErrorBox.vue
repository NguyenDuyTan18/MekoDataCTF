<template>
    <div>
        <p v-if="error !== null" class="error-message">
            {{ error }}
        </p>
        <slot v-else />
    </div>
</template>

<script>
export default {
    props: {
        error: {
            validator: (prop) => typeof prop === 'string' || prop === null,
            required: true,
        },
    },
};
</script>

<style lang="scss" scoped>
.error-message {
    max-width: 760px;
    margin: 0 auto;
    padding: 12px 16px;
    border-radius: 8px;
    color: #fecaca;
    background: #2a1719;
    border: 1px solid #4a2326;
}
</style>
