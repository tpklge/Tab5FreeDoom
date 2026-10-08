#pragma once

#include <stdint.h>

/* Returns a static IWAD path after keyboard confirmation. */
const char *freedoom_select_wad(void (*draw)(const uint32_t *),
                                 int (*get_key)(int *, unsigned char *),
                                 int (*mount_card)(void));
