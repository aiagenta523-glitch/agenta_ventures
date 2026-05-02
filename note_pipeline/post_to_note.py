#!/usr/bin/env python3
"""
Post articles to note.com using Playwright.
Uses saved session cookies (no headless login needed).
Handles article creation and publishing.

FIXES (2026-05-02):
- Use saved session cookies directly instead of headless login
- Navigate to editor.note.com/new directly
- Use wait_for_selector instead of networkidle+sleep
- Correct selectors: textarea[placeholder="記事タイトル"] and .ProseMirror
"""
import json
import time
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CREDENTIALS_PATH = "/home/agena/claude_org/agenta/credentials/note.json"
LOG_FILE = "/home/agena/claude_org/ventures/logs/note_pipeline.jsonl"


def load_article_from_file(filepath: str) -> dict:
    """Load article data from markdown file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Article file not found: {filepath}")

    content = path.read_text(encoding="utf-8")
    article = {"filepath": str(filepath), "raw_content": content}

    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            front_matter = content[3:end].strip()
            for line in front_matter.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"')
                    if key == "price":
                        try:
                            article[key] = int(value)
                        except ValueError:
                            article[key] = 300
                    elif key == "tags":
                        tags_str = value.strip("[]")
                        article[key] = [t.strip() for t in tags_str.split(",") if t.strip()]
                    else:
                        article[key] = value

            body_content = content[end + 3:].strip()
            title_match = re.search(r"^# (.+)$", body_content, re.MULTILINE)
            if title_match and not article.get("title"):
                article["title"] = title_match.group(1)
            article["body_content"] = body_content

    return article


def _insert_paid_zone(page) -> bool:
    """
    Insert note.com's paid zone separator into the ProseMirror editor.
    Tries multiple approaches; returns True on success.
    """
    try:
        # Approach 1: Press Enter to ensure we're on a new line, then find + button
        page.keyboard.press("End")
        page.keyboard.press("Enter")
        time.sleep(0.5)

        # Try clicking the "+" add-block button that appears on empty lines
        add_btn_selectors = [
            'button[aria-label="ブロックを追加"]',
            '.addButton',
            '[data-testid="add-block-button"]',
            'button.add-block',
        ]
        add_btn = None
        for sel in add_btn_selectors:
            add_btn = page.query_selector(sel)
            if add_btn:
                break

        if add_btn:
            add_btn.click()
            time.sleep(0.5)
            # Click "有料ライン" in the popup menu
            paid_line_btn = page.query_selector(
                'button:has-text("有料ライン"), [data-type="paid"], [aria-label="有料ライン"]'
            )
            if paid_line_btn:
                paid_line_btn.click()
                time.sleep(0.5)
                print("[INFO] Paid zone inserted via + button")
                return True

        # Approach 2: Try "/" command (slash command menu)
        body_area = page.query_selector(".ProseMirror")
        if body_area:
            body_area.click()
            page.keyboard.press("End")
            page.keyboard.press("Enter")
            page.keyboard.type("/有料")
            time.sleep(0.8)
            paid_option = page.query_selector(
                'button:has-text("有料ライン"), [data-type="paid-line"]'
            )
            if paid_option:
                paid_option.click()
                time.sleep(0.5)
                print("[INFO] Paid zone inserted via slash command")
                return True
            else:
                # Clear the typed text if no option appeared
                page.keyboard.press("Escape")
                for _ in range(4):
                    page.keyboard.press("Backspace")

    except Exception as e:
        print(f"[WARN] Paid zone insertion error: {e}")

    return False


def post_article(article: dict) -> dict:
    """
    Post an article to note.com using saved session cookies.
    Returns dict with post_url and status.
    """
    result = {
        "success": False,
        "post_url": None,
        "error": None,
        "article_title": article.get("title", ""),
    }

    creds_path = Path(CREDENTIALS_PATH)
    if not creds_path.exists():
        result["error"] = "No saved credentials found"
        return result

    with open(creds_path) as f:
        creds = json.load(f)

    cookies = creds.get("cookies", [])
    if not cookies:
        result["error"] = "No saved cookies"
        return result

    title = article.get("title", "AIキャリアラボ記事")
    body_content = article.get("body_content", article.get("raw_content", ""))
    price = article.get("price", 300)
    tags = article.get("tags", [])

    # NOTE: Paid content requires owner identity registration (本人情報の入力).
    # Owner has completed registration (2026-05-03). Paid mode is now enabled.
    # Articles with price > 0 and <!-- paid_zone --> marker will be published as paid.
    paid_zone_split = "<!-- paid_zone -->"
    has_paid_zone = paid_zone_split in body_content
    if has_paid_zone:
        free_body, paid_body = body_content.split(paid_zone_split, 1)
    else:
        free_body = body_content
        paid_body = ""

    def clean_markdown(text):
        text = re.sub(r"^#{1,6} +", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"^---$", "", text, flags=re.MULTILINE)
        return text.strip()

    # Combine full article content (free + paid) for free publishing
    full_body = free_body + ("\n\n" + paid_body if paid_body.strip() else "")
    clean_full_body = clean_markdown(full_body)[:3500]
    # Keep for future paid mode use
    clean_free_body = clean_markdown(free_body)[:2000]
    clean_paid_body = clean_markdown(paid_body)[:1500] if paid_body else ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            # Open editor
            print("[INFO] Opening note editor...")
            page.goto("https://editor.note.com/new", timeout=60000)
            page.wait_for_selector('textarea[placeholder="記事タイトル"]', timeout=20000)
            time.sleep(2)

            # Enter title
            print(f"[INFO] Entering title: {title[:50]}")
            title_area = page.query_selector('textarea[placeholder="記事タイトル"]')
            title_area.click()
            title_area.fill(title)
            time.sleep(0.5)

            # Enter body content via JS execCommand
            print("[INFO] Entering body content...")
            body_area = page.query_selector(".ProseMirror")
            paid_zone_inserted = False
            if body_area:
                body_area.click()
                time.sleep(0.3)

                if price > 0 and clean_paid_body:
                    # Insert free preview, then paid zone separator, then paid content
                    print(f"[INFO] Inserting free preview ({len(clean_free_body)} chars)...")
                    page.evaluate(
                        "(text) => { const el = document.querySelector('.ProseMirror'); el.focus(); document.execCommand('insertText', false, text); }",
                        clean_free_body,
                    )
                    time.sleep(1.0)
                    paid_zone_inserted = _insert_paid_zone(page)
                    if paid_zone_inserted:
                        print(f"[INFO] Inserting paid content ({len(clean_paid_body)} chars)...")
                        body_area.click()
                        page.keyboard.press("End")
                        time.sleep(0.3)
                        page.evaluate(
                            "(text) => { const el = document.querySelector('.ProseMirror'); el.focus(); document.execCommand('insertText', false, text); }",
                            "\n" + clean_paid_body,
                        )
                    else:
                        print("[WARN] Paid zone insertion failed, appending paid content as plain text")
                        page.evaluate(
                            "(text) => { const el = document.querySelector('.ProseMirror'); el.focus(); document.execCommand('insertText', false, text); }",
                            "\n\n" + clean_paid_body,
                        )
                else:
                    print("[INFO] Publishing as free article")
                    page.evaluate(
                        "(text) => { const el = document.querySelector('.ProseMirror'); el.focus(); document.execCommand('insertText', false, text); }",
                        clean_full_body,
                    )
                time.sleep(1.5)
            else:
                print("[WARN] Could not find body editor (.ProseMirror)")

            page.screenshot(path="/tmp/note_editor_filled.png")

            # Save as draft
            print("[INFO] Saving draft...")
            draft_btn = page.query_selector('button:has-text("下書き保存")')
            if draft_btn:
                draft_btn.click()
                time.sleep(3)
                print("[INFO] Draft saved")

            # Proceed to publish (use JS click to avoid visibility/stability timeout)
            page.screenshot(path="/tmp/note_before_publish.png")
            publish_btn = page.query_selector('button:has-text("公開に進む")')
            if not publish_btn:
                result["error"] = "Could not find 公開に進む button"
                return result

            page.evaluate("(el) => el.click()", publish_btn)
            time.sleep(5)

            note_key = None
            current_url = page.url
            key_match = re.search(r"/notes/(n[a-f0-9]+)/publish", current_url)
            if key_match:
                note_key = key_match.group(1)
                print(f"[INFO] Note key: {note_key}")

            # Add hashtags
            if tags:
                hashtag_input = page.query_selector('input[placeholder="ハッシュタグを追加する"]')
                if hashtag_input:
                    for tag in tags[:5]:
                        hashtag_input.click()
                        hashtag_input.fill(tag)
                        page.keyboard.press("Enter")
                        time.sleep(0.8)
                    print(f"[INFO] Added {len(tags[:5])} hashtags")

            # Set price in publish modal if paid zone was inserted
            if paid_zone_inserted and price > 0:
                print(f"[INFO] Setting article price to ¥{price}...")
                paid_selectors = [
                    'input[value="paid"]',
                    'label:has-text("有料")',
                    'button:has-text("有料")',
                    '[data-value="paid"]',
                ]
                for sel in paid_selectors:
                    paid_opt = page.query_selector(sel)
                    if paid_opt:
                        paid_opt.click()
                        time.sleep(0.8)
                        print(f"[INFO] Clicked paid option: {sel}")
                        break
                price_input = page.query_selector(
                    'input[type="number"][min], input[placeholder*="価格"], input[name="price"]'
                )
                if price_input:
                    price_input.click()
                    price_input.fill(str(price))
                    time.sleep(0.3)
                    print(f"[INFO] Price set to ¥{price}")
                else:
                    print("[WARN] Could not find price input field")
            else:
                print("[INFO] Publishing as free article")

            page.screenshot(path="/tmp/note_publish_modal.png")

            # Click 投稿する (JS click to avoid visibility/stability timeout)
            print("[INFO] Publishing...")
            final_publish_btn = page.query_selector('button:has-text("投稿する")')
            if not final_publish_btn:
                result["error"] = "Could not find 投稿する button"
                return result

            page.evaluate("(el) => el.click()", final_publish_btn)
            time.sleep(6)

            page.screenshot(path="/tmp/note_published.png")

            # Build the public URL if we have the note key
            if note_key:
                public_url = f"https://note.com/aicareer523/n/{note_key}"
                result["success"] = True
                result["post_url"] = public_url
                print(f"[SUCCESS] Published: {public_url}")
            else:
                # Fallback: check URL for note key
                final_url = page.url
                key_match2 = re.search(r"/(n[a-f0-9]+)", final_url)
                if key_match2:
                    note_key2 = key_match2.group(1)
                    public_url = f"https://note.com/aicareer523/n/{note_key2}"
                    result["success"] = True
                    result["post_url"] = public_url
                    print(f"[SUCCESS] Published: {public_url}")
                else:
                    result["error"] = f"Could not determine note URL. Final URL: {final_url[:100]}"

        except PlaywrightTimeoutError as e:
            result["error"] = f"Timeout: {str(e)[:150]}"
            try:
                page.screenshot(path="/tmp/note_post_timeout.png")
            except Exception:
                pass
        except Exception as e:
            result["error"] = f"Exception: {str(e)[:150]}"
            try:
                page.screenshot(path="/tmp/note_post_error.png")
            except Exception:
                pass
        finally:
            # Save updated cookies
            try:
                updated_cookies = context.cookies()
                if updated_cookies:
                    with open(creds_path) as f:
                        creds = json.load(f)
                    creds["cookies"] = updated_cookies
                    with open(creds_path, "w") as f:
                        json.dump(creds, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            context.close()
            browser.close()

    return result


def log_result(result: dict, article_info: dict):
    """Log posting result to jsonl file."""
    import datetime
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": "post_to_note",
        "success": result.get("success"),
        "post_url": result.get("post_url"),
        "error": result.get("error"),
        "title": article_info.get("title", ""),
        "price": article_info.get("price", 0),
        "filepath": article_info.get("filepath", ""),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[INFO] Result logged to {LOG_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: post_to_note.py <article_filepath>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"[INFO] Posting article: {filepath}")

    article = load_article_from_file(filepath)
    print(f"[INFO] Title: {article.get('title', '?')}")
    print(f"[INFO] Price: ¥{article.get('price', 300)}")

    result = post_article(article)
    log_result(result, article)

    print("\n[RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["success"] else 1)
