import os
import time
import random
import base64
import asyncio
from collections import deque
from datetime import datetime, timezone

import aiohttp
from aiohttp import web

GROUP_ID = int(os.getenv("GROUP_ID", "34356929"))
AFFILIATE_ID = os.getenv("AFFILIATE_ID", "6692596")
KEY = os.getenv("LV_KEY", "discordggreceb")
MAX_PLAYERS = 3
MEMBER_PAGES = 9
MEMBER_CACHE_TTL = 600
BATCH_SIZE = 15
MAX_BATCHES = 12
CONCURRENCY = 5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CityRequest/1.0)",
    "Accept": "application/json",
}
members_cache = {"ts": 0.0, "ids": []}
recent_games = deque(maxlen=200)
search_lock = asyncio.Lock()


async def api_get(session, url, retries=3):
    for _ in range(retries):
        try:
            async with session.get(url, headers=HEADERS,
                                   timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    return await r.json()
                if r.status == 429:
                    try:
                        delay = min(float(r.headers.get("Retry-After", 2)), 10)
                    except ValueError:
                        delay = 2
                    await asyncio.sleep(delay)
                    continue
                print(f"[Roblox API] HTTP {r.status}: {url[:100]}")
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            print(f"[Roblox API] {exc}")
            await asyncio.sleep(1)
    return None


async def fetch_members(session):
    now = time.time()
    if members_cache["ids"] and now - members_cache["ts"] < MEMBER_CACHE_TTL:
        ids = members_cache["ids"][:]
    else:
        ids, cursor = [], None
        for _ in range(MEMBER_PAGES):
            url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users?sortOrder=Desc&limit=100"
            if cursor:
                url += f"&cursor={cursor}"
            data = await api_get(session, url)
            if not data:
                break
            ids.extend(row["user"]["userId"] for row in data.get("data", []) if row.get("user"))
            cursor = data.get("nextPageCursor")
            if not cursor:
                break
        if ids:
            members_cache.update(ts=now, ids=ids[:])
        elif members_cache["ids"]:
            ids = members_cache["ids"][:]
    random.shuffle(ids)
    return ids


async def fetch_user_games(session, user_id, semaphore):
    url = f"https://games.roblox.com/v2/users/{user_id}/games?sortOrder=Desc&limit=50&accessFilter=2"
    async with semaphore:
        data = await api_get(session, url)
    if not data:
        return []
    return [g for g in data.get("data", []) if (g.get("rootPlace") or {}).get("id")]


async def fetch_details(session, universe_ids):
    details = {}
    for start in range(0, len(universe_ids), 100):
        chunk = universe_ids[start:start + 100]
        params = "&".join(f"universeIds={uid}" for uid in chunk)
        data = await api_get(session, f"https://games.roblox.com/v1/games?{params}")
        if data:
            details.update({g["id"]: g for g in data.get("data", [])})
    return details


async def fetch_icon(session, universe_id):
    url = ("https://thumbnails.roblox.com/v1/games/icons"
           f"?universeIds={universe_id}&returnPolicy=PlaceHolder&size=256x256&format=Png&isCircular=false")
    data = await api_get(session, url)
    try:
        item = data["data"][0]
        if item.get("state") == "Completed":
            return item.get("imageUrl")
    except (TypeError, KeyError, IndexError):
        pass
    return None


async def pick_game(session):
    members = await fetch_members(session)
    if not members:
        return None
    semaphore = asyncio.Semaphore(CONCURRENCY)
    checked = set()
    limit = min(len(members), BATCH_SIZE * MAX_BATCHES)
    for start in range(0, limit, BATCH_SIZE):
        batch = members[start:start + BATCH_SIZE]
        results = await asyncio.gather(*(fetch_user_games(session, uid, semaphore) for uid in batch))
        candidates = {}
        for games in results:
            for game in games:
                gid = game.get("id")
                if gid and gid not in checked and gid not in recent_games:
                    candidates[gid] = game
        if not candidates:
            continue
        checked.update(candidates)
        details = await fetch_details(session, list(candidates))
        eligible = []
        for gid, game in candidates.items():
            info = details.get(gid)
            if info and info.get("maxPlayers") == MAX_PLAYERS:
                game["_info"] = info
                eligible.append(game)
        print(f"[scanner] batch {start // BATCH_SIZE + 1}: {len(candidates)} games, {len(eligible)} eligible")
        if eligible:
            chosen = random.choice(eligible)
            recent_games.append(chosen["id"])
            return chosen
    return None


def linkvertise_url(place_id):
    destination = f"https://www.roblox.com/games/start?placeId={place_id}"
    encoded = base64.urlsafe_b64encode(destination.encode()).decode().rstrip("=")
    salt = random.randint(100000, 999999)
    return f"https://linkvertise.com/{AFFILIATE_ID}/{salt}/dynamic?r={encoded}"


async def generate(request):
    if search_lock.locked():
        return web.json_response({"error": "A search is already running. Please wait a moment."}, status=429)
    async with search_lock:
        game = await pick_game(request.app["session"])
        if not game:
            return web.json_response({"error": "No game with a maximum of exactly 3 players was found among the checked group members. Try again later."}, status=404)
        info = game.get("_info", {})
        place_id = game["rootPlace"]["id"]
        icon = await fetch_icon(request.app["session"], game["id"])
        payload = {
            "name": game.get("name") or "Roblox Game",
            "playing": info.get("playing") or 0,
            "maxPlayers": info.get("maxPlayers") or MAX_PLAYERS,
            "visits": info.get("visits") or 0,
            "created": info.get("created"),
            "updated": info.get("updated"),
            "iconUrl": icon,
            "gameUrl": f"https://www.roblox.com/games/{place_id}",
            "linkvertiseUrl": linkvertise_url(place_id),
            "key": KEY,
        }
        return web.json_response(payload)


async def health(request):
    return web.json_response({"status": "ok", "groupId": GROUP_ID, "maxPlayers": MAX_PLAYERS})


async def on_startup(app):
    app["session"] = aiohttp.ClientSession()


async def on_cleanup(app):
    await app["session"].close()


def create_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/api/generate", generate)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    web.run_app(create_app(), host="0.0.0.0", port=port)