# Android staging API connection — deployment gate

The Samsung Galaxy S22 Ultra successfully launched LUMIÈRE in Expo Go through an Expo tunnel, and the user confirmed Stylist, Discover, Wardrobe, Try-On and You navigation. **Account/login/photo/AI calls have not been verified on Android.**

## Current environment
- Expo tunnel delivers JavaScript only; it does **not** proxy FastAPI on port 8000.
- The existing Codespaces MongoDB, FastAPI on 127.0.0.1:8000, Expo on 8081, and Resend/Supabase secrets must stay private. **Do not make FastAPI port 8000 or MongoDB 27018 public.**
- Native requests now fail with an explicit configuration error if `EXPO_PUBLIC_BACKEND_URL` is missing or not an HTTPS origin, rather than silently using the Metro origin. This check is applied lazily so offline navigation still opens in Expo Go. This is not authentication for the server.
- `EXPO_PUBLIC_BACKEND_URL` is public **by design** and must include only a nonsecret HTTPS host, never credentials, API keys, tokens, or a private URL containing authorization parameters.

## Prerequisites for API-linked Android test (not completed)
1. Provision a separately authenticated, access-controlled HTTPS **staging API**, staging MongoDB and disposable test accounts. Prefer dedicated cloud resources and data separation. Do **not** reuse the Codespaces database containing existing profiles.
2. Configure private Supabase staging/test storage and backend-only service key; verify the bucket's privacy; apply fail-closed distributed throttling; verify staging CORS/TLS and no legacy unauthenticated endpoints.
3. Confirm staging HTTPS origin is accessible from the phone *only to authorized testers*. Restrict APIs at the gateway and in FastAPI; mobile clients must authenticate at the application layer. A Codespaces forwarded/private URL is not automatically a production-appropriate mobile API.
4. Start Expo from a clean private development environment with `EXPO_PUBLIC_BACKEND_URL=https://<staging-origin>` and rebuild/restart Metro; install an internal app only after secure staging is operational.
5. Complete Android A01–A08 in `docs/ANDROID_FIRST_DEVICE_PLAN.md` and capture test evidence.

No staging server, Android APK, production rollout, or external private-network proxy was created by the current changes. Keep public release blocked.
