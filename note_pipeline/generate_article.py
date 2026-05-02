#!/usr/bin/env python3
"""
Article generator for note.com - AI x Career topic.
Uses Claude claude-haiku-4-5-20251001 to generate articles based on trending topics.
"""
import os
import json
import sys
import re
from datetime import datetime
from pathlib import Path
import anthropic

# Configuration
ARTICLES_DIR = Path(__file__).parent / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4096

ARTICLE_TOPICS = [
    "AIで職務経歴書を改善する方法",
    "ChatGPTを使った転職活動",
    "AI時代に求められるスキル",
    "AIを活用したキャリアアップ",
    "機械学習エンジニアの転職市場",
    "AI面接対策と傾向分析",
    "GitHub Copilot活用によるエンジニアの生産性向上",
    "AIプロンプトエンジニアリングの副業",
    "2026年のITエンジニア採用動向",
    "AIツールで仕事を自動化する方法",
]


def get_daily_topic() -> str:
    """Get a topic for today's article based on the date."""
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday
    return ARTICLE_TOPICS[day_of_year % len(ARTICLE_TOPICS)]


def generate_article_with_claude(topic: str, custom_prompt: str = None) -> dict:
    """Generate an article using Claude claude-haiku-4-5-20251001."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    if custom_prompt:
        prompt = custom_prompt
    else:
        today = datetime.now().strftime("%Y年%m月%d日")
        prompt = f"""
あなたは「AIキャリアラボ」というnoteクリエイターです。AI×キャリアをテーマに、実践的で価値のある有料記事を書いています。

以下のテーマで有料記事を書いてください：
テーマ：{topic}

要件：
- タイトル：SEOを意識した魅力的なタイトル（30-50文字程度）
- 本文：2000〜3000文字
- 構成：
  1. リード文（200字程度）：読者の課題共感と記事の価値提示
  2. 本論（1500-2000字）：具体的な手順・ノウハウを3〜5つのセクションで
  3. まとめ（200字程度）：行動を促すクロージング
- 読者層：転職・キャリアアップを考えているITエンジニア・ビジネスパーソン
- 価格設定：¥300-500（有料ゾーンの設定も含める）
- 今日の日付：{today}

必ず以下のフォーマットで出力してください：

---TITLE---
（タイトル）

---PRICE---
（300, 400, または 500）

---LEAD---
（リード文200字程度）

---BODY---
（本文2000-3000字 - Markdown形式）

---PAID_ZONE---
（この部分は有料ゾーンに入れる段落のタイトルまたは開始テキスト）

---SUMMARY---
（まとめ200字程度）

---TAGS---
（タグ3-5個をカンマ区切りで。例：AI,転職,キャリア,ChatGPT,副業）
---
"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_content = message.content[0].text

    # Parse the structured output
    article = parse_article_output(raw_content, topic)
    article["raw_content"] = raw_content
    article["model"] = MODEL
    article["generated_at"] = datetime.now().isoformat()
    article["topic"] = topic

    return article


def parse_article_output(raw: str, topic: str) -> dict:
    """Parse the structured article output from Claude."""
    sections = {
        "title": "",
        "price": 300,
        "lead": "",
        "body": "",
        "paid_zone_marker": "",
        "summary": "",
        "tags": [],
    }

    def extract_section(raw, start_marker, end_marker=None):
        start_idx = raw.find(start_marker)
        if start_idx == -1:
            return ""
        start_idx += len(start_marker)
        if end_marker:
            end_idx = raw.find(end_marker, start_idx)
            if end_idx == -1:
                return raw[start_idx:].strip()
            return raw[start_idx:end_idx].strip()
        return raw[start_idx:].strip()

    sections["title"] = extract_section(raw, "---TITLE---", "---PRICE---")
    if not sections["title"]:
        sections["title"] = topic

    price_str = extract_section(raw, "---PRICE---", "---LEAD---")
    try:
        price_val = int(re.search(r"\d+", price_str).group())
        sections["price"] = price_val if price_val in [300, 400, 500] else 300
    except Exception:
        sections["price"] = 300

    sections["lead"] = extract_section(raw, "---LEAD---", "---BODY---")
    sections["body"] = extract_section(raw, "---BODY---", "---PAID_ZONE---")
    sections["paid_zone_marker"] = extract_section(raw, "---PAID_ZONE---", "---SUMMARY---")
    sections["summary"] = extract_section(raw, "---SUMMARY---", "---TAGS---")

    tags_str = extract_section(raw, "---TAGS---")
    if tags_str:
        # Remove trailing --- and parse
        tags_str = tags_str.split("---")[0].strip()
        sections["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    return sections


def save_article(article: dict, date_str: str = None) -> Path:
    """Save article to markdown file."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Create slug from title
    title = article.get("title", "untitled")
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s]+", "-", slug).strip("-")[:50]
    if not slug:
        slug = "article"

    filename = f"{date_str}_{slug}.md"
    filepath = ARTICLES_DIR / filename

    # Build markdown content
    content = f"""---
title: "{article['title']}"
date: {date_str}
price: {article['price']}
tags: [{', '.join(article.get('tags', []))}]
model: {article.get('model', MODEL)}
generated_at: {article.get('generated_at', '')}
topic: {article.get('topic', '')}
---

# {article['title']}

{article.get('lead', '')}

---

{article.get('body', '')}

---

{article.get('summary', '')}
"""

    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Article saved: {filepath}")
    return filepath


def generate_and_save(topic: str = None) -> dict:
    """Main function: generate and save an article."""
    if not topic:
        topic = get_daily_topic()

    print(f"[INFO] Generating article on topic: {topic}")
    article = generate_article_with_claude(topic)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = save_article(article, date_str)

    return {
        "topic": topic,
        "title": article["title"],
        "price": article["price"],
        "tags": article.get("tags", []),
        "filepath": str(filepath),
        "date": date_str,
    }


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_and_save(topic)
    print(json.dumps(result, ensure_ascii=False, indent=2))
