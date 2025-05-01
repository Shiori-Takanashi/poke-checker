import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Generator, List, Any

from tqdm import tqdm

# ── ログ設定 ──────────────────────────────────────────
LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
_BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = _BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True) # Ensure log directory exists
LOG_PATH = LOG_DIR / f"{Path(__file__).stem}.log"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# ── データモデル ──────────────────────────────────────
@dataclass
class PokemonForm:
    unique_id: str
    species_name: str
    name: str
    forms_name: str
    forms_url: str
    form_status: str

# ── ユーティリティ ────────────────────────────────────
def load_json_generator(directory: Path) -> Generator[tuple[str, Any], None, None]:
    """ディレクトリ内 *.json を逐次読み込むジェネレータ"""
    for jf in directory.glob("*.json"):
        try:
            with jf.open(encoding="utf-8") as f:
                yield jf.stem, json.load(f)
        except Exception as e:
            logger.error("load error %s: %s", jf, e)

def normalize_species_name(data: dict) -> str:
    species = data.get("species")
    if isinstance(species, dict):
        name = species.get("name")
        if isinstance(name, str):
            return name
    return "ERROR"

def normalize_form_status(is_default: Any) -> str:
    match is_default:
        case True:
            return "基本形"
        case False:
            return "変化形"
        case _:
            return "ERROR"

# ── 主要処理 ──────────────────────────────────────────
def parse_pokemon_data(fid: str, data: Any) -> List[PokemonForm]:
    if not isinstance(data, dict):
        logger.warning("%s: root not dict", fid)
        return []

    # 基本フィールド
    forms = data.get("forms") if isinstance(data.get("forms"), list) else []
    if not forms:
        logger.warning("%s: forms missing or invalid", fid)

    name = data.get("name") if isinstance(data.get("name"), str) else "ERROR"
    if name == "ERROR":
        logger.warning("%s: name invalid", fid)

    species_name = normalize_species_name(data)
    if species_name == "ERROR":
        logger.warning("%s: species name invalid", fid)

    form_status = normalize_form_status(data.get("is_default"))
    if form_status == "ERROR":
        logger.warning("%s: is_default invalid", fid)

    # 各フォームを dataclass 化
    results: list[PokemonForm] = []
    for idx, form in enumerate(forms):
        if isinstance(form, dict):
            fname = form.get("name") if isinstance(form.get("name"), str) else "ERROR"
            furl  = form.get("url")  if isinstance(form.get("url"),  str) else "ERROR"
        else:
            fname = furl = "ERROR"

        if "ERROR" in (fname, furl):
            logger.warning("%s: form entry invalid %d", fid, idx)

        uid = f"{int(fid):05d}-{idx:02d}"
        results.append(
            PokemonForm(uid, species_name, name, fname, furl, form_status)
        )

    return results

def save_results(results: List[PokemonForm], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=4)
    logger.info("saved %d entries -> %s", len(results), path)

# ── エントリポイント ──────────────────────────────────
def main() -> None:
    base   = Path(__file__).resolve().parent
    in_dir = base / "data" / "pokemon-pokemon"
    out_fp = base / "data_set" / "pokemon_set.json"

    logger.info("start load %s", in_dir)
    results: list[PokemonForm] = []
    for fid, data in tqdm(load_json_generator(in_dir), desc="parse"):
        results.extend(parse_pokemon_data(fid, data))

    results.sort(key=lambda x: x.unique_id)
    save_results(results, out_fp)
    logger.info("finish")

if __name__ == "__main__":
    main()
