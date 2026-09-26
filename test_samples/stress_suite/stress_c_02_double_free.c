/*
 * stress_c_02_double_free.c
 * ByteSized Stress Suite — C: double-free, use-after-free, malloc/free mismatches
 *
 * Compile: gcc -O0 -fsanitize=address -g stress_c_02_double_free.c -o double_free
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ==============================================================
 * ANTI-PATTERN 1: Double free (CWE-415)
 * ============================================================== */
void double_free_demo(void) {
    char *ptr = (char *)malloc(128);
    if (!ptr) return;
    strcpy(ptr, "sensitive data");
    printf("Before free: ptr = %p, *ptr = %s\n", (void*)ptr, ptr);
    free(ptr);
    /* HAZARD (CWE-415): freeing an already-freed pointer corrupts the heap allocator
     * metadata, potentially enabling arbitrary code execution. */
    free(ptr);
    printf("After double free — heap state is corrupt\n");
}

/* ==============================================================
 * ANTI-PATTERN 2: Use-after-free (CWE-416) via aliased pointer
 * ============================================================== */
typedef struct {
    int  id;
    char name[64];
} Entity;

Entity *global_cache = NULL;

void load_entity(int id) {
    global_cache = (Entity *)malloc(sizeof(Entity));
    global_cache->id = id;
    snprintf(global_cache->name, 64, "Entity_%d", id);
}

void evict_entity(void) {
    free(global_cache);
    /* HAZARD: global_cache is not set to NULL after free */
}

void use_entity(void) {
    /* HAZARD (CWE-416): global_cache may point to freed memory */
    printf("Entity id=%d name=%s\n", global_cache->id, global_cache->name);
}

/* ==============================================================
 * ANTI-PATTERN 3: free() on stack-allocated memory (CWE-590)
 * ============================================================== */
void free_stack_memory(void) {
    int stack_array[10] = {0};
    int *ptr = stack_array;
    /* HAZARD (CWE-590): freeing a pointer to stack memory — catastrophic UB */
    free(ptr);
}

/* ==============================================================
 * ANTI-PATTERN 4: Mismatched new/delete vs malloc/free
 * (Shown in C via simulated mismatch with realloc)
 * ============================================================== */
void realloc_mismatch_demo(void) {
    int *arr = (int *)malloc(10 * sizeof(int));
    if (!arr) return;
    for (int i = 0; i < 10; i++) arr[i] = i;

    /* HAZARD: realloc can move the block; the old pointer arr is now invalid */
    int *new_arr = (int *)realloc(arr, 200 * sizeof(int));
    if (!new_arr) {
        free(arr);  /* correct cleanup if realloc fails */
        return;
    }
    /* arr is now a dangling pointer if realloc moved the block */
    printf("arr[0] via OLD dangling pointer: %d (UB if moved)\n", arr[0]);  /* UB */
    free(new_arr);
    /* HAZARD: free(arr) here would be double-free if realloc succeeded */
}

/* ==============================================================
 * ANTI-PATTERN 5: Partial free in loop (leaks remaining elements)
 * ============================================================== */
typedef struct Node {
    int data;
    struct Node *next;
} Node;

Node *build_list(int n) {
    Node *head = NULL;
    for (int i = 0; i < n; i++) {
        Node *node = (Node *)malloc(sizeof(Node));
        node->data = i;
        node->next = head;
        head = node;
    }
    return head;
}

void free_list_partial(Node *head) {
    /* ANTI-PATTERN: saves next AFTER free — UB because we dereference freed memory */
    while (head != NULL) {
        free(head);
        head = head->next;  /* HAZARD (CWE-416): head->next accessed after free(head) */
    }
}

/* ==============================================================
 * ANTI-PATTERN 6: Incorrect NULL check after malloc
 * ============================================================== */
void missing_null_check_demo(void) {
    /* HAZARD: malloc return value is not checked before use */
    char *buf = (char *)malloc(1024 * 1024 * 512);  /* 512 MB — may return NULL */
    strcpy(buf, "data");  /* if buf is NULL, this is a null pointer dereference */
    free(buf);
}

/* ==============================================================
 * ANTI-PATTERN 7: Freeing a pointer obtained by pointer arithmetic
 * ============================================================== */
void free_pointer_arithmetic(void) {
    int *arr = (int *)malloc(10 * sizeof(int));
    if (!arr) return;
    arr++;          /* advance pointer by one element */
    free(arr);      /* HAZARD: freeing offset pointer — not the original malloc address */
}

int main(void) {
    printf("=== Double Free ===\n");
    double_free_demo();

    printf("\n=== Use-After-Free via Global Cache ===\n");
    load_entity(42);
    evict_entity();
    use_entity();   /* UAF */

    printf("\n=== realloc Mismatch ===\n");
    realloc_mismatch_demo();

    printf("\n=== Partial List Free ===\n");
    Node *list = build_list(5);
    free_list_partial(list);

    return 0;
}
