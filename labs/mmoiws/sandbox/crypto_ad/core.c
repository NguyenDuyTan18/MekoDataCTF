#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <immintrin.h>
#include <omp.h>

static inline __m128i run(__m128i *k, __m128i x) {
    x = _mm_xor_si128(x, k[0]);
    x = _mm_aesenc_si128(x, k[1]);
    x = _mm_aesenc_si128(x, k[2]);
    x = _mm_aesenc_si128(x, k[3]);
    x = _mm_aesenc_si128(x, k[4]);
    x = _mm_aesenc_si128(x, k[5]);
    return _mm_aesenclast_si128(x, k[6]);
}

void encrypt_many(const uint8_t *rk, const uint8_t *in, uint8_t *out, size_t count) {
    __m128i k[7];
    for (int i = 0; i < 7; i++) k[i] = _mm_loadu_si128((const __m128i*)(rk+16*i));
    for (size_t i = 0; i < count; i++) {
        __m128i x = _mm_loadu_si128((const __m128i*)(in+16*i));
        x = run(k, x);
        _mm_storeu_si128((__m128i*)(out+16*i), x);
    }
}

int make_bitmap(const uint8_t *rk, const uint8_t *base, uint64_t count, uint32_t group, const char *fname) {
    if (count > (1ULL<<32) || group >= 4) return -1;
    static const uint8_t pos[4][4] = {
        {0, 13, 10, 7},
        {4, 1, 14, 11},
        {8, 5, 2, 15},
        {12, 9, 6, 3}
    };
    const uint8_t *loc = pos[group];
    const uint64_t words = (1ULL<<26)+1;
    uint64_t *bits = (uint64_t*)calloc(words, sizeof(uint64_t));
    if (!bits) return -2;
    __m128i k[7];
    for (int i=0;i<7;i++) k[i] = _mm_loadu_si128((const __m128i*)(rk+16*i));
    #pragma omp parallel
    {
        uint8_t p[16], c[16];
        memcpy(p, base, 16);
        #pragma omp for schedule(static)
        for (uint64_t i=0;i<count;i++) {
            p[0] = (uint8_t)i;
            p[5] = (uint8_t)(i>>8);
            p[10] = (uint8_t)(i>>16);
            p[15] = (uint8_t)(i>>24);
            __m128i x = run(k, _mm_loadu_si128((const __m128i*)p));
            _mm_storeu_si128((__m128i*)c, x);
            uint32_t idx = ((uint32_t)c[loc[3]]<<24) | ((uint32_t)c[loc[2]]<<16) | ((uint32_t)c[loc[1]]<<8) | c[loc[0]];
            __atomic_fetch_xor(bits + (idx>>6), 1ULL << (idx&63), __ATOMIC_RELAXED);
        }
    }
    FILE *fp = fopen(fname, "wb");
    if (!fp) {free(bits);return -3;}
    uint64_t header[2] = {(1ULL<<32), 0};
    int ok = fwrite(header,1,sizeof(header),fp) == sizeof(header)
          && fwrite(bits,sizeof(uint64_t),words,fp) == words;
    int close_ok = fclose(fp) == 0;
    ok = ok && close_ok;
    free(bits);
    return ok ? 0 : -4;
}
