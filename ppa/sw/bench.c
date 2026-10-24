/* Small integer workload: xorshift PRNG, bubble sort, CRC32. No mul/div. */
#include <stdint.h>
#define N 20
static int32_t a[N];
static uint32_t crc_step(uint32_t crc, uint32_t b) {
    crc ^= b;
    for (int i = 0; i < 8; i++)
        crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    return crc;
}
int main(void) {
    uint32_t s = 2463534242u;
    for (int i = 0; i < N; i++) {
        s ^= s << 13; s ^= s >> 17; s ^= s << 5;
        a[i] = (int32_t)s;
    }
    for (int i = 0; i < N - 1; i++)
        for (int j = 0; j < N - 1 - i; j++)
            if (a[j] > a[j + 1]) { int32_t t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
    uint32_t crc = 0xFFFFFFFFu;
    for (int i = 0; i < N; i++) {
        crc = crc_step(crc, (uint32_t)a[i] & 0xFF);
        crc = crc_step(crc, ((uint32_t)a[i] >> 8) & 0xFF);
    }
    return (int)(crc ^ (uint32_t)a[0] ^ ((uint32_t)a[N - 1] >> 3));
}
