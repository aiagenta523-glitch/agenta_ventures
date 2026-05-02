#!/usr/bin/env python3
"""
Fix existing note.com articles: add paid zone and set price.
Does NOT re-enter content - opens existing article for editing,
positions cursor at 30% mark, inserts paywall-line, sets price.

Usage:
    python fix_paid_zone.py                          # fix all known articles
    python fix_paid_zone.py https://note.com/...     # fix specific article
"""
import json
import sys
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDENTIALS_PATH = "/home/agena/claude_org/agenta/credentials/note.json"
FIXED_ARTICLES_FILE = Path(__file__).parent / "fixed_articles.json"
LOG_FILE = "/home/agena/claude_org/ventures/logs/note_pipeline.jsonl"

# All published articles (note key → title mapping)
KNOWN_ARTICLES = {
    "n0cc0a04bf3e9": "AI副業で初月10万円｜2026年最新・未経験から稼ぐ実践ロードマップ",
    "n74a20d320628": "ChatGPT・Claude活用で職務経歴書を2倍魅力的にする実戦プロンプト集",
    "na2949ec11041": "ChatGPT時代の必須スキルは「AIとの協働」—エンジニアが今すぐ身につけるべき5つの能力",
    "n9deed9c709b1": "AI会議アシスタントで時間を40%削減！実践的な5つの自動化テクニック",
}

DEFAULT_PRICE = 300


def load_fixed_articles() -> dict:
    if FIXED_ARTICLES_FILE.exists():
        return json.loads(FIXED_ARTICLES_FILE.read_text())
    return {}


def save_fixed_articles(data: dict):
    FIXED_ARTICLES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def log_result(note_key: str, title: str, success: bool, error: str = None):
    import datetime
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": "fix_paid_zone",
        "note_key": note_key,
        "title": title,
        "success": success,
        "error": error,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fix_article(page, note_key: str, title: str, price: int = DEFAULT_PRICE) -> dict:
    """Open article for editing, add paid zone, set price, re-publish."""
    result = {"success": False, "error": None}

    edit_url = f"https://editor.note.com/notes/{note_key}/edit"
    print(f"\n[INFO] Opening edit page: {edit_url}")
    print(f"[INFO] Title: {title}")

    try:
        page.goto(edit_url, timeout=60000)
        # Wait for editor to load
        page.wait_for_selector(".ProseMirror", timeout=30000)
        time.sleep(3)

        page.screenshot(path=f"/tmp/fix_{note_key}_1_loaded.png")

        # Check if paywall-line already exists
        existing_paywall = page.query_selector("paywall-line")
        if existing_paywall:
            print(f"[INFO] Article already has paywall-line, skipping content edit")
            # Still need to check if price is set - proceed to publish
        else:
            # Position cursor: find a good split point (~30% into content)
            # Click at ~30% height of editor
            editor = page.query_selector(".ProseMirror")
            if not editor:
                result["error"] = "Editor not found"
                return result

            # Get all paragraphs
            paragraphs = page.query_selector_all(".ProseMirror > p")
            print(f"[INFO] Paragraphs in editor: {len(paragraphs)}")

            if len(paragraphs) >= 3:
                # Click after 2nd paragraph (free preview = first ~2 paragraphs)
                target_para = paragraphs[1]
                target_para.click()
                page.keyboard.press("End")
                time.sleep(0.3)
            else:
                # Click at end of first available paragraph
                editor.click()
                page.keyboard.press("End")
                time.sleep(0.3)

            # Insert paid zone via menu
            print("[INFO] Inserting paid zone...")
            menu_btn = page.query_selector('button[aria-label="メニューを開く"]')
            if not menu_btn:
                result["error"] = "メニューを開く button not found"
                return result

            menu_btn.click()
            time.sleep(0.8)

            paid_btn = page.query_selector('button:has-text("有料エリア指定")')
            if not paid_btn:
                result["error"] = "有料エリア指定 button not found in menu"
                page.keyboard.press("Escape")
                return result

            paid_btn.click()
            time.sleep(0.8)

            # Verify insertion
            paywall_el = page.query_selector("paywall-line")
            if not paywall_el:
                result["error"] = "paywall-line not found after insertion"
                return result
            print("[INFO] Paid zone inserted successfully")

        page.screenshot(path=f"/tmp/fix_{note_key}_2_paid_inserted.png")

        # Save draft (use JS click to avoid visibility timeout)
        draft_btn = page.query_selector('button:has-text("下書き保存")')
        if draft_btn:
            page.evaluate("(el) => el.click()", draft_btn)
            time.sleep(3)
            print("[INFO] Draft saved")

        # Proceed to publish modal
        publish_btn = page.query_selector('button:has-text("公開に進む")')
        if not publish_btn:
            result["error"] = "公開に進む button not found"
            return result

        page.evaluate("(el) => el.click()", publish_btn)
        time.sleep(5)

        page.screenshot(path=f"/tmp/fix_{note_key}_3_modal.png")

        # Set paid mode
        paid_radio = page.query_selector('input[name="is_paid"][value="paid"]')
        if not paid_radio:
            paid_radio = page.query_selector('input[value="paid"]')

        if paid_radio:
            page.evaluate("(el) => el.click()", paid_radio)
            time.sleep(0.8)
            print("[INFO] Paid radio selected")

            # Set price
            price_input = page.query_selector('input[placeholder="300"], input[type="text"][placeholder]')
            if price_input:
                page.evaluate("(el) => el.click()", price_input)
                price_input.click(click_count=3)
                price_input.fill(str(price))
                time.sleep(0.3)
                print(f"[INFO] Price set to ¥{price}")
            else:
                print("[WARN] Price input not found")
        else:
            print("[WARN] Paid radio button not found in modal")

        page.screenshot(path=f"/tmp/fix_{note_key}_4_price_set.png")

        # Step A: Click '有料エリア設定' to open the paid zone position confirmation modal
        # (This shows a preview of where paywall-line is placed)
        paid_zone_btn = page.query_selector('button:has-text("有料エリア設定")')
        if paid_zone_btn:
            print("[INFO] Clicking 有料エリア設定 to confirm paid zone position...")
            page.evaluate("(el) => el.click()", paid_zone_btn)
            time.sleep(3)
            page.screenshot(path=f"/tmp/fix_{note_key}_5_zone_modal.png")

        # Step B: Click the final publish/update button
        # For new articles: '投稿する', for existing: '更新する'
        final_btn = (
            page.query_selector('button:has-text("更新する")')
            or page.query_selector('button:has-text("投稿する")')
        )
        if not final_btn:
            result["error"] = "No final publish button found (tried 更新する / 投稿する)"
            return result

        btn_text = final_btn.inner_text()
        print(f"[INFO] Clicking final button: '{btn_text}'")
        page.evaluate("(el) => el.click()", final_btn)
        time.sleep(6)

        page.screenshot(path=f"/tmp/fix_{note_key}_6_published.png")
        print(f"[SUCCESS] Article updated: https://note.com/aicareer523/n/{note_key}")
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)[:200]
        try:
            page.screenshot(path=f"/tmp/fix_{note_key}_error.png")
        except Exception:
            pass

    return result


