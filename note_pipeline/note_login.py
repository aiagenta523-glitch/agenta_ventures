#!/usr/bin/env python3
"""
note.com login helper - handles login, session management, and cookie storage.
"""
import json
import time
import subprocess
import sys
import imaplib
import email
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CREDENTIALS_PATH = "/home/agena/claude_org/agenta/credentials/note.json"
GMAIL_READER = "/home/agena/claude_org/agenta/gmail_reader.py"
EMAIL = "ai.agenta523@gmail.com"
PASSWORD = "NoteAI2026!#$"
APP_PASSWORD = "rqby hzqu ilfb lfyy"


def get_gmail_activation_url():
    """Get latest note.com activation URL from Gmail."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, 'FROM "note.com"')
        ids = messages[0].split()
        if not ids:
            return None
        for msg_id in reversed(ids):
            status, data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    urls = re.findall(r'https?://[^\s"<>&]+(?:&amp;[^\s"<>&]+)*', body)
                    activate_urls = [u.replace("&amp;", "&") for u in urls if "activate" in u]
                    if activate_urls:
                        mail.close()
                        mail.logout()
                        return activate_urls[0]
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"[WARN] Gmail error: {e}")
    return None


def login_to_note(context, page) -> bool:
    """Login to note.com and return True if successful."""
    print("[INFO] Navigating to note.com login...")
    page.goto("https://note.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    body = page.locator("body").inner_text()
    if "しばらくたってからもう一度" in body:
        print("[WARN] Login rate limited, waiting...")
        time.sleep(30)
        page.reload()
        time.sleep(3)

    page.fill("#email", EMAIL)
    page.fill("#password", PASSWORD)
    page.keyboard.press("Enter")
    time.sleep(6)

    current_url = page.url
    if "login" in current_url:
        print(f"[WARN] Still on login page after submit. URL: {current_url[:80]}")
        return False

    print(f"[INFO] Login result URL: {current_url[:80]}")
    return True


def get_valid_session(force_refresh: bool = False) -> dict:
    """
    Get a valid note.com session. Uses saved cookies or logs in fresh.
    Returns dict with cookies on success, raises on failure.
    """
    creds_path = Path(CREDENTIALS_PATH)

    # Try saved cookies first
    if not force_refresh and creds_path.exists():
        with open(creds_path) as f:
            creds = json.load(f)

        # Test if cookies are still valid
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            context.add_cookies(creds["cookies"])
            page = context.new_page()

            try:
                user_info = page.evaluate("""
                    async () => {
                        const r = await fetch('/api/v2/current_user', {credentials: 'include'});
                        if (r.ok) return await r.json();
                        return {error: r.status};
                    }
                """)
                if "error" not in user_info or user_info.get("error") != 401:
                    print("[INFO] Saved session is valid")
                    context.close()
                    browser.close()
                    return creds
            except Exception:
                pass

            context.close()
            browser.close()

    # Fresh login
    print("[INFO] Performing fresh login...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )
        page = context.new_page()

        success = login_to_note(context, page)
        if not success:
            browser.close()
            raise Exception("Login failed - possible rate limiting")

        # Handle post-login steps
        current_url = page.url
        body = page.locator("body").inner_text()

        # Handle email verification banner - request resend if needed
        if "認証メールを送信" in body:
            print("[INFO] Email verification needed, requesting resend...")
            resend_btn = page.query_selector("button:has-text('メールを再送信')")
            if resend_btn:
                resend_btn.click()
                time.sleep(15)

                # Get fresh activation URL
                activation_url = get_gmail_activation_url()
                if activation_url:
                    print(f"[INFO] Using activation URL...")
                    page.goto(activation_url, timeout=30000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)

        # Complete note_id setup if needed
        if "signup/note_id" in page.url:
            print("[INFO] Completing note_id setup...")
            current_id = page.evaluate("document.querySelector('#noteID')?.value")
            if current_id:
                page.fill("#nickname", "AIキャリアラボ")
                time.sleep(1)
                btn = page.query_selector("button:has-text('次へ')")
                if btn and not btn.get_attribute("disabled"):
                    btn.click()
                    time.sleep(4)

                    # Handle Twitter linking step
                    skip = page.query_selector("button:has-text('今はしない')")
                    if skip:
                        skip.click()
                        time.sleep(3)

        # Save cookies
        cookies = context.cookies()

        # Get username
        username = "aicareer523"  # Known username
        try:
            page.goto("https://note.com/me", timeout=15000)
            time.sleep(2)
            me_url = page.url
            if "/n/" in me_url:
                username = me_url.split("/n/")[-1].strip("/")
        except Exception:
            pass

        creds = {
            "cookies": cookies,
            "user_info": {
                "username": username,
                "email": EMAIL,
                "password": PASSWORD,
            },
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        with open(CREDENTIALS_PATH, "w") as f:
            json.dump(creds, f, indent=2, ensure_ascii=False)

        print(f"[SUCCESS] Session saved. Username: {username}")

        context.close()
        browser.close()

        return creds


if __name__ == "__main__":
    force = "--force" in sys.argv
    try:
        creds = get_valid_session(force_refresh=force)
        print(f"Session obtained for: {creds['user_info']['username']}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
