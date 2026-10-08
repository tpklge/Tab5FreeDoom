#include "freedoom_menu.h"
#include "doomkeys.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

#ifndef FREEDOOM_SD_DIR
#define FREEDOOM_SD_DIR "/sdcard/doom"
#endif

#define WIDTH 320
#define HEIGHT 200

static const char *TAG = "FREEDOOM";
static const char *const paths[2][2] = {
    {FREEDOOM_SD_DIR "/freedoom1.wad", FREEDOOM_SD_DIR "/FREEDOOM1.WAD"},
    {FREEDOOM_SD_DIR "/freedoom2.wad", FREEDOOM_SD_DIR "/FREEDOOM2.WAD"},
};

/* Original compact 5x7 font: A-Z, then 0-9. Rows use the low five bits. */
static const uint8_t glyphs[][7] = {
    {14,17,17,31,17,17,17}, {30,17,17,30,17,17,30},
    {14,17,16,16,16,17,14}, {30,17,17,17,17,17,30},
    {31,16,16,30,16,16,31}, {31,16,16,30,16,16,16},
    {14,17,16,23,17,17,15}, {17,17,17,31,17,17,17},
    {14,4,4,4,4,4,14}, {7,2,2,2,18,18,12},
    {17,18,20,24,20,18,17}, {16,16,16,16,16,16,31},
    {17,27,21,21,17,17,17}, {17,25,21,19,17,17,17},
    {14,17,17,17,17,17,14}, {30,17,17,30,16,16,16},
    {14,17,17,17,21,18,13}, {30,17,17,30,20,18,17},
    {15,16,16,14,1,1,30}, {31,4,4,4,4,4,4},
    {17,17,17,17,17,17,14}, {17,17,17,17,17,10,4},
    {17,17,17,21,21,21,10}, {17,17,10,4,10,17,17},
    {17,17,10,4,4,4,4}, {31,1,2,4,8,16,31},
    {14,17,19,21,25,17,14}, {4,12,4,4,4,4,14},
    {14,17,1,2,4,8,31}, {30,1,1,14,1,1,30},
    {2,6,10,18,31,2,2}, {31,16,16,30,1,1,30},
    {14,16,16,30,17,17,14}, {31,1,2,4,8,8,8},
    {14,17,17,14,17,17,14}, {14,17,17,15,1,1,14},
};

static void text(uint16_t *frame, int x, int y, const char *s,
                 int scale, uint16_t color)
{
    for (; *s; s++, x += 6 * scale) {
        const uint8_t *glyph = NULL;
        if (*s >= 'A' && *s <= 'Z') glyph = glyphs[*s - 'A'];
        if (*s >= '0' && *s <= '9') glyph = glyphs[26 + *s - '0'];
        for (int row = 0; row < 7; row++) {
            uint8_t bits = glyph ? glyph[row] : 0;
            if (*s == '.' && row == 6) bits = 4;
            if (*s == '/' && row < 5) bits = 1 << row;
            if (*s == '-' && row == 3) bits = 14;
            for (int col = 0; col < 5; col++) {
                if (!(bits & (1 << (4 - col)))) continue;
                for (int dy = 0; dy < scale; dy++)
                    for (int dx = 0; dx < scale; dx++) {
                        int px = x + col * scale + dx;
                        int py = y + row * scale + dy;
                        if (px >= 0 && px < WIDTH && py >= 0 && py < HEIGHT)
                            frame[py * WIDTH + px] = color;
                    }
            }
        }
    }
}

