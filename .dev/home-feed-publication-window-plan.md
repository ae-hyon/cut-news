# Home feed publication window requirement and implementation plan

## Requirement

Cut News home feed visibility is controlled by the server using Korea time (`Asia/Seoul`). The frontend should not decide whether a feed is publishable from the device clock.

### Daily timeline

- AI news generation target: `08:30:00` KST.
- Home feed publication window: `09:00:00` KST through next-day `02:59:59` KST.
- Pre-publication window: `03:00:00` KST through `08:59:59` KST.

### Expected examples

| KST request time | Server home-feed result |
|---|---|
| `2026-05-31 02:59:59` | show `feed_date=2026-05-30` |
| `2026-05-31 03:00:00` | do not show a home feed; return pre-publication state |
| `2026-05-31 08:59:59` | do not show a home feed; return pre-publication state |
| `2026-05-31 09:00:00` | show `feed_date=2026-05-31` |
| `2026-06-01 02:59:59` | show `feed_date=2026-05-31` |
| `2026-06-01 03:00:00` | do not show a home feed; return pre-publication state |

## Server policy

Introduce a small server-side policy helper for the home feed window:

```text
resolve_home_feed_window(now_kst):
  if 00:00:00 <= now < 03:00:00:
    status = published
    feed_date = yesterday
    next_publish_at = today 09:00:00 KST
  elif 03:00:00 <= now < 09:00:00:
    status = before_publication
    feed_date = today
    next_publish_at = today 09:00:00 KST
  else:
    status = published
    feed_date = today
    next_publish_at = tomorrow 09:00:00 KST
```

`feed_date` means the product feed bucket date, not article `published_at` and not the request timestamp date.

## API behavior

`GET /v1/me/feed` should:

1. Resolve the home-feed window using server KST time.
2. If `status=before_publication`, return an explicit non-2xx response before touching snapshot generation or read/check-in state.
   - Proposed status: `425 Too Early`.
   - Proposed detail payload:
     ```json
     {
       "publication_status": "before_publication",
       "feed_date": "2026-05-31",
       "next_publish_at": "2026-05-31T09:00:00+09:00"
     }
     ```
3. If `status=published`, use the resolved `feed_date` for snapshot generation/lookup and mark the snapshot viewed as today.
4. Archive endpoints remain date-addressed and should keep reading explicit persisted `feed_date` values. The home-feed publication window should not hide archive access.

## Development plan

1. Add focused RED tests for the time policy boundaries:
   - `02:59:59` returns previous day and published.
   - `03:00:00` returns before-publication for today.
   - `08:59:59` returns before-publication for today.
   - `09:00:00` returns today and published.
   - next-day `02:59:59` still returns previous day.
   - next-day `03:00:00` returns before-publication for that day.
2. Add a route-contract RED test for `GET /v1/me/feed` during pre-publication:
   - response is `425`.
   - detail includes `publication_status`, `feed_date`, and `next_publish_at`.
   - snapshot service is not called.
3. Add a route-contract RED test for the early-morning published window:
   - request at `02:59:59` uses yesterday's `feed_date` when calling snapshot generation.
4. Implement the helper in `apps/backend/app/presentation/api/routes/users.py` or extract it to a small pure module if reuse grows.
5. Update route description/OpenAPI responses for `425`.
6. Run focused tests, then backend gate.

## Non-goals for this slice

- Do not change crawler GitHub Actions timing; crawler artifact creation can remain separate from feed publication.
- Do not change AI generation target `08:30:00`.
- Do not alter archive endpoint behavior beyond documentation if tests prove it remains date-addressed.
- Do not add frontend UI in this slice unless separately requested.
