#!/usr/bin/env python3
"""Exercise the actual menu with a temporary SD directory and platform stubs."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='freedoom-menu-') as tmp:
    temp = Path(tmp)
    sd = temp / 'doom'
    sd.mkdir()
    stubs = temp / 'include'
    (stubs / 'freertos').mkdir(parents=True)
    (stubs / 'esp_log.h').write_text('''
#define ESP_LOGI(tag, ...) ((void)(tag))
#define ESP_LOGE(tag, ...) ((void)(tag))
''')
    (stubs / 'esp_heap_caps.h').write_text('''
#include <stdlib.h>
#define MALLOC_CAP_SPIRAM 1
#define MALLOC_CAP_8BIT 2
extern int allocations, fail_alloc;
static inline void *heap_caps_malloc(size_t n, int caps) {
    (void)caps;
    if (fail_alloc) return NULL;
    void *p = malloc(n);
    if (p) allocations++;
    return p;
}
static inline void heap_caps_free(void *p) {
    if (p) allocations--;
    free(p);
}
''')
    (stubs / 'freertos/FreeRTOS.h').write_text('#define pdMS_TO_TICKS(n) (n)\n')
    (stubs / 'freertos/task.h').write_text('static inline void vTaskDelay(int n) { (void)n; }\n')
    harness = temp / 'test.c'
    harness.write_text(r'''
#include "freedoom_menu.h"
#include "doomkeys.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

int allocations, fail_alloc;
static const int *events;
static unsigned event_count, event_pos, draws, mount_calls;
static int mount_failures;
static const char *files[] = {"freedoom1.wad", "FREEDOOM1.WAD", "freedoom2.wad", "FREEDOOM2.WAD"};
static char selected[512];

static void file(const char *name, const char *magic) {
    char path[512];
    snprintf(path, sizeof(path), "%s/%s", FREEDOOM_SD_DIR, name);
    FILE *f = fopen(path, "wb"); assert(f);
    unsigned char header[12] = {0};
    memcpy(header, magic, 4);
    assert(fwrite(header, 1, sizeof(header), f) == sizeof(header));
    fclose(f);
}
static void clear(void) {
    for (unsigned i = 0; i < 4; i++) {
        char path[512];
        snprintf(path, sizeof(path), "%s/%s", FREEDOOM_SD_DIR, files[i]);
        unlink(path);
    }
    draws = mount_calls = event_pos = 0;
    mount_failures = fail_alloc = 0;
}
static int mount(void) {
    mount_calls++;
    return (int)mount_calls <= mount_failures ? 1 : 0;
}
static void draw(const uint32_t *buffer) {
    const uint16_t *pixels = (const uint16_t *)buffer;
    assert(pixels[0] == 0);
    assert(pixels[52 * 320 + 12] == 0x18c3 || pixels[97 * 320 + 12] == 0x18c3);
    draws++;
}
static int key(int *pressed, unsigned char *value) {
    assert(event_pos < event_count && "menu did not finish after scripted input");
    int event = events[event_pos++];
    if (event == -1) { file("freedoom2.wad", "IWAD"); event = 'r'; }
    *pressed = !(event & 0x100);
    *value = event & 0xff;
    return 1;
}
static void run(const int *input, unsigned n, const char *expected) {
    events = input; event_count = n;
    const char *result = freedoom_select_wad(draw, key, mount);
    snprintf(selected, sizeof(selected), "%s/%s", FREEDOOM_SD_DIR, expected);
    /* FAT and macOS volumes can resolve uppercase names via the lowercase path. */
    assert(result && strcasecmp(result, selected) == 0);
    assert(allocations == 0 && draws > 0);
}
#define RUN(input, expected) run(input, sizeof(input)/sizeof(input[0]), expected)
int main(void) {
    clear(); file("freedoom1.wad", "IWAD"); file("freedoom2.wad", "IWAD");
    const int down[] = {KEY_DOWNARROW | 0x100, KEY_DOWNARROW, KEY_ENTER};
    RUN(down, "freedoom2.wad"); assert(draws == 2);
    clear(); file("FREEDOOM1.WAD", "IWAD");
    const int enter[] = {KEY_ENTER}; RUN(enter, "FREEDOOM1.WAD");
    clear(); file("FREEDOOM2.WAD", "IWAD"); RUN(enter, "FREEDOOM2.WAD");
    clear(); file("freedoom2.wad", "IWAD");
    const int absent[] = {'1', KEY_ENTER, '2', KEY_ENTER};
    RUN(absent, "freedoom2.wad"); assert(event_pos == 4);
    clear(); file("freedoom1.wad", "PWAD"); file("freedoom2.wad", "IWAD");
    RUN(enter, "freedoom2.wad");
    clear(); file("freedoom1.wad", "IWAD"); mount_failures = 1;
    const int retry[] = {KEY_ENTER, 'r', KEY_ENTER};
    RUN(retry, "freedoom1.wad"); assert(mount_calls == 2);
    clear();
    const int added[] = {KEY_ENTER, -1, '2', KEY_ENTER};
    RUN(added, "freedoom2.wad"); assert(event_pos == 4);
    clear(); fail_alloc = 1;
    assert(freedoom_select_wad(draw, key, mount) == NULL);
    assert(allocations == 0 && draws == 0);
    puts("8 menu scenarios passed: selection, release, uppercase, missing/invalid WAD, mount retry, file refresh, allocation failure.");
}
''')
    binary = temp / 'test-menu'
    subprocess.run([
        os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
        f'-DFREEDOOM_SD_DIR="{sd}"',
        '-I', str(stubs), '-I', str(ROOT / 'main'),
        '-I', str(ROOT / 'components/doomgeneric/doomgeneric'),
        str(ROOT / 'main/freedoom_menu.c'), str(harness), '-o', str(binary),
    ], check=True)
    subprocess.run([str(binary)], check=True, timeout=10)
