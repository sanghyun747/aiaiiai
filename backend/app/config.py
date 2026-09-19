import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = BASE_DIR / ".runtime"


def load_env() -> None:
    """Load backend/.env without extra dependencies. Never logs values."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

CONTRACT_VERSION = "1.1.0"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_ZIP_ENTRIES = 500
MAX_UNCOMPRESSED_BYTES = 80 * 1024 * 1024
MAX_CONCURRENT_JOBS = 2

ARTIFACT_NAMES = (
    "report.md",
    "content-strategy.json",
    "script.md",
    "shot-list.json",
    "editing-guide.md",
    "thumbnail-plan.md",
    "publishing-package.md",
)


def configured() -> dict:
    """Key presence only. NOT proof of a successful remote call."""
    return {
        "nosana": bool(os.environ.get("NOSANA_API_KEY")),
        "daytona": bool(os.environ.get("DAYTONA_API_KEY")),
        "dnsimple": bool(os.environ.get("DNSIMPLE_API_TOKEN")),
        "youtube": bool(os.environ.get("YOUTUBE_API_KEY")),
    }


def live_providers_enabled() -> bool:
    return os.environ.get("TRENDPILOT_LIVE_PROVIDERS", "1") == "1"


def replay_mode_enabled() -> bool:
    """Explicit opt-in labelled demo replay: Nosana plan/recommend are taken
    from fixtures/run-sample.json instead of live inference. Daytona analyze and
    render still execute for real. This is NEVER a fallback for a live failure -
    it only activates when TRENDPILOT_LIVE_PROVIDERS=0 is set on purpose."""
    return os.environ.get("TRENDPILOT_LIVE_PROVIDERS", "1") == "0"


REPLAY_NOTICE = (
    "데모 재생(replay) 모드입니다. 전략/추천 3안은 fixtures/run-sample.json의 고정 예시이며 "
    "Nosana 실시간 추론 결과가 아닙니다. Daytona 샌드박스 분석과 산출물 렌더링은 실제로 실행되었습니다."
)