def main():
    with open(CREDENTIALS_PATH) as f:
        creds = json.load(f)
    cookies = creds.get("cookies", [])

    # Determine which articles to fix
    if len(sys.argv) > 1:
        url = sys.argv[1]
        match = re.search(r"/(n[a-f0-9]+)", url)
        if match:
            articles_to_fix = {match.group(1): url}
        else:
            print(f"[ERROR] Could not extract note key from URL: {url}")
            sys.exit(1)
    else:
        articles_to_fix = KNOWN_ARTICLES

    fixed = load_fixed_articles()
    print(f"[INFO] Articles to process: {len(articles_to_fix)}")
    print(f"[INFO] Already fixed: {list(fixed.keys())}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        context.add_cookies(cookies)
        page = context.new_page()

        results = []
        for note_key, title in articles_to_fix.items():
            if note_key in fixed:
                print(f"\n[SKIP] Already fixed: {note_key} ({title[:40]})")
                continue

            result = fix_article(page, note_key, title)
            log_result(note_key, title, result["success"], result.get("error"))

            if result["success"]:
                fixed[note_key] = {"title": title, "price": DEFAULT_PRICE}
                save_fixed_articles(fixed)
                results.append({"note_key": note_key, "status": "fixed"})
            else:
                print(f"[ERROR] Failed to fix {note_key}: {result.get('error')}")
                results.append({"note_key": note_key, "status": "failed", "error": result.get("error")})

            time.sleep(2)  # Brief pause between articles

        # Save updated cookies
        try:
            updated_cookies = context.cookies()
            if updated_cookies:
                creds["cookies"] = updated_cookies
                with open(CREDENTIALS_PATH, "w") as f:
                    json.dump(creds, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        context.close()
        browser.close()

    print("\n=== RESULTS ===")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
