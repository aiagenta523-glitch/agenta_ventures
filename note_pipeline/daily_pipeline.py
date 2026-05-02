#!/usr/bin/env python3
"""
Daily note.com article pipeline.
Generates an article and posts it to note.com automatically.
Run via cron: 0 8 * * * python3 /path/to/daily_pipeline.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

LOG_FILE = "/home/agena/claude_org/ventures/logs/note_pipeline.jsonl"
PIPELINE_DIR = Path(__file__).parent


def log_event(event: dict):
    """Append event to pipeline log."""
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event["timestamp"] = datetime.now().isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_pipeline(topic: str = None, skip_post: bool = False) -> dict:
    """
    Run the full pipeline: generate article -> post to note.com.

    Args:
        topic: Optional specific topic. If None, uses daily topic.
        skip_post: If True, only generate (don't post). Useful for testing.

    Returns:
        dict with pipeline results.
    """
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generate_success": False,
        "post_success": False,
        "article_path": None,
        "post_url": None,
        "error": None,
    }

    log_event({"action": "pipeline_start", "topic": topic or "daily"})

    # Step 1: Generate article
    print(f"\n{'='*60}")
    print(f"STEP 1: Generating article ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*60}")

    try:
        from generate_article import generate_and_save

        gen_result = generate_and_save(topic)
        result["generate_success"] = True
        result["article_path"] = gen_result["filepath"]
        result["article_title"] = gen_result["title"]
        result["article_price"] = gen_result["price"]

        print(f"[SUCCESS] Article generated: {gen_result['title']}")
        print(f"[INFO] File: {gen_result['filepath']}")
        print(f"[INFO] Price: ¥{gen_result['price']}")

        log_event({
            "action": "article_generated",
            "title": gen_result["title"],
            "filepath": gen_result["filepath"],
            "price": gen_result["price"],
        })

    except Exception as e:
        result["error"] = f"Generation failed: {str(e)}"
        print(f"[ERROR] Article generation failed: {e}")
        log_event({"action": "generate_failed", "error": str(e)})
        return result

    if skip_post:
        print("\n[INFO] Skipping post (skip_post=True)")
        log_event({"action": "pipeline_complete", "status": "generated_only"})
        return result

    # Step 2: Post to note.com
    print(f"\n{'='*60}")
    print(f"STEP 2: Posting to note.com ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*60}")

    try:
        from post_to_note import post_article, load_article_from_file, log_result

        article = load_article_from_file(result["article_path"])
        post_result = post_article(article)

        log_result(post_result, article)

        if post_result["success"]:
            result["post_success"] = True
            result["post_url"] = post_result["post_url"]
            print(f"[SUCCESS] Article posted: {post_result['post_url']}")
            log_event({
                "action": "post_success",
                "post_url": post_result["post_url"],
                "title": result.get("article_title", ""),
            })
        else:
            result["error"] = f"Post failed: {post_result.get('error')}"
            print(f"[ERROR] Post failed: {post_result.get('error')}")
            log_event({
                "action": "post_failed",
                "error": post_result.get("error"),
                "title": result.get("article_title", ""),
            })

    except Exception as e:
        result["error"] = f"Post exception: {str(e)}"
        print(f"[ERROR] Post exception: {e}")
        log_event({"action": "post_exception", "error": str(e)})

    # Final log
    status = "complete" if result["post_success"] else "partial" if result["generate_success"] else "failed"
    log_event({"action": "pipeline_complete", "status": status, "result": result})

    return result


def print_summary(result: dict):
    """Print pipeline execution summary."""
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"Date:            {result['date']}")
    print(f"Generate:        {'SUCCESS' if result['generate_success'] else 'FAILED'}")
    print(f"Post:            {'SUCCESS' if result['post_success'] else 'FAILED'}")
    if result.get("article_title"):
        print(f"Article title:   {result['article_title']}")
    if result.get("article_price"):
        print(f"Price:           ¥{result['article_price']}")
    if result.get("article_path"):
        print(f"Article file:    {result['article_path']}")
    if result.get("post_url"):
        print(f"Post URL:        {result['post_url']}")
    if result.get("error"):
        print(f"Error:           {result['error']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="note.com daily article pipeline")
    parser.add_argument("--topic", "-t", help="Article topic (default: auto-select)")
    parser.add_argument("--skip-post", "-s", action="store_true",
                        help="Only generate article, don't post")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (generate only)")
    args = parser.parse_args()

    skip_post = args.skip_post or args.test

    print(f"\nnote.com Daily Article Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.topic:
        print(f"Topic: {args.topic}")
    if skip_post:
        print("Mode: Generate only (no posting)")

    result = run_pipeline(topic=args.topic, skip_post=skip_post)
    print_summary(result)

    sys.exit(0 if (result["generate_success"]) else 1)
