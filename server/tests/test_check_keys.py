"""scripts/check_keys.py: catches bad keys, regions, and voices before a live run (ADR-005, ADR-006)."""

import asyncio
import json

import anthropic
import httpx2 as httpx

from config import LIVE_MODEL, RECORD_MODEL
from scripts.check_keys import LANGUAGES_TS, check_azure, check_claude, configured_voices, env_problems, parse_env

GOOD = {"ANTHROPIC_API_KEY": "sk-ant-abc123", "AZURE_SPEECH_KEY": "f00dfeed", "AZURE_SPEECH_REGION": "canadacentral"}
VOICES = {"pa-IN": "pa-IN-VaaniNeural", "en-CA": "en-CA-ClaraNeural"}


def test_parse_env_reads_values_like_dev_sh():
    text = "# comment\nANTHROPIC_API_KEY=sk-ant-abc\n\nTRANSLATOR=\n AZURE_SPEECH_REGION = canadacentral \n"
    assert parse_env(text) == {
        "ANTHROPIC_API_KEY": "sk-ant-abc",
        "TRANSLATOR": "",
        "AZURE_SPEECH_REGION": "canadacentral",
    }


def test_env_problems_catch_common_mistakes():
    assert env_problems(GOOD) == []
    problems = env_problems(
        {**GOOD, "ANTHROPIC_API_KEY": "", "AZURE_SPEECH_KEY": '"f00d"', "AZURE_SPEECH_REGION": "Canada Central"}
    )
    assert any("ANTHROPIC_API_KEY is empty" in p for p in problems)
    assert any("AZURE_SPEECH_KEY has quotes" in p for p in problems)
    assert any("AZURE_SPEECH_REGION" in p for p in problems)


def test_voices_come_from_the_web_app():
    voices = configured_voices(LANGUAGES_TS.read_text())
    assert set(voices) == {"pa-IN", "fr-CA", "en-CA"} and voices["pa-IN"].endswith("Neural")


def azure(token_status: int, voice_names: list[str]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/issueToken"):
            return httpx.Response(token_status, text="token")
        return httpx.Response(200, json=[{"ShortName": name} for name in voice_names])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_azure_ok_when_token_and_voices_exist():
    assert asyncio.run(check_azure("k", "canadacentral", VOICES, azure(200, list(VOICES.values())))) == []


def test_azure_reports_a_missing_voice():
    problems = asyncio.run(check_azure("k", "canadacentral", VOICES, azure(200, ["en-CA-ClaraNeural"])))
    assert problems == ["voice pa-IN-VaaniNeural for pa-IN is not offered in canadacentral"]


def test_azure_reports_a_rejected_key():
    problems = asyncio.run(check_azure("k", "canadacentral", VOICES, azure(401, [])))
    assert problems and "rejected AZURE_SPEECH_KEY" in problems[0]


def claude(statuses: dict[str, int]) -> anthropic.Anthropic:
    def handler(request: httpx.Request) -> httpx.Response:
        model = request.url.path.rsplit("/", 1)[-1]
        status = statuses[model]
        if status == 200:
            body = {"id": model, "type": "model", "display_name": model, "created_at": "2026-01-01T00:00:00Z"}
        else:
            body = {"type": "error", "error": {"type": "error", "message": "no"}}
        return httpx.Response(status, content=json.dumps(body), headers={"content-type": "application/json"})

    return anthropic.Anthropic(
        api_key="sk-test", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_claude_ok_when_both_models_are_available():
    assert check_claude("sk-test", claude({LIVE_MODEL: 200, RECORD_MODEL: 200})) == []


def test_claude_reports_a_rejected_key():
    assert check_claude("sk-test", claude({LIVE_MODEL: 401, RECORD_MODEL: 401})) == [
        "Claude rejected ANTHROPIC_API_KEY (check it was copied whole)"
    ]


def test_claude_reports_a_model_the_key_cannot_use():
    assert check_claude("sk-test", claude({LIVE_MODEL: 200, RECORD_MODEL: 404})) == [
        f"this key cannot use {RECORD_MODEL}"
    ]
