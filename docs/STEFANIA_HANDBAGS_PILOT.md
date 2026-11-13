# Stefania P. Creations handbag pilot

This branch adds an isolated Handbags tab and 18 authorised handbag product records, with colour filters and saved-preference colour sorting.

## Commercial safeguards
- Supplier permissions were confirmed by the project owner.
- No price has yet been supplied: prices are `null`; the UI says "Price on request".
- No live stock or checkout is claimed. No transaction is available.
- No MongoDB migration, customer data writes, or changes to existing AI outfit routines.

## Important outstanding asset step
The **18 source hero JPGs have not yet been uploaded into this Git branch**. The screen deliberately displays a neutral holding panel rather than a broken or falsely attributed image. The pictures are present in the supplied integration archive but the connected GitHub API only accepts UTF-8 text via the accessible file-writing action. Do not merge/deploy this PR as a completed photo catalogue until images are uploaded.

Photo filenames expected:
`frontend/assets/spc-handbags/SPC-FW2627-01_hero.jpg` through `SPC-FW2627-18_hero.jpg`.

After adding images, update each catalogue record's `image` with a **static** Expo/Metro require, e.g. `require("../assets/spc-handbags/SPC-FW2627-01_hero.jpg")`. Dynamic requires do not work in Metro. Keep unverified prices, invented stock and shopping disabled.

## Validation
Run `cd frontend && npx tsc --noEmit` and launch Expo on web and mobile after transferring the image assets.
