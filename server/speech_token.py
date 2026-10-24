"""Short-lived Azure Speech tokens so the key never reaches the browser.

@implements ADR-005: Speech: Azure Speech primary, Google Speech backup
@see openspec/tdr/adr/adr-005-speech-provider.md
"""

import httpx2 as httpx

# Azure tokens last 10 minutes; the browser refreshes before this.
TOKEN_LIFETIME_SECONDS = 540


class SpeechNotConfigured(Exception):
    pass


async def issue_token(key: str | None, region: str | None, client: httpx.AsyncClient | None = None) -> dict:
    if not key or not region:
        raise SpeechNotConfigured("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10.0)
    try:
        response = await client.post(url, headers={"Ocp-Apim-Subscription-Key": key})
        response.raise_for_status()
        return {"token": response.text, "region": region, "expiresInSeconds": TOKEN_LIFETIME_SECONDS}
    finally:
        if owns_client:
            await client.aclose()
