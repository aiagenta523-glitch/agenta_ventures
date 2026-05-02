#!/usr/bin/env python3
"""
Post articles to note.com using Playwright.
Handles authentication, article creation, paid zone settings, and publishing.
"""
import json
import time
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CREDENTIALS_PATH = "/home/agena/claude_org/agenta/credentials/note.json"
LOG_FILE = "/home/agena/claude_org/ventures/logs/note_pipeline.jsonl"
EMAIL = "ai.agenta523@gmail.com"
PASSWORD = "NoteAI2026!#$"


def load_article_from_file(filepath: str) -> dict:
    """Load article data from markdown file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Article file not found: {filepath}")

    content = path.read_text(encoding="utf-8")

    # Parse front matter
    article = {"filepath": str(filepath), "raw_content": content}

    if content.startswith("---"):
        # Extract YAML front matter
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
                        # Parse list like [AI, キャリア, ...]
                        tags_str = value.strip("[]")
                        article[key] = [t.strip() for t in tags_str.split(",") if t.strip()]
                    else:
                        article[key] = value

            # Get body (everything after front matter)
            body_content = content[end + 3:].strip()
            # Extract title from first h1
            title_match = re.search(r'^# (.+)$', body_content, re.MULTILINE)
            if title_match and not article.get("title"):
                article["title"] = title_match.group(1)

            article["body_content"] = body_content

    return article


def login_with_session(context, email: str, password: str) -> bool:
    """Login to note.com and return success."""
    page = context.new_page()

    page.goto("https://note.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    body = page.locator("body").inner_text()
    if "しばらくたってからもう一度" in body:
        print("[WARN] Rate limited on login")
        page.close()
        return False

    page.fill("#email", email)
    page.fill("#password", password)
    page.keyboard.press("Enter")
    time.sleep(6)

    current_url = page.url
    page.close()

    if "login" in current_url:
        print(f"[WARN] Login failed, still on login page")
        return False

    print(f"[INFO] Login successful: {current_url[:80]}")
    return True


def post_article(article: dict) -> dict:
    """
    Post an article to note.com.
    Returns dict with post_url and status.
    """
    result = {
        "success": False,
        "post_url": None,
        "error": None,
        "article_title": article.get("title", ""),
    }

    # Load saved credentials
    creds_path = Path(CREDENTIALS_PATH)
    cookies = []

    if creds_path.exists():
        with open(creds_path) as f:
            creds = json.load(f)
        cookies = creds.get("cookies", [])

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )

        # Set saved cookies
        if cookies:
            context.add_cookies(cookies)

        page = context.new_page()

        try:
            # Check if session is valid by visiting home
            page.goto("https://note.com/", timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Check login status
            user_check = page.evaluate("""
                async () => {
                    try {
                        const r = await fetch('/api/v2/current_user', {credentials: 'include'});
                        if (r.ok) {
                            const data = await r.json();
                            return {ok: true, urlname: data.data?.urlname};
                        }
                        return {ok: false, status: r.status};
                    } catch(e) {
                        return {ok: false, error: String(e)};
                    }
                }
            """)

            print(f"[INFO] User check: {user_check}")

            if not user_check.get("ok"):
                print("[INFO] Session expired, logging in fresh...")
                success = login_with_session(context, EMAIL, PASSWORD)
                if not success:
                    result["error"] = "Login failed"
                    return result

            # Navigate to note editor
            print("[INFO] Opening note editor...")
            page.goto("https://note.com/notes/new", timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(5)

            editor_url = page.url
            print(f"[INFO] Editor URL: {editor_url[:100]}")

            if "login" in editor_url:
                result["error"] = "Redirected to login - session invalid"
                return result

            # Wait for editor to load
            page.wait_for_selector("[contenteditable]", timeout=20000)
            time.sleep(3)

            # Get title field
            title = article.get("title", "AIキャリアラボ記事")
            body_content = article.get("body_content", "")
            if not body_content:
                body_content = article.get("raw_content", "")

            # Enter title
            print(f"[INFO] Entering title: {title[:50]}")
            title_area = page.query_selector(
                "input[placeholder*='タイトル'], "
                "[data-testid='title'], "
                ".o-noteEditor__title input, "
                "input.note-title, "
                ".title-input"
            )

            if not title_area:
                # Try first contenteditable
                editables = page.query_selector_all("[contenteditable]")
                if editables:
                    title_area = editables[0]
                    title_area.click()
                    title_area.fill(title)

            if title_area:
                title_area.click()
                title_area.fill(title)
                time.sleep(0.5)
            else:
                print("[WARN] Could not find title input")

            page.keyboard.press("Tab")
            time.sleep(0.5)

            # Enter body content
            print("[INFO] Entering body content...")
            body_area = page.query_selector(
                ".ProseMirror, "
                "[data-testid='editor-body'], "
                ".note-body [contenteditable], "
                ".o-noteEditor__body [contenteditable]"
            )

            if not body_area:
                editables = page.query_selector_all("[contenteditable]")
                if len(editables) >= 2:
                    body_area = editables[1]

            if body_area:
                body_area.click()
                # Use keyboard shortcut to select all and replace
                page.keyboard.press("Control+a")
                time.sleep(0.3)

                # Type the content (simplified - remove markdown formatting for basic editor)
                # Note editor may not support full markdown
                clean_body = re.sub(r"^#{1,6} ", "", body_content, flags=re.MULTILINE)
                clean_body = re.sub(r"\*\*(.+?)\*\*", r"\1", clean_body)
                clean_body = re.sub(r"\*(.+?)\*", r"\1", clean_body)

                body_area.type(clean_body[:3000], delay=10)
                time.sleep(2)
            else:
                print("[WARN] Could not find body editor")

            page.screenshot(path="/tmp/note_editor_filled.png")

            # Set paid content settings
            price = article.get("price", 300)
            print(f"[INFO] Setting price to ¥{price}...")

            # Look for paid settings button
            paid_btns = page.query_selector_all(
                "button[class*='paid'], "
                "button[aria-label*='有料'], "
                ".o-noteEditor__payButton, "
                "button:has-text('有料')"
            )

            print(f"[INFO] Found {len(paid_btns)} potential paid buttons")

            # Save as draft first
            print("[INFO] Saving as draft...")
            save_draft_btn = page.query_selector(
                "button:has-text('下書き保存'), "
                "button[aria-label='下書き保存']"
            )

            if save_draft_btn:
                save_draft_btn.click()
                time.sleep(3)
                print("[INFO] Draft saved")

            # Publish
            print("[INFO] Looking for publish button...")
            publish_btn = page.query_selector(
                "button:has-text('公開する'), "
                "button:has-text('投稿する'), "
                "button[aria-label='投稿する']"
            )

            if publish_btn:
                publish_btn.click()
                time.sleep(3)
                page.screenshot(path="/tmp/note_publish_modal.png")

                # Look for price setting in publish modal
                price_input = page.query_selector("input[placeholder*='価格'], input[type='number']")
                if price_input:
                    price_input.fill(str(price))
                    time.sleep(0.5)

                # Find confirm publish button
                confirm_btn = page.query_selector(
                    "button:has-text('公開する'), "
                    "button:has-text('この設定で公開する')"
                )
                if confirm_btn:
                    confirm_btn.click()
                    time.sleep(5)

                    post_url = page.url
                    print(f"[SUCCESS] Published! URL: {post_url[:100]}")
                    result["success"] = True
                    result["post_url"] = post_url
                else:
                    result["error"] = "Could not find confirm publish button"
            else:
                # Try to find the publish flow via settings
                all_buttons = page.query_selector_all("button")
                btn_texts = [b.inner_text().strip() for b in all_buttons if b.inner_text().strip()]
                print(f"[DEBUG] Available buttons: {btn_texts[:20]}")
                result["error"] = "Could not find publish button"

        except PlaywrightTimeoutError as e:
            result["error"] = f"Timeout: {str(e)[:100]}"
            try:
                page.screenshot(path="/tmp/note_post_timeout.png")
            except Exception:
                pass

        except Exception as e:
            result["error"] = f"Exception: {str(e)[:100]}"
            try:
                page.screenshot(path="/tmp/note_post_error.png")
            except Exception:
                pass

        finally:
            # Save updated cookies
            try:
                updated_cookies = context.cookies()
                if updated_cookies and creds_path.exists():
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

    print(f"\n[RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["success"] else 1)
