/*
 * stress_c_01_buffer_overflow.c
 * ByteSized Stress Suite — C: buffer overflows, format string attacks, OOB reads
 *
 * Compile: gcc -O0 -fsanitize=address -g stress_c_01_buffer_overflow.c -o buf_overflow
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUFFER_SIZE 64

/* ==============================================================
 * ANTI-PATTERN 1: gets() — no boundary check (CWE-242)
 * Removed from C11 standard; any input > buffer causes overflow.
 * ============================================================== */
void gets_overflow_demo(void) {
    char buf[BUFFER_SIZE];
    printf("Enter input (gets — no length check): ");
    /* HAZARD (CWE-242): gets() writes unboundedly into buf */
    gets(buf);
    printf("You entered: %s\n", buf);
}

/* ==============================================================
 * ANTI-PATTERN 2: strcpy() without size check (CWE-120)
 * ============================================================== */
void strcpy_overflow_demo(const char *user_input) {
    char dest[BUFFER_SIZE];
    /* HAZARD (CWE-120): if strlen(user_input) >= BUFFER_SIZE, overflows dest */
    strcpy(dest, user_input);
    printf("Copied: %s\n", dest);
}

/* ==============================================================
 * ANTI-PATTERN 3: sprintf() without bounds (CWE-134)
 * ============================================================== */
void sprintf_overflow_demo(const char *user_name) {
    char message[BUFFER_SIZE];
    /* HAZARD (CWE-134): sprintf writes past message if user_name is long */
    sprintf(message, "Hello, %s! Welcome to the system.", user_name);
    printf("%s\n", message);
}

/* ==============================================================
 * ANTI-PATTERN 4: Off-by-one error in array indexing
 * ============================================================== */
void off_by_one_demo(void) {
    int arr[10];
    /* HAZARD: loop runs i <= 10, writing arr[10] which is out of bounds */
    for (int i = 0; i <= 10; i++) {
        arr[i] = i * i;   /* i=10 → OOB write */
    }
    printf("arr[9]=%d  arr[10]=%d (OOB read)\n", arr[9], arr[10]);
}

/* ==============================================================
 * ANTI-PATTERN 5: Unvalidated format string from user (CWE-134)
 * ============================================================== */
void format_string_attack(const char *user_fmt) {
    char output[256];
    /* HAZARD (CWE-134): user controls the format string — can leak stack,
     * write arbitrary memory with %n, or crash with mismatched specifiers. */
    sprintf(output, user_fmt);   /* NOT: snprintf(output, sizeof(output), "%s", user_fmt) */
    printf(user_fmt);            /* HAZARD: printf(user_controlled_string) */
}

/* ==============================================================
 * ANTI-PATTERN 6: Stack smashing via nested strcpy
 * ============================================================== */
typedef struct {
    char name[32];
    int  access_level;    /* overwritten if name overflows */
    char role[32];
} UserRecord;

void process_user_record(const char *name, const char *role) {
    UserRecord rec;
    rec.access_level = 0;   /* default: unprivileged */
    /* HAZARD: both strcpy calls can overflow into adjacent fields or return addr */
    strcpy(rec.name, name);
    strcpy(rec.role, role);
    printf("User: %s  Access: %d  Role: %s\n", rec.name, rec.access_level, rec.role);
    if (rec.access_level > 0) {
        printf("PRIVILEGE ESCALATION: access_level was overwritten to %d!\n", rec.access_level);
    }
}

/* ==============================================================
 * ANTI-PATTERN 7: Integer overflow in size calculation (CWE-190)
 * ============================================================== */
void integer_overflow_alloc(int width, int height) {
    /* HAZARD (CWE-190): width * height may overflow int before cast to size_t,
     * resulting in a very small malloc that is then overwritten. */
    int size = width * height;  /* integer overflow if width*height > INT_MAX */
    char *buffer = (char *)malloc((size_t)size);
    if (!buffer) {
        perror("malloc failed");
        return;
    }
    /* HAZARD: memset writes beyond the actually-allocated (small) buffer */
    memset(buffer, 0, (size_t)width * (size_t)height);
    free(buffer);
}

/* ==============================================================
 * ANTI-PATTERN 8: strcat without bounds check
 * ============================================================== */
void strcat_overflow_demo(void) {
    char base[BUFFER_SIZE] = "PREFIX_";
    const char *suffix = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    /* HAZARD: strcat does not check that base has room for strlen(suffix) more chars */
    strcat(base, suffix);
    printf("Result: %s\n", base);
}

int main(void) {
    printf("=== strcpy Overflow ===\n");
    char long_input[200];
    memset(long_input, 'A', sizeof(long_input) - 1);
    long_input[sizeof(long_input) - 1] = '\0';
    strcpy_overflow_demo(long_input);

    printf("\n=== sprintf Overflow ===\n");
    sprintf_overflow_demo(long_input);

    printf("\n=== Off-By-One ===\n");
    off_by_one_demo();

    printf("\n=== Format String Attack ===\n");
    format_string_attack("Normal message: %s %s %s %d %d\n");

    printf("\n=== Struct Field Overflow ===\n");
    process_user_record(long_input, "admin");

    printf("\n=== Integer Overflow Alloc ===\n");
    integer_overflow_alloc(100000, 100000);  /* 10^10 overflows int */

    printf("\n=== strcat Overflow ===\n");
    strcat_overflow_demo();

    return 0;
}
