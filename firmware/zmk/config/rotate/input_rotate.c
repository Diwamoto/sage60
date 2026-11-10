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
 * The tunables can be changed at runtime over a BLE GATT characteristic
 * (case/site/tune.html uses it via Web Bluetooth) and are kept in settings.
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
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>

/* Wire/storage format: little-endian int16 fields. */
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

/* ponytail: params change from the BT thread without a lock; worst case one
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

/* ---- BLE GATT: one 8-byte read/write characteristic, bonded links only ---- */

#if IS_ENABLED(CONFIG_BT)
#define ROT_SVC_UUID BT_UUID_128_ENCODE(0x5a6e6060, 0x7f1c, 0x4b8e, 0x9d2a, 0x3c51e0a10000)
#define ROT_CHR_UUID BT_UUID_128_ENCODE(0x5a6e6060, 0x7f1c, 0x4b8e, 0x9d2a, 0x3c51e0a10001)

static ssize_t rot_read(struct bt_conn *conn, const struct bt_gatt_attr *attr, void *buf,
                        uint16_t len, uint16_t offset) {
    struct rotate_params p = inst ? inst->p : (struct rotate_params){0};

    return bt_gatt_attr_read(conn, attr, buf, len, offset, &p, sizeof(p));
}

static ssize_t rot_write(struct bt_conn *conn, const struct bt_gatt_attr *attr, const void *buf,
                         uint16_t len, uint16_t offset, uint8_t flags) {
    struct rotate_params p;

    if (offset || len != sizeof(p)) {
        return BT_GATT_ERR(BT_ATT_ERR_INVALID_ATTRIBUTE_LEN);
    }
    memcpy(&p, buf, sizeof(p));
    if (!inst || !valid(&p)) {
        return BT_GATT_ERR(BT_ATT_ERR_VALUE_NOT_ALLOWED);
    }
    inst->p = p;
    apply(inst);
#if IS_ENABLED(CONFIG_SETTINGS)
    settings_save_one("sage60/rot", &p, sizeof(p));
#endif
    return len;
}

BT_GATT_SERVICE_DEFINE(rot_svc, BT_GATT_PRIMARY_SERVICE(BT_UUID_DECLARE_128(ROT_SVC_UUID)),
                       BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_128(ROT_CHR_UUID),
                                              BT_GATT_CHRC_READ | BT_GATT_CHRC_WRITE,
                                              BT_GATT_PERM_READ_ENCRYPT |
                                                  BT_GATT_PERM_WRITE_ENCRYPT,
                                              rot_read, rot_write, NULL), );
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
