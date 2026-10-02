"""Small, explicit live editorial evaluation; never invoked by unit tests.

Usage: python scripts/evaluate_abridgement.py --levels standard compact
Uses the configured API key/model. Writes outputs under evaluation/.
"""
import argparse
import json
import sys
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.services.abridgement import AbridgementEngine
from api.config.settings import settings
from openai import OpenAI


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", nargs="+", default=["standard", "compact"],
                        choices=["light", "standard", "compact", "essence"])
    parser.add_argument("--revision", type=int, default=0)
    parser.add_argument("--epub", type=Path)
    parser.add_argument("--chapters", nargs="+", type=int, help="Zero-based TOC indices; required with --epub")
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation"))
    args = parser.parse_args()
    if args.epub and not args.chapters:
        parser.error("--epub requires an explicit --chapters selection")
    client = OpenAI(api_key=settings.openai_api_key, timeout=180, max_retries=1)
    print("Model:", settings.openai_default_model, flush=True)
    folder = args.output_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True, exist_ok=True)
    usage = {"input_tokens": 0, "output_tokens": 0}

    def complete(system, prompt):
        response = client.chat.completions.create(model=settings.openai_default_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, max_completion_tokens=12000,
            **({"reasoning_effort": "low"} if settings.openai_default_model.startswith(("gpt-5", "o3", "o4")) else {}))
        if response.usage:
            usage["input_tokens"] += response.usage.prompt_tokens
            usage["output_tokens"] += response.usage.completion_tokens
        if response.choices[0].finish_reason != "stop":
            raise ValueError("Incomplete model response: " + response.choices[0].finish_reason)
        return response.choices[0].message.content

    chapters = [{"title": "The Map and the Garden", "href": "sample", "text":
                 Path("tests/fixtures/editorial_sample.txt").read_text(encoding="utf-8")}]
    if args.epub:
        from ebooklib import epub
        from api.services.epub_structure import table_of_contents, chapter_text
        book = epub.read_epub(str(args.epub))
        toc = table_of_contents(book)
        if any(index < 0 or index >= len(toc) for index in args.chapters):
            parser.error("Chapter index outside the table of contents")
        chapters = [{"title": title, "href": href, "text": chapter_text(book, href, toc)}
                    for index, (title, href) in enumerate(toc) if index in args.chapters]
    manifest = {"model": settings.openai_default_model, "revision": args.revision,
                "source_sha256": hashlib.sha256(json.dumps(chapters, sort_keys=True).encode()).hexdigest(),
                "chapters": [{"title": c["title"], "href": c["href"], "words": len(c["text"].split())}
                             for c in chapters], "results": {}, "usage": usage}
    print("Output:", folder, flush=True)
    for level in args.levels:
        started = time.monotonic()
        usage_before = dict(usage)
        engine = AbridgementEngine(complete, args.output_dir / ".cache", settings.openai_default_model,
                                    lambda p, message: print(f"{p}% {message}", flush=True), revision=args.revision)
        try:
            result = engine.run(chapters, level)
            (folder / (level + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (folder / (level + ".txt")).write_text("\n\n".join(s["text"] for s in result["sections"]), encoding="utf-8")
            manifest["results"][level] = {"status": result["quality_status"], "words": result["word_count"],
                "ratio": result["actual_ratio"], "warnings": result["warnings"], "cache_hits": result["cache_hits"]}
            print(level, result["word_count"], result["quality_status"], flush=True)
        except Exception as error:
            manifest["results"][level] = {"status": "failed", "error": str(error)}
            print(level, "FAILED:", str(error), flush=True)
        finally:
            manifest["results"][level]["seconds"] = round(time.monotonic() - started, 2)
            manifest["results"][level]["usage"] = {key: value - usage_before[key] for key, value in usage.items()}
            (folder / "report.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(usage), flush=True)
    if any(r["status"] == "failed" for r in manifest["results"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
