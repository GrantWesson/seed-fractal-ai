/*
 * Branch-free reference kernels for Seed-Fractal AI
 *
 * Compile:
 *   gcc -O3 -march=native -fno-exceptions -fno-asynchronous-unwind-tables \
 *       -o seed_kernels_test native/seed_kernels.c
 *
 * Measure cache behaviour (Linux):
 *   perf stat -e cache-references,cache-misses,branches,branch-misses \
 *       ./seed_kernels_test
 *
 * Design:
 *   - No data-dependent branches in the hot functions.
 *   - All memory traffic is sequential / aligned loads & stores
 *     into a single contiguous buffer.
 *   - Both single-word and spanning cases are computed; a mask selects.
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define ARENA_WORDS (1u << 20)   /* 8 MiB of uint64 */

static uint64_t arena[ARENA_WORDS];

/* branchless select */
static inline uint64_t sel(uint64_t cond /* 0 or 1 */, uint64_t a, uint64_t b) {
    /* mask = 0 or ~0 */
    uint64_t mask = (uint64_t)0 - cond;
    return (a & mask) | (b & ~mask);
}

/* Extract 1..64 bits, completely branch-free */
static inline uint64_t read_bits(uint64_t bit_offset, unsigned n_bits) {
    n_bits = 1u + ((n_bits - 1u) & 63u);          /* clamp 1..64 */
    uint64_t word_idx = bit_offset >> 6;
    unsigned shift    = (unsigned)(bit_offset & 63);
    uint64_t mask     = (n_bits == 64) ? ~0ULL : ((1ULL << n_bits) - 1ULL);

    uint64_t w0 = arena[word_idx];
    uint64_t w1 = arena[word_idx + 1 < ARENA_WORDS ? word_idx + 1 : word_idx];

    uint64_t single   = (w0 >> shift) & mask;
    uint64_t low      =  w0 >> shift;
    uint64_t high     =  w1 << ((64u - shift) & 63u);
    uint64_t spanning = (low | high) & mask;

    uint64_t fits = (shift + n_bits <= 64);
    return sel(fits, single, spanning);
}

/* Deposit 1..64 bits, branch-free */
static inline void write_bits(uint64_t bit_offset, unsigned n_bits, uint64_t value) {
    n_bits = 1u + ((n_bits - 1u) & 63u);
    uint64_t word_idx = bit_offset >> 6;
    unsigned shift    = (unsigned)(bit_offset & 63);
    uint64_t mask     = (n_bits == 64) ? ~0ULL : ((1ULL << n_bits) - 1ULL);
    value &= mask;

    uint64_t fits = (shift + n_bits <= 64);

    /* single-word path */
    uint64_t single_clear = ~(mask << shift);
    uint64_t single_new   = (arena[word_idx] & single_clear) | (value << shift);

    /* spanning path */
    unsigned bits_in_first = 64u - shift;
    uint64_t low_mask      = (1ULL << bits_in_first) - 1ULL;
    uint64_t high_bits     = n_bits - bits_in_first;
    uint64_t high_mask     = (high_bits & 63u) ? ((1ULL << (high_bits & 63u)) - 1ULL) : 0ULL;

    uint64_t low_new  = (arena[word_idx] & ~(low_mask << shift)) | ((value & low_mask) << shift);
    uint64_t high_new = (arena[word_idx + 1] & ~high_mask) | ((value >> bits_in_first) & high_mask);

    uint64_t word0 = sel(fits, single_new, low_new);
    uint64_t word1 = sel(fits, arena[word_idx + 1], high_new);

    arena[word_idx]     = word0;
    arena[word_idx + 1] = word1;   /* when fits==1 this is a silent store of old value */
}

/* Trivial involutive permute for the test harness */
static inline uint64_t involute(uint64_t x, uint64_t seed) {
    x ^= seed;
    x = (x << 13) | (x >> 51);
    x ^= seed >> 7;
    return x;
}

int main(void) {
    /* Touch the whole arena once so pages are resident */
    memset(arena, 0, sizeof(arena));

    const int N = 2000000;
    uint64_t checksum = 0;
    clock_t t0 = clock();

    for (int i = 0; i < N; i++) {
        uint64_t q   = (uint64_t)i * 0x9E3779B97F4A7C15ULL;
        uint64_t addr = (involute(q, 0xDEADBEEF) & (ARENA_WORDS * 64 - 128)) & ~63ULL;
        write_bits(addr, 32, q & 0xFFFFFFFFULL);
        write_bits(addr + 32, 32, (q >> 32));
        uint64_t back = read_bits(addr, 32);
        checksum ^= back;
    }

    clock_t t1 = clock();
    double secs = (double)(t1 - t0) / CLOCKS_PER_SEC;

    printf("iterations : %d\n", N);
    printf("checksum   : 0x%016llx\n", (unsigned long long)checksum);
    printf("time       : %.3f s\n", secs);
    printf("ns / op    : %.2f\n", (secs * 1e9) / N);
    return 0;
}
