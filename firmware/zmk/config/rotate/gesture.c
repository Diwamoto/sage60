/*
 * Copyright (c) 2026 Diwamoto_
 * SPDX-License-Identifier: MIT
 *
 * Input processor for a held gesture layer: swallows the ball's motion and
 * turns one roll up or down past threshold into one tap of the first or
 * second binding. It fires again only after the ball has rested rearm-ms.
 */

#define DT_DRV_COMPAT sage60_input_gesture

#include <stdlib.h>
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <drivers/input_processor.h>
#include <zmk/behavior.h>
#include <zmk/keymap.h>
#include <zmk/virtual_key_position.h>

struct gesture_config {
    uint8_t index;
    int threshold;
    int rearm_ms;
    struct zmk_behavior_binding bindings[2]; /* up, down */
};

struct gesture_data {
    int32_t acc;
    int64_t last_ms;
    bool fired;
};

static int gesture_handle(const struct device *dev, struct input_event *evt, uint32_t p1,
                          uint32_t p2, struct zmk_input_processor_state *state) {
    const struct gesture_config *cfg = dev->config;
    struct gesture_data *d = dev->data;

    if (evt->type != INPUT_EV_REL) {
        return ZMK_INPUT_PROC_CONTINUE;
    }
    int64_t now = k_uptime_get();
    if (now - d->last_ms > cfg->rearm_ms) {
        d->acc = 0;
        d->fired = false;
    }
    d->last_ms = now;

    if (evt->code == INPUT_REL_Y && !d->fired) {
        d->acc += evt->value;
        if (abs(d->acc) >= cfg->threshold) {
            /* Negative Y is up on screen. */
            const struct zmk_behavior_binding *b = &cfg->bindings[d->acc < 0 ? 0 : 1];
            struct zmk_behavior_binding_event be = {
                .position = ZMK_VIRTUAL_KEY_POSITION_BEHAVIOR_INPUT_PROCESSOR(
                    state->input_device_index, cfg->index),
                .timestamp = now,
#if IS_ENABLED(CONFIG_ZMK_SPLIT)
                .source = ZMK_POSITION_STATE_CHANGE_SOURCE_LOCAL,
#endif
            };
            zmk_behavior_invoke_binding(b, be, true);
            zmk_behavior_invoke_binding(b, be, false);
            d->fired = true;
        }
    }
    /* A layer override's STOP doesn't reach the listener in this ZMK, so
     * swallow by zeroing instead. */
    evt->value = 0;
    return ZMK_INPUT_PROC_STOP;
}

static struct zmk_input_processor_driver_api gesture_api = {.handle_event = gesture_handle};

#define GESTURE_INST(n)                                                                            \
    BUILD_ASSERT(DT_INST_PROP_LEN(n, bindings) == 2, "bindings: <up>, <down>");                    \
    static struct gesture_data gesture_data_##n;                                                   \
    static const struct gesture_config gesture_config_##n = {                                      \
        .index = n,                                                                                \
        .threshold = DT_INST_PROP(n, threshold),                                                   \
        .rearm_ms = DT_INST_PROP(n, rearm_ms),                                                     \
        .bindings = {LISTIFY(2, ZMK_KEYMAP_EXTRACT_BINDING, (, ), DT_DRV_INST(n))},                \
    };                                                                                             \
    DEVICE_DT_INST_DEFINE(n, NULL, NULL, &gesture_data_##n, &gesture_config_##n, POST_KERNEL,      \
                          CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &gesture_api);

DT_INST_FOREACH_STATUS_OKAY(GESTURE_INST)
