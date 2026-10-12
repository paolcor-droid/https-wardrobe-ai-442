# LUMIÈRE — Android-first staging device test

**State: not executed on a physical device.** The user has an Android phone.
Never expose private Codespaces MongoDB or FastAPI ports to the internet.
No real account photographs should be used.

## Prerequisites
1. Provision a protected HTTPS staging API with a disposable MongoDB and
   the private Supabase test bucket. The Codespaces FastAPI loopback address
   cannot be reached from an Android handset; a safe authenticated staging
   endpoint and review of CORS, origin and cookie security are required.
2. Configure an Android development/preview build using a **staging**
   `EXPO_PUBLIC_BACKEND_URL`; no Supabase secret, Resend key, or database
   credentials in the Expo binary or environment variables prefixed `EXPO_PUBLIC_`.
3. Build and install a signed internal Android preview (Expo EAS or equivalent).
   Store build artifact and manifest privately. Record build SHA and Android OS.
4. Use two disposable test accounts and synthetic or explicitly consented photos.

## Android acceptance (owner run)
A01: Install, launch, register A and B, sign in, and navigate You/Discover/
Stylist/Wardrobe/Try-On. No cached A information after changing to B.
A02: Upload new test photo; verify private Supabase object; check camera/gallery
permissions, crop/orientation, background/relaunch.
A03: Run colour analysis and view the saved image after reopening the app.
A04: Delete the newly uploaded test photograph via the UI. Confirm the same
object is absent in Supabase and an authenticated API read returns 404.
A05: Try an unauthorized cross-account photo URL; expect 404.
A06: Reset password through a delivered email on a disposable account. Old
password and pre-reset sessions must fail; reset link may be used once.
A07: Interrupt network during image upload and resume; confirm no false
success or wrong-account content.
A08: Verify styling and Try-On outputs on Android using consented fixtures.

For each item record PASS/FAIL, test date, phone model/OS, build SHA, staging
origin, redacted screenshots, and issue. **No automatic completion claim.**

iOS remains a separate required physical-device signoff; an Android PASS
does not certify iOS.
