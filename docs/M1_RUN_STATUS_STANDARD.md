# M1 Run Status Standard

## Canonical TAP run statuses

TAP uses the following run statuses during M1:

- `created`
- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`
- `unknown`

## Active statuses

These statuses represent runs that may still change:

- `created`
- `queued`
- `running`
- `unknown`

## Terminal statuses

These statuses represent runs that should not continue polling aggressively:

- `completed`
- `failed`
- `cancelled`

## Expected M1 lifecycle

Successful run:

`created → queued → running → completed`

Failed run:

`created → queued → running → failed`

Cancelled run:

`created → queued/running → cancelled`

## Slurm to TAP status mapping

- `PENDING`, `PD`, `CONFIGURING`, `CF` → `queued`
- `RUNNING`, `R`, `COMPLETING`, `CG` → `running`
- `COMPLETED`, `CD` with successful exit code → `completed`
- `FAILED`, `TIMEOUT`, `OUT_OF_MEMORY`, `NODE_FAIL`, `BOOT_FAIL`, `DEADLINE`, `PREEMPTED` → `failed`
- `CANCELLED`, `CA` → `cancelled`
- unrecognised state → `unknown` or keep current status if safer

## W&B to TAP status mapping

- `running` → `running`
- `finished`, `completed` → `completed`
- `failed`, `crashed` → `failed`
- `killed`, `cancelled`, `canceled` → `cancelled`
- missing/unknown state → `unknown`

## Rule

Backend, database, API responses, and frontend must use these exact lowercase strings.