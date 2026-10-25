"""Check server/.env before a live run: the Claude key and models, and the Azure Speech key, region,
and voices. Makes no paid calls and never prints a key.

Usage (from server/): uv run python scripts/check_keys.py

@implements ADR-005: Speech: Azure Speech primary, Google Speech backup
@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
"""

import asyncio
import re
import sys
from pathlib import Path

import anthropic
import httpx2 as httpx

SERVER = Path(__file__).resolve().parents[1]
# Scripts run with scripts/ on the import path; the server modules live one level up.
sys.path.insert(0, str(SERVER))

from config import LIVE_MODEL, RECORD_MODEL, TONE_MODEL  # noqa: E402
from speech_token import issue_token  # noqa: E402

ENV_FILE = SERVER / ".env"
LANGUAGES_TS = SERVER.parent / "web" / "lib" / "languages.ts"


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines as scripts/dev.sh reads them; comments and blank lines skipped."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def env_problems(values: dict[str, str]) -> list[str]:
    """Mistakes that make a key look set but fail: missing, quoted, or with a placeholder left in."""
    problems = []
    for key in ("ANTHROPIC_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"):
        value = values.get(key, "")
        if not value:
            problems.append(f"{key} is empty")
        elif value[0] in "\"'" or " " in value:
            problems.append(f"{key} has quotes or spaces; paste the bare value after =")
        elif "<" in value or "your" in value.lower():
            problems.append(f"{key} still holds a placeholder")
    region = values.get("AZURE_SPEECH_REGION", "")
    if region and not re.fullmatch(r"[a-z0-9]+", region):
        problems.append("AZURE_SPEECH_REGION should look like canadacentral (lower case, no spaces)")
    return problems


def configured_voices(languages_ts: str) -> dict[str, str]:
    """The neural voice per language from web/lib/languages.ts, so this check never drifts from it."""
    block = languages_ts.split("VOICES", 1)[-1]
    return dict(re.findall(r'"([a-z]{2}-[A-Z]{2})":\s*"([\w-]+Neural)"', block))


def mask(secret: str) -> str:
    return f"...{secret[-4:]}" if len(secret) > 8 else "(set)"


def check_claude(key: str, client: anthropic.Anthropic | None = None) -> list[str]:
    client = client or anthropic.Anthropic(api_key=key, max_retries=1, timeout=20)
    problems = []
    for model in (LIVE_MODEL, TONE_MODEL, RECORD_MODEL):
        try:
            client.models.retrieve(model)
        except anthropic.AuthenticationError:
            return ["Claude rejected ANTHROPIC_API_KEY (check it was copied whole)"]
        except (anthropic.NotFoundError, anthropic.PermissionDeniedError):
            problems.append(f"this key cannot use {model}")
        except anthropic.APIConnectionError:
            return ["could not reach api.anthropic.com (check the network)"]
    return problems


async def check_azure(
    key: str, region: str, voices: dict[str, str], client: httpx.AsyncClient | None = None
) -> list[str]:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=20.0)
    try:
        try:
            await issue_token(key, region, client)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                return [f"Azure rejected AZURE_SPEECH_KEY for region {region} (key and region must match)"]
            return [f"Azure token request failed with HTTP {exc.response.status_code}"]
        except httpx.HTTPError:
            return [f"could not reach {region}.api.cognitive.microsoft.com (check AZURE_SPEECH_REGION)"]
        response = await client.get(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
            headers={"Ocp-Apim-Subscription-Key": key},
        )
        response.raise_for_status()
        available = {v["ShortName"] for v in response.json()}
        return [
            f"voice {voice} for {lang} is not offered in {region}"
            for lang, voice in voices.items()
            if voice not in available
        ]
    finally:
        if owns_client:
            await client.aclose()


def main() -> int:
    if not ENV_FILE.exists():
        print("server/.env not found. Copy server/.env.example to server/.env and fill in the keys.")
        return 1
    values = parse_env(ENV_FILE.read_text())
    problems = env_problems(values)
    if problems:
        print("server/.env needs attention:")
        print("\n".join(f"  - {p}" for p in problems))
        return 1

    claude_key, speech_key, region = (
        values["ANTHROPIC_API_KEY"],
        values["AZURE_SPEECH_KEY"],
        values["AZURE_SPEECH_REGION"],
    )
    voices = configured_voices(LANGUAGES_TS.read_text())
    print(f"Claude key {mask(claude_key)}, Azure key {mask(speech_key)}, region {region}")

    results = {
        f"Claude ({LIVE_MODEL}, {TONE_MODEL}, {RECORD_MODEL})": check_claude(claude_key),
        f"Azure Speech (token and voices {', '.join(voices.values())})": asyncio.run(
            check_azure(speech_key, region, voices)
        ),
    }
    for name, found in results.items():
        print(f"{'ok ' if not found else 'FAIL'} {name}")
        for problem in found:
            print(f"     - {problem}")
    if values.get("TRANSLATOR", "") not in ("", "claude"):
        print(f"note TRANSLATOR={values['TRANSLATOR']} in server/.env; leave it blank for a live run")
    return 0 if not any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
