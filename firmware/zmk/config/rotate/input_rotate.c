/*
 * Copyright (c) 2026 Diwamoto_
 * SPDX-License-Identifier: MIT
 *
 * Buffers one REL_X/REL_Y frame from the source device until sync, rotates
 * and scales it, and re-reports it from this device. Sub-count remainders
 * carry over so slow rolls don't lose the rotated component.
 *
 * After the ball has been still for idle-ms, motion is swallowed until it
 * adds up to wake-threshold counts, so keystroke vibration doesn't move the
 * cursor (or wake the auto mouse layer).
 *
 * The tunables can be changed at runtime over a USB serial port
 * (case/site/tune.html uses it via Web Serial) and are kept in settings.
 * Only one instance is supported.
 */

#define DT_DRV_COMPAT sage60_input_rotate

#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/input/input.h>
#include <zephyr/settings/settings.h>

/* Storage format: little-endian int16 fields. */
struct rotate_params {
    int16_t angle;          /* degrees, sideways rolls */
    int16_t angle_y;        /* degrees, up/down rolls */
    int16_t wake_threshold; /* counts */
    int16_t scale_pct;      /* 100 = 1x */
} __packed;

struct rotate_config {
    struct rotate_params defaults;
    int idle_ms;
};

struct rotate_data {
    struct rotate_params p;
    float xx, xy, yx, yy; /* output = M * input, scale folded in */
    int32_t x, y;
    float rem_x, rem_y;
    int64_t last_ms;
    int32_t wake_acc;
    bool awake;
};

static struct rotate_data *inst;

/* ponytail: params change from the work queue without a lock; worst case one
 * frame uses half-updated coefficients. Add a spinlock if that ever shows. */
static void apply(struct rotate_data *d) {
    float s = d->p.scale_pct / 100.0f;
    float a = d->p.angle * 3.14159265f / 180.0f;
    float b = d->p.angle_y * 3.14159265f / 180.0f;

    d->xx = cosf(a) * s;
    d->yx = sinf(a) * s;
    d->xy = -sinf(b) * s;
    d->yy = cosf(b) * s;
}

static bool valid(const struct rotate_params *p) {
    return p->angle >= -180 && p->angle <= 180 && p->angle_y >= -180 && p->angle_y <= 180 &&
           p->wake_threshold >= 0 && p->wake_threshold <= 200 && p->scale_pct >= 10 &&
           p->scale_pct <= 1000;
}

static void rotate_cb(struct input_event *evt, void *user_data) {
    const struct device *dev = user_data;
    const struct rotate_config *cfg = dev->config;
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

    int64_t now = k_uptime_get();
    if (now - d->last_ms > cfg->idle_ms) {
        d->awake = false;
        d->wake_acc = 0;
        d->rem_x = d->rem_y = 0;
    }
    d->last_ms = now;
    if (!d->awake) {
        d->wake_acc += abs(d->x) + abs(d->y);
        d->x = d->y = 0;
        d->awake = d->wake_acc >= d->p.wake_threshold;
        return;
    }

    float fx = d->x * d->xx + d->y * d->xy + d->rem_x;
    float fy = d->x * d->yx + d->y * d->yy + d->rem_y;
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

/* ---- persistence ---- */

#if IS_ENABLED(CONFIG_SETTINGS)
static int rot_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    struct rotate_params p;

    if (!inst || len != sizeof(p) || read_cb(cb_arg, &p, sizeof(p)) != sizeof(p) || !valid(&p)) {
        return 0; /* keep devicetree defaults */
    }
    inst->p = p;
    apply(inst);
    return 0;
}

SETTINGS_STATIC_HANDLER_DEFINE(sage60_rot, "sage60/rot", NULL, rot_settings_set, NULL, NULL);
#endif

