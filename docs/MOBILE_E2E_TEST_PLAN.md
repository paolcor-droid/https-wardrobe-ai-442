# LUMIÈRE real-device release verification (execution required)

**Status: NOT YET EXECUTED.** Android/iOS Metro export and TypeScript checks
do not demonstrate that the app works on physical devices.

## Preflight
- Build separate internal Android and iOS versions on a secured staging environment.
- Use a protected HTTPS FastAPI staging endpoint and disposable MongoDB. Do
  not make Codespaces private ports public to connect a phone.
- Confirm device API origin, environment keys, valid TLS certificate, and
  private photo storage (verified S3 or disposable local test-only environment).
- Use two disposable accounts and explicitly consented non-sensitive test images.
- Capture outcomes, build versions, OS versions and redacted error reports.

## Test cases on BOTH Android and iOS
| ID | Test | Expected result |
|----|------|-----------------|
| M01 | Register two unique accounts | Both can register; duplicate email rejected |
| M02 | Sign in, background, force quit and reopen | Session restored securely, only own data |
| M03 | Sign out then revisit You, Discover, Try-On and Wardrobe | Private data never appears |
| M04 | Switch between accounts A and B | No cached photo, preferences, look or chat leaks |
| M05 | Wait for token expiry / revoke via backend | Access denied, app shows sign-in |
| M06 | Request password recovery, follow deep link, reset password | One-use token and prior sessions revoked |
| M07 | Select photo from library and camera | Valid MIME, crop/orientation, size, permissions |
| M08 | Upload photo with network interrupted | Clear retry/error, no false success |
| M09 | Analyse two different faces using ChatGPT | Fresh per-photo results, own-account persistence |
| M10 | Save preferences and reopen | Only current customer's data persists |
| M11 | Retrieve Discover catalogue / styling chat | Own preferences affect result; no invented inventory |
| M12 | Try on one and two garments | Image generated, photorealism checked, owner-only result |
| M13 | Delete source photograph | 404 afterward; linked skin/try-on references removed |
| M14 | Delete generated Try-On image | Owner cannot read image, other account never could |
| M15 | Attempt cross-account URL/photo ID access | Server returns 404/401, no media bytes |
| M16 | Logout during upload, close/reopen app | No stale tokens, thumbnails or responses |
| M17 | Dark mode, screen reader, font scaling | Accessible navigation and legibility |
| M18 | Slow connection / expired credential | Graceful fail without exposing debug info |

## Sign-off format
For each case, capture: date, OS/device, build SHA, API environment,
PASS/FAIL, redacted evidence and issue link. Stop release on any privacy,
cross-account or deletion failure.

### Remaining prerequisites
- Live S3 test deletion and provider retention signoff.
- Staging SMTP password-recovery deliverability.
- Shared/distributed login and recovery rate limiting for production.
- Real ChatGPT / Gemini provider credentials and consented photo fixtures.
- Signed Android and iOS builds and actual physical devices.

Do not mark this plan complete based solely on Expo web preview.
