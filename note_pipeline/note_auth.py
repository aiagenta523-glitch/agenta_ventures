#!/usr/bin/env python3
"""
note.com authentication via Playwright (headless)
Attempts Google OAuth login, saves session cookies to credentials file.
"""
import json
import time
import subprocess
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CREDENTIALS_PATH = "/home/agena/claude_org/agenta/credentials/note.json"
GMAIL_READER = "/home/agena/claude_org/agenta/gmail_reader.py"
GOOGLE_EMAIL = "ai.agenta523@gmail.com"
GOOGLE_PASSWORD = "dkeidbryw1837!?4&"


def get_gmail_code(service="note"):
    """Attempt to retrieve verification code from Gmail."""
    try:
        result = subprocess.run(
            ["python3", GMAIL_READER, "--code", service],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"[WARN] gmail_reader failed: {e}")
    return None


def save_credentials(cookies, user_info):
    """Save session cookies and user info to credentials file."""
    data = {
        "cookies": cookies,
        "user_info": user_info,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    Path(CREDENTIALS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Credentials saved to {CREDENTIALS_PATH}")


def attempt_note_login():
    """Main login flow for note.com via Google OAuth."""
    result = {
        "success": False,
        "username": None,
        "error": None,
        "method": None
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("[INFO] Navigating to note.com login page...")
            page.goto("https://note.com/login", wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Take screenshot for debugging
            page.screenshot(path="/tmp/note_login_1.png")
            print(f"[INFO] Current URL: {page.url}")
            print(f"[INFO] Page title: {page.title()}")

            # Look for Google login button
            google_btn = None
            selectors = [
                "text=Googleでログイン",
                "text=Googleでサインイン",
                "[data-social='google']",
                "a[href*='google']",
                "button[class*='google']",
                ".o-loginButtons__google",
                "a[class*='google']"
            ]

            for sel in selectors:
                try:
                    elem = page.query_selector(sel)
                    if elem:
                        google_btn = elem
                        print(f"[INFO] Found Google button with selector: {sel}")
                        break
                except Exception:
                    continue

            if not google_btn:
                # Try checking if already logged in or find email/password form
                print("[WARN] Google button not found, trying email login...")
                page.screenshot(path="/tmp/note_login_no_google.png")

                # Try email-based signup/login
                email_input = page.query_selector("input[type='email'], input[name='email']")
                if email_input:
                    email_input.fill(GOOGLE_EMAIL)
                    page.screenshot(path="/tmp/note_login_email_filled.png")
                    result["error"] = "Email form found but Google OAuth not available"
                else:
                    result["error"] = "Neither Google button nor email form found"
                return result

            # Click Google login
            print("[INFO] Clicking Google login button...")
            google_btn.click()
            time.sleep(3)
            page.screenshot(path="/tmp/note_google_auth_1.png")
            print(f"[INFO] After click URL: {page.url}")

            # Handle Google OAuth popup or redirect
            current_url = page.url
            if "accounts.google.com" in current_url:
                print("[INFO] On Google auth page, entering credentials...")

                # Enter email
                try:
                    page.wait_for_selector("input[type='email']", timeout=10000)
                    page.fill("input[type='email']", GOOGLE_EMAIL)
                    page.screenshot(path="/tmp/note_google_email.png")

                    # Click Next
                    page.click("#identifierNext, [id='identifierNext'], button[jsname='LgbsSe']")
                    time.sleep(2)
                    page.screenshot(path="/tmp/note_google_next1.png")

                    # Enter password
                    page.wait_for_selector("input[type='password']", timeout=10000)
                    page.fill("input[type='password']", GOOGLE_PASSWORD)
                    page.screenshot(path="/tmp/note_google_password.png")

                    # Click Next
                    page.click("#passwordNext, [id='passwordNext'], button[jsname='LgbsSe']")
                    time.sleep(4)
                    page.screenshot(path="/tmp/note_google_after_password.png")
                    print(f"[INFO] After password URL: {page.url}")

                    # Check for 2FA/verification
                    if "signin/challenge" in page.url or "accounts.google.com" in page.url:
                        print("[INFO] Possible 2FA challenge detected, waiting for email code...")
                        time.sleep(5)

                        # Try to get code from Gmail
                        code = get_gmail_code("google")
                        if code:
                            print(f"[INFO] Got code: {code}")
                            # Look for code input
                            code_input = page.query_selector("input[type='tel'], input[name='code'], input[aria-label*='code'], input[aria-label*='Code']")
                            if code_input:
                                code_input.fill(code)
                                page.click("button[jsname='LgbsSe'], #submit")
                                time.sleep(3)
                        else:
                            print("[WARN] Could not retrieve verification code automatically")
                            result["error"] = "2FA required but could not auto-retrieve code"
                            page.screenshot(path="/tmp/note_google_2fa.png")
                            return result

                except PlaywrightTimeoutError as e:
                    print(f"[ERROR] Timeout during Google auth: {e}")
                    page.screenshot(path="/tmp/note_google_timeout.png")
                    result["error"] = f"Google auth timeout: {str(e)}"
                    return result

            # Wait to be redirected back to note.com
            print("[INFO] Waiting for redirect back to note.com...")
            try:
                page.wait_for_url("*note.com*", timeout=15000)
            except PlaywrightTimeoutError:
                print(f"[WARN] Timeout waiting for note.com redirect. Current URL: {page.url}")

            time.sleep(3)
            page.screenshot(path="/tmp/note_after_login.png")
            current_url = page.url
            print(f"[INFO] Final URL: {current_url}")

            # Check if login succeeded
            if "note.com" in current_url and "login" not in current_url and "signup" not in current_url:
                print("[INFO] Login appears successful!")

                # Get user info
                cookies = context.cookies()
                username = None

                # Try to extract username from URL or page
                if "/n/" in current_url:
                    username = current_url.split("/n/")[-1].strip("/")
                else:
                    # Try to find profile link
                    try:
                        profile_link = page.query_selector("a[href*='/n/']")
                        if profile_link:
                            href = profile_link.get_attribute("href")
                            username = href.split("/n/")[-1].strip("/")
                    except Exception:
                        pass

                    # Navigate to profile to get username
                    if not username:
                        try:
                            page.goto("https://note.com/me", wait_until="networkidle", timeout=15000)
                            time.sleep(2)
                            current_url = page.url
                            if "/n/" in current_url:
                                username = current_url.split("/n/")[-1].strip("/")
                        except Exception:
                            pass

                print(f"[INFO] Username: {username}")
                user_info = {"username": username, "email": GOOGLE_EMAIL}
                save_credentials(cookies, user_info)

                result["success"] = True
                result["username"] = username
                result["method"] = "google_oauth"
            else:
                print(f"[WARN] Login may have failed. URL: {current_url}")
                page.screenshot(path="/tmp/note_login_failed.png")

                # Check page content for error messages
                content = page.content()
                if "error" in content.lower() or "エラー" in content:
                    result["error"] = "Login failed - error detected on page"
                else:
                    result["error"] = f"Unexpected URL after login: {current_url}"

        except Exception as e:
            print(f"[ERROR] Exception during login: {e}")
            result["error"] = str(e)
            try:
                page.screenshot(path="/tmp/note_exception.png")
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    return result


if __name__ == "__main__":
    print("=== note.com Authentication Setup ===")
    result = attempt_note_login()
    print(f"\n=== Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print(f"\n[SUCCESS] Logged in as: {result['username']}")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Error: {result['error']}")
        sys.exit(1)