/* ---- USB serial, shared with ZMK Studio ----
 * One CDC ACM port carries both ZMK Studio and the tuning lines. The
 * sage60,uart-tap device sits in front of the real port (zmk,studio-rpc-uart
 * points at the tap): bytes inside Studio frames (SOF 0xAB .. EOF 0xAD, ESC
 * 0xAC) pass through to Studio, plain text lines outside frames are ours:
 *   "get"          -> "rot <angle> <angle_y> <wake_threshold> <scale_pct>"
 *   "set a b c d"  -> same reply after applying and saving, or "err"
 * A stray 0xAD outside a frame is dropped, so a client can send one first to
 * resync if Studio left a frame half-sent. case/site/tune.html uses this. */

#if DT_HAS_COMPAT_STATUS_OKAY(sage60_uart_tap)
#include <stdio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/ring_buffer.h>

#define TAP_NODE DT_COMPAT_GET_ANY_STATUS_OKAY(sage60_uart_tap)
#define SOF 0xAB
#define ESC 0xAC
#define EOF_ 0xAD

static const struct device *const real = DEVICE_DT_GET(DT_PHANDLE(TAP_NODE, uart));
RING_BUF_DECLARE(studio_rx, 256);
static uart_irq_callback_user_data_t studio_cb;
static void *studio_ud;
static bool studio_rx_en, in_frame, escaped;
static char line[48], cmd[48];
static size_t line_len;

static void tune_puts(const char *s) {
    while (*s) {
        uart_poll_out(real, *s++);
    }
}

static void tune_work_fn(struct k_work *work) {
    struct rotate_params p;
    int a, b, c, d;
    char out[48];

    if (!inst) {
        return;
    }
    if (sscanf(cmd, "set %d %d %d %d", &a, &b, &c, &d) == 4) {
        p = (struct rotate_params){a, b, c, d};
        if (a != p.angle || b != p.angle_y || c != p.wake_threshold || d != p.scale_pct ||
            !valid(&p)) {
            tune_puts("err\n");
            return;
        }
        inst->p = p;
        apply(inst);
#if IS_ENABLED(CONFIG_SETTINGS)
        settings_save_one("sage60/rot", &p, sizeof(p));
#endif
    } else if (strcmp(cmd, "get") != 0) {
        tune_puts("err\n");
        return;
    }
    snprintf(out, sizeof(out), "rot %d %d %d %d\n", inst->p.angle, inst->p.angle_y,
             inst->p.wake_threshold, inst->p.scale_pct);
    tune_puts(out);
}

static K_WORK_DEFINE(tune_work, tune_work_fn);

static void tune_byte(uint8_t c) {
    if (c == '\r' || c == EOF_) {
        return;
    }
    if (c != '\n') {
        if (line_len < sizeof(line) - 1) {
            line[line_len++] = c;
        }
        return;
    }
    /* ponytail: one pending command; a line arriving mid-work is dropped. */
    if (!k_work_is_pending(&tune_work)) {
        line[line_len] = 0;
        memcpy(cmd, line, line_len + 1);
        k_work_submit(&tune_work);
    }
    line_len = 0;
}

/* Split incoming bytes between Studio's frames and our text lines. */
static void route(uint8_t c) {
    if (!in_frame && c != SOF) {
        tune_byte(c);
        return;
    }
    if (escaped) {
        escaped = false;
    } else if (c == ESC) {
        escaped = true;
    } else if (c == SOF) {
        in_frame = true;
    } else if (c == EOF_) {
        in_frame = false;
    }
    /* ponytail: overflow drops Studio bytes; Studio resyncs on the next SOF. */
    ring_buf_put(&studio_rx, &c, 1);
}

static void real_isr(const struct device *dev, void *user_data) {
    const struct device *tap = user_data;
    uint8_t buf[32];
    int n;

    while (uart_irq_update(real) && uart_irq_rx_ready(real) &&
           (n = uart_fifo_read(real, buf, sizeof(buf))) > 0) {
        for (int i = 0; i < n; i++) {
            route(buf[i]);
        }
    }
    if (studio_cb) {
        studio_cb(tap, studio_ud);
    }
}

