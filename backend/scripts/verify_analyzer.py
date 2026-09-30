"""Opt-in raw classifier check: run `python -m scripts.verify_analyzer` from backend.

Real provider calls using synthetic examples; validates the first JSON response
without retries or deterministic mode corrections. Never prints reasoning or keys.
"""
import asyncio
import json

from app.schemas import Analysis
from app.services.groq import GroqProvider, ProviderError
from app.services.state import ANALYZER_PROMPT
from scripts.verify_live import CASES


async def main():
    provider = GroqProvider()
    failures = 0
    for message, mode, sensitivity in CASES:
        try:
            raw = await provider.complete([
                {"role": "system", "content": ANALYZER_PROMPT},
                {"role": "user", "content": message},
            ], json_mode=True)
            result = Analysis.model_validate_json(raw)
            passed = result.mode == mode and result.sensitivity == sensitivity
            if "don't know if I want advice" in message:
                passed = passed and result.confidence < .6
            failures += not passed
            print(json.dumps({"input": message, "passed": passed, "schema_valid": True, "analysis": result.model_dump()}, ensure_ascii=True), flush=True)
        except ProviderError as error:
            failures += 1
            print(json.dumps({"input": message, "passed": False, "error": error.code}), flush=True)
            if error.status in (429, 503):
                raise SystemExit("Stopped: provider quota/configuration needs attention.")
        except ValueError:
            failures += 1
            print(json.dumps({"input": message, "passed": False, "schema_valid": False}), flush=True)
    print(f"Raw analyzer cases: {len(CASES)}; failures: {failures}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
