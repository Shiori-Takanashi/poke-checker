import asyncio, aiohttp, aiofiles, json
from pathlib import Path
from tqdm.asyncio import tqdm_asyncio  # tqdm>=4.66 ならOK

URL = "https://pokeapi.co/api/v2/pokemon?limit=1025"

async def fetch_json(session, url):
    async with session.get(url) as r:
        r.raise_for_status()
        return await r.json()

async def save_json(path: Path, data: dict):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

async def fetch_and_save(session, url, save_dir):
    json_data = await fetch_json(session, url)
    pid = url.rstrip("/").split("/")[-1]
    path = save_dir / f"{pid}.json"
    await save_json(path, json_data)

async def main():
    save_dir = Path("poke")

    # 既存ディレクトリがあれば中身削除
    if save_dir.exists():
        for item in save_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                for sub in item.glob("**/*"):
                    if sub.is_file():
                        sub.unlink()
                item.rmdir()
    save_dir.mkdir(exist_ok=True)

    async with aiohttp.ClientSession() as session:
        # 一覧取得
        data = await fetch_json(session, URL)
        items = data["results"]  # ← 1025件すべて使う
        urls = [item["url"] for item in items]

        # URLをファイルに保存
        urls_file = save_dir / "urls.json"
        urls_file.write_text(json.dumps(urls, indent=2, ensure_ascii=False), encoding="utf-8")

        # 並列で詳細取得＋保存
        await tqdm_asyncio.gather(*[
            fetch_and_save(session, url, save_dir) for url in urls
        ])

if __name__ == "__main__":
    asyncio.run(main())