/* The tap's UART API: what Studio's transport sees. */
static int tap_update(const struct device *dev) { return 1; }
static int tap_rx_ready(const struct device *dev) {
    return studio_rx_en && !ring_buf_is_empty(&studio_rx);
}
static int tap_fifo_read(const struct device *dev, uint8_t *data, int size) {
    return ring_buf_get(&studio_rx, data, size);
}
static int tap_tx_ready(const struct device *dev) { return uart_irq_tx_ready(real); }
static int tap_fifo_fill(const struct device *dev, const uint8_t *data, int size) {
    return uart_fifo_fill(real, data, size);
}
static void tap_tx_enable(const struct device *dev) { uart_irq_tx_enable(real); }
static void tap_tx_disable(const struct device *dev) { uart_irq_tx_disable(real); }
static void tap_rx_enable(const struct device *dev) { studio_rx_en = true; }
static void tap_rx_disable(const struct device *dev) { studio_rx_en = false; }
static void tap_poll_out(const struct device *dev, unsigned char c) { uart_poll_out(real, c); }
static int tap_poll_in(const struct device *dev, unsigned char *c) { return -1; }
static void tap_callback_set(const struct device *dev, uart_irq_callback_user_data_t cb,
                             void *ud) {
    studio_cb = cb;
    studio_ud = ud;
}

static DEVICE_API(uart, tap_api) = {
    .poll_in = tap_poll_in,
    .poll_out = tap_poll_out,
    .fifo_fill = tap_fifo_fill,
    .fifo_read = tap_fifo_read,
    .irq_tx_enable = tap_tx_enable,
    .irq_tx_disable = tap_tx_disable,
    .irq_tx_ready = tap_tx_ready,
    .irq_rx_enable = tap_rx_enable,
    .irq_rx_disable = tap_rx_disable,
    .irq_rx_ready = tap_rx_ready,
    .irq_update = tap_update,
    .irq_callback_set = tap_callback_set,
};

static int tap_init(const struct device *dev) {
    if (!device_is_ready(real)) {
        return -ENODEV;
    }
    uart_irq_callback_user_data_set(real, real_isr, (void *)dev);
    uart_irq_rx_enable(real);
    return 0;
}

/* After the CDC ACM port (PRE_KERNEL_1), before Studio's transport (POST_KERNEL). */
DEVICE_DT_DEFINE(TAP_NODE, tap_init, NULL, NULL, NULL, PRE_KERNEL_2, CONFIG_SERIAL_INIT_PRIORITY,
                 &tap_api);
#endif

static int rotate_init(const struct device *dev) {
    const struct rotate_config *cfg = dev->config;
    struct rotate_data *d = dev->data;

    d->p = cfg->defaults;
    apply(d);
    inst = d;
    return 0;
}

#define ROTATE_INST(n)                                                                             \
    static struct rotate_data rotate_data_##n;                                                     \
    static const struct rotate_config rotate_config_##n = {                                        \
        .defaults =                                                                                \
            {                                                                                      \
                .angle = DT_INST_PROP(n, angle),                                                   \
                .angle_y = DT_INST_PROP_OR(n, angle_y, DT_INST_PROP(n, angle)),                    \
                .wake_threshold = DT_INST_PROP(n, wake_threshold),                                 \
                .scale_pct = DT_INST_PROP(n, scale_pct),                                           \
            },                                                                                     \
        .idle_ms = DT_INST_PROP(n, idle_ms),                                                       \
    };                                                                                             \
    DEVICE_DT_INST_DEFINE(n, rotate_init, NULL, &rotate_data_##n, &rotate_config_##n, POST_KERNEL, \
                          CONFIG_INPUT_INIT_PRIORITY, NULL);                                       \
    INPUT_CALLBACK_DEFINE(DEVICE_DT_GET(DT_INST_PHANDLE(n, device)), rotate_cb,                    \
                          (void *)DEVICE_DT_INST_GET(n));

DT_INST_FOREACH_STATUS_OKAY(ROTATE_INST)
