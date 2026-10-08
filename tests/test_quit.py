#!/usr/bin/env python3
"""Compile the real shutdown functions with a simulated board restart."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'components/doomgeneric/doomgeneric'


def function(filename, signature):
    source = (ENGINE / filename).read_text()
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


source = r'''
#include <assert.h>
#include <setjmp.h>
#include <stdlib.h>
#define ESP_PLATFORM 1
#define ESP_LOGI(...) ((void)0)
typedef int boolean;
typedef void (*atexit_func_t)(void);
typedef struct atexit_listentry_s {
    atexit_func_t func;
    boolean run_on_error;
    struct atexit_listentry_s *next;
} atexit_listentry_t;
static atexit_listentry_t *exit_funcs;
static jmp_buf restarted;
static int sequence;
static void p4_doom_prepare_restart(void) { assert(sequence++ == 2); }
static void save_config(void) { assert(sequence++ == 0); }
static void stop_audio(void) { assert(sequence++ == 1); }
static void esp_restart(void) {
    assert(sequence == 3);
    longjmp(restarted, 1);
}
'''
source += function('d_main.c', 'static void D_Endoom(void)') + '\n'
source += function('i_system.c', 'void I_AtExit(') + '\n'
source += function('i_system.c', 'void I_Quit (void)') + '\n'
source += r'''
int main(void) {
    I_AtExit(D_Endoom, 0);
    I_AtExit(stop_audio, 0);
    I_AtExit(save_config, 0);
    if (setjmp(restarted) == 0) {
        I_Quit();
        assert(!"I_Quit returned to the game loop");
    }
    assert(sequence == 3);
    while (exit_funcs) {
        atexit_listentry_t *entry = exit_funcs;
        exit_funcs = entry->next;
        free(entry);
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='freedoom-quit-') as tmp:
    test = Path(tmp) / 'quit.c'
    binary = Path(tmp) / 'quit'
    test.write_text(source)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall',
                    '-Wextra', '-Werror', str(test), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('PASS: shutdown callbacks complete before restart; no exit or fallthrough')
