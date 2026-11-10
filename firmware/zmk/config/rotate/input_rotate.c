/*
 * Copyright (c) 2026 Diwamoto_
 * SPDX-License-Identifier: MIT
 *
 * Buffers one REL_X/REL_Y frame from the source device until sync, rotates
 * it and re-reports it from this device. Sub-count remainders carry over so
 * slow rolls don't lose the rotated component.
 */

#define DT_DRV_COMPAT sage60_input_rotate

#include <math.h>
#include <zephyr/device.h>
#include <zephyr/input/input.h>

struct rotate_config {
    int angle;
};

struct rotate_data {
    float cos, sin;
    int32_t x, y;
    float rem_x, rem_y;
};

static void rotate_cb(struct input_event *evt, void *user_data) {
    const struct device *dev = user_data;
    struct rotate_data *d = dev->data;

    if (evt->type != INPUT_EV_REL) {
        return;
    }
    if (evt->code == INPUT_REL_X) {
        d->x += evt->value;
    } else if (evt->code == INPUT_REL_Y) {
        d->y += evt->value;
    }
    if (!evt->sync) {
        return;
    }

    float fx = d->x * d->cos - d->y * d->sin + d->rem_x;
    float fy = d->x * d->sin + d->y * d->cos + d->rem_y;
    int16_t ox = (int16_t)fx, oy = (int16_t)fy;
    d->rem_x = fx - ox;
    d->rem_y = fy - oy;
    d->x = d->y = 0;

    if (ox) {
        input_report_rel(dev, INPUT_REL_X, ox, !oy, K_NO_WAIT);
    }
    if (oy) {
        input_report_rel(dev, INPUT_REL_Y, oy, true, K_NO_WAIT);
    }
}

static int rotate_init(const struct device *dev) {
    const struct rotate_config *cfg = dev->config;
    struct rotate_data *d = dev->data;
    float rad = cfg->angle * 3.14159265f / 180.0f;

    d->cos = cosf(rad);
    d->sin = sinf(rad);
    return 0;
}

#define ROTATE_INST(n)                                                                             \
    static struct rotate_data rotate_data_##n;                                                     \
    static const struct rotate_config rotate_config_##n = {.angle = DT_INST_PROP(n, angle)};       \
    DEVICE_DT_INST_DEFINE(n, rotate_init, NULL, &rotate_data_##n, &rotate_config_##n, POST_KERNEL, \
                          CONFIG_INPUT_INIT_PRIORITY, NULL);                                       \
    INPUT_CALLBACK_DEFINE(DEVICE_DT_GET(DT_INST_PHANDLE(n, device)), rotate_cb,                    \
                          (void *)DEVICE_DT_INST_GET(n));

DT_INST_FOREACH_STATUS_OKAY(ROTATE_INST)
