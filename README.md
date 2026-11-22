# City Request

GTA-inspired Roblox group game finder.

## GitHub Pages

The site is static and uses clean folder routing:

- `/` → `index.html`
- `/requestor/` → `requestor/index.html`

In GitHub, open **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/(root)`.

## Backend (required for live scanning)

GitHub Pages cannot run Python. Deploy this repository as a separate Render Web Service using the included `render.yaml` (or create a Python web service manually):

- Build command: `pip install -r requirements.txt`
- Start command: `python backend.py`

Set environment variables:
- `GROUP_ID=34356929`
- `AFFILIATE_ID=6692596`
- `LV_KEY=your Linkvertise key`

After Render deploys, edit `requestor/index.html` and replace `https://YOUR-RENDER-SERVICE.onrender.com` in `API_BASE` with your actual Render service URL.

## Scanner behavior

- Loads up to 9 pages of 100 members from Roblox group 34356929.
- Checks public games created by those members in batches.
- Selects only experiences whose `maxPlayers` is exactly 3.
- Avoids repeating the last 200 selected games while the backend process remains running.
- Returns game name, thumbnail, current players, max players, visits, created/updated dates, Linkvertise URL and key.

The API performs Roblox requests server-side. Do not put private Discord bot tokens in frontend code.
