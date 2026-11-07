"""Blind voice comparison for the listening test (mediator-voice task 0.4, ADR-010).

Speaks every relay in docs/voice-test.md with each configured voice (OpenAI, ElevenLabs, Azure) and
writes server/voice-samples/index.html, with each line's clips shuffled under the letters A, B, and C
so the speakers rate the voices without knowing the vendor. The letter-to-vendor key goes in
voice-samples/key.json; open it only after the ratings are in. Makes paid calls; never prints a key.

Usage (from server/): uv run python scripts/voice_samples.py
Keys from server/.env: OPENAI_API_KEY, AZURE_SPEECH_KEY, and AZURE_SPEECH_REGION; ELEVENLABS_API_KEY from
the project's .env.local, where `npx @elevenlabs/cli onboard` puts it (ELEVENLABS_VOICE_ID optional, in
either file). A voice without its key is skipped.

@implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
"""

import asyncio
import html
import json
import os
import random
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import httpx2 as httpx
from elevenlabs import AsyncElevenLabs

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from scripts.check_keys import ENV_FILE, LANGUAGES_TS, parse_env  # noqa: E402

ELEVEN_ENV_FILE = SERVER.parent / ".env.local"
VOICE_TEST = SERVER.parent / "docs" / "voice-test.md"
OUT = SERVER / "voice-samples"

OPENAI_MODEL, OPENAI_VOICE = "gpt-4o-mini-tts", "marin"  # marin: OpenAI's recommended voice
ELEVEN_MODEL = "eleven_v4"
# Sarah ("mature, reassuring, confident"): an account voice, which free plans can use through the API
# (library voices need a paid plan); female like the OpenAI and Azure voices, so all three match.
ELEVEN_VOICE = "EXAVITQu4vr4xnSDxMaL"
# The same plain delivery for every voice, so the test compares voices, not instructions.
DELIVERY = "A warm, calm medical interpreter. Speak clearly and at a steady pace."


def relays(markdown: str) -> list[dict]:
    """Rows of the Relays table: line, speaker, and the relay text with the language it is in."""
    rows = []
    for line in markdown.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 4 or not re.match(r"(pa-IN|fr-CA) \d", cells[0]):
            continue
        visit_language, number = cells[0].split()
        language = visit_language if cells[1] == "physician" else "en-CA"
        rows.append({"id": f"{visit_language}-{number}", "language": language, "text": cells[3].replace("\\|", "|")})
    return rows


def azure_voices() -> dict[str, str]:
    return dict(re.findall(r'"(\w\w-\w\w)": "([\w-]+Neural)"', LANGUAGES_TS.read_text(encoding="utf-8")))


async def openai_speech(client: httpx.AsyncClient, env: dict, text: str, language: str) -> bytes:
    response = await client.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {env['OPENAI_API_KEY']}"},
        json={
            "model": OPENAI_MODEL,
            "voice": OPENAI_VOICE,
            "input": text,
            "instructions": DELIVERY,
            "response_format": "mp3",
        },
    )
    response.raise_for_status()
    return response.content


async def eleven_speech(client: AsyncElevenLabs, voice_id: str, text: str, language: str) -> bytes:
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=ELEVEN_MODEL,
        language_code=language.split("-")[0],  # "pa", "fr", "en"
        output_format="mp3_44100_128",
    )
    return b"".join([chunk async for chunk in audio])


async def azure_speech(client: httpx.AsyncClient, env: dict, text: str, language: str, voices: dict) -> bytes:
    ssml = f'<speak version="1.0" xml:lang="{language}"><voice name="{voices[language]}">{escape(text)}</voice></speak>'
    response = await client.post(
        f"https://{env['AZURE_SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": env["AZURE_SPEECH_KEY"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        },
        content=ssml.encode("utf-8"),
    )
    response.raise_for_status()
    return response.content


def page(rows: list[dict], letters: dict[str, dict[str, str]]) -> str:
    items = []
    for row in rows:
        players = "".join(
            f'<div class="clip"><b>{letter}</b><audio controls preload="none" src="{row["id"]}-{letter}.mp3"></audio></div>'
            for letter in sorted(letters[row["id"]])
        )
        items.append(
            f'<section><h2>{row["id"]}</h2><p lang="{row["language"]}">{html.escape(row["text"])}</p>{players}</section>'
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Voice listening test</title><style>
body {{ font: 17px/1.5 system-ui, sans-serif; max-width: 860px; margin: 0 auto; padding: 32px 16px; }}
section {{ border-top: 1px solid #ccc; padding: 16px 0; }} h2 {{ font-size: 13px; letter-spacing: .1em; }}
.clip {{ display: flex; align-items: center; gap: 12px; margin: 6px 0; }}
</style></head><body><h1>Voice listening test</h1>
<p>For each line, play A, B, and C. Note which sounds most like a person interpreting, and any mispronounced word.
The vendors are hidden on purpose.</p>{"".join(items)}</body></html>"""


async def main() -> None:
    env = {}
    for path in (ENV_FILE, ELEVEN_ENV_FILE):
        if path.exists():
            env.update(parse_env(path.read_text(encoding="utf-8")))
    rows = relays(VOICE_TEST.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=60) as client:
        vendors = {}
        if env.get("OPENAI_API_KEY"):
            vendors["openai"] = lambda text, lang: openai_speech(client, env, text, lang)
        if env.get("ELEVENLABS_API_KEY"):
            # The key comes from the env file into the environment; it never appears in code or output.
            # Passed explicitly: the SDK reads ELEVENLABS_API_KEY at import, before this script loads the file.
            os.environ["ELEVENLABS_API_KEY"] = env["ELEVENLABS_API_KEY"]
            eleven = AsyncElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
            voice_id = env.get("ELEVENLABS_VOICE_ID") or ELEVEN_VOICE
            vendors["elevenlabs"] = lambda text, lang: eleven_speech(eleven, voice_id, text, lang)
        if env.get("AZURE_SPEECH_KEY") and env.get("AZURE_SPEECH_REGION"):
            voices = azure_voices()
            vendors["azure"] = lambda text, lang: azure_speech(client, env, text, lang, voices)
        missing = {"openai", "elevenlabs", "azure"} - vendors.keys()
        if missing:
            print(f"Skipping (no key in server/.env): {', '.join(sorted(missing))}")
        if not vendors:
            sys.exit("No voice keys configured.")

        shuffle = random.Random()
        letters: dict[str, dict[str, str]] = {}
        for row in rows:
            order = list(vendors)
            shuffle.shuffle(order)
            letters[row["id"]] = dict(zip("ABC", order, strict=False))
            for letter, vendor in list(letters[row["id"]].items()):
                try:
                    audio = await vendors[vendor](row["text"], row["language"])
                except Exception as exc:  # one failed clip should not end the run, or leave an empty player
                    status = getattr(getattr(exc, "response", None), "status_code", None) or getattr(
                        exc, "status_code", ""
                    )
                    print(f"{row['id']} {letter}: {vendor} failed {status} {type(exc).__name__}")
                    del letters[row["id"]][letter]
                    continue
                (OUT / f"{row['id']}-{letter}.mp3").write_bytes(audio)
            print(f"{row['id']}: {len(letters[row['id']])} clips", flush=True)

    (OUT / "key.json").write_text(json.dumps(letters, indent=2) + "\n", encoding="utf-8")
    (OUT / "index.html").write_text(page(rows, letters), encoding="utf-8")
    print(f"Open {OUT / 'index.html'}; the answer key is {OUT / 'key.json'}.")


if __name__ == "__main__":
    asyncio.run(main())
