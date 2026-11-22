# City Request

GTA-inspired Roblox group game finder.

## GitHub Pages

The site is static and uses clean folder routing:

- `/` → `index.html`
- `/requestor/` → `requestor/index.html`

In GitHub, open **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/(root)`.

## Random game picker

The requestor runs entirely in the visitor's browser. It:

- Loads up to 9 pages of members from Roblox group `34356929`.
- Randomly checks up to 100 members' public experiences.
- Selects a random experience whose maximum server size is exactly 3 players.
- Shows its thumbnail, player count, visits and dates.
- Builds the Linkvertise destination and displays the configured key.

No Render service, Python backend or API hosting is required. The picker calls public Roblox APIs directly from the browser. If Roblox blocks cross-origin browser requests (CORS) or rate-limits them, the scan may fail; a static GitHub Pages site cannot bypass those browser/API restrictions by itself.
