/**
 * SiliconBob Test Sample: C / C++
 * Demonstrates buffer overflow vulnerabilities (CWE-120, CWE-242, CWE-134).
 */

#include <stdio.h>
#include <string.h>

void process_buffer(char *destination, const char *source) {
    char user_input[64];

    // Critical Hazard: gets() lacks boundary bounds (CWE-242)
    gets(user_input);

    // Hazard: strcpy without size check causes buffer overflow (CWE-120)
    strcpy(destination, source);

    // Hazard: sprintf without bounds limit (CWE-134)
    sprintf(destination, "Prefix: %s", source);
}