static void render(uint16_t *frame, int selected, const char *const available[2],
                   const char *message)
{
    memset(frame, 0, WIDTH * HEIGHT * sizeof(*frame));
    text(frame, 100, 10, "FREEDOOM", 2, 0xffe0);
    text(frame, 100, 32, "ESCOLHA A CAMPANHA", 1, 0xffff);
    const char *const titles[] = {"1  FREEDOOM 1", "2  FREEDOOM 2"};
    const char *const names[] = {"FREEDOOM1.WAD", "FREEDOOM2.WAD"};
    for (int i = 0; i < 2; i++) {
        int y = 57 + i * 45;
        if (selected == i)
            for (int row = y - 5; row < y + 32; row++)
                for (int col = 12; col < WIDTH - 12; col++)
                    frame[row * WIDTH + col] = 0x18c3;
        text(frame, 24, y, titles[i], 2, available[i] ? 0xffff : 0x8410);
        text(frame, 24, y + 19, names[i], 1, 0x07ff);
        text(frame, 190, y + 19, available[i] ? "PRONTO" : "AUSENTE OU INVALIDO",
             1, available[i] ? 0x07e0 : 0xf800);
    }
    text(frame, 12, 151, message, 1, 0xffe0);
    text(frame, 12, 172, "SETAS OU 1/2 - ENTER PARA JOGAR", 1, 0xffff);
    text(frame, 12, 185, "R - BUSCAR WADS NA PASTA /DOOM", 1, 0x07ff);
}

static void refresh(const char *available[2], bool *mounted, int (*mount_card)(void))
{
    if (!*mounted) *mounted = mount_card() == 0;
    for (int i = 0; i < 2; i++) {
        available[i] = NULL;
        if (!*mounted) continue;
        for (int j = 0; j < 2; j++) {
            FILE *f = fopen(paths[i][j], "rb");
            if (!f) {
                ESP_LOGE(TAG, "Cannot open %s: %s", paths[i][j], strerror(errno));
                continue;
            }
            unsigned char header[12];
            bool valid = fread(header, 1, sizeof(header), f) == sizeof(header)
                         && memcmp(header, "IWAD", 4) == 0;
            fclose(f);
            if (valid) {
                available[i] = paths[i][j];
                break;
            }
            ESP_LOGE(TAG, "Invalid IWAD header: %s", paths[i][j]);
        }
        ESP_LOGI(TAG, "%s: %s", i == 0 ? "Freedoom 1" : "Freedoom 2",
                 available[i] ? available[i] : "missing or invalid IWAD");
    }
}

const char *freedoom_select_wad(void (*draw)(const uint32_t *),
                                 int (*get_key)(int *, unsigned char *),
                                 int (*mount_card)(void))
{
    uint16_t *frame = heap_caps_malloc(WIDTH * HEIGHT * sizeof(*frame),
                                       MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!frame) {
        ESP_LOGE(TAG, "Not enough PSRAM for the selection menu");
        return NULL;
    }
    bool mounted = false;
    const char *available[2] = {NULL, NULL};
    refresh(available, &mounted, mount_card);
    int selected = !available[0] && available[1] ? 1 : 0;
    const char *message = mounted ? "WADS EM /DOOM NO MICROSD" : "MICROSD INDISPONIVEL - PRESSIONE R";
    bool dirty = true;
    while (true) {
        if (dirty) {
            render(frame, selected, available, message);
            draw((const uint32_t *)frame);
            dirty = false;
        }
        int pressed;
        unsigned char key;
        if (!get_key(&pressed, &key) || !pressed) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }
        if (key == KEY_UPARROW || key == KEY_DOWNARROW || key == 'w' || key == 's') {
            selected ^= 1;
            dirty = true;
        } else if (key == '1' || key == '2') {
            selected = key - '1';
            dirty = true;
        } else if (key == 'r' || key == 'R') {
            refresh(available, &mounted, mount_card);
            message = mounted ? "BUSCA CONCLUIDA" : "MICROSD INDISPONIVEL - PRESSIONE R";
            dirty = true;
        } else if (key == KEY_ENTER) {
            if (!available[selected]) {
                message = "WAD AUSENTE OU INVALIDO - USE R";
                dirty = true;
                continue;
            }
            const char *path = available[selected];
            heap_caps_free(frame);
            ESP_LOGI(TAG, "Selected IWAD: %s", path);
            return path;
        }
    }
}
