# note.com Daily Article Pipeline

AI×キャリアジャンルの有料記事を毎日自動生成・投稿するパイプライン。

## 構成

```
note_pipeline/
├── generate_article.py   # Claude claude-haiku-4-5-20251001で記事生成
├── post_to_note.py       # Playwrightでnote.comに投稿
├── note_login.py         # セッション管理・ログインヘルパー
├── daily_pipeline.py     # メインパイプライン（cron実行）
├── note_auth.py          # 初回アカウントセットアップ
├── requirements.txt      # 依存パッケージ
├── articles/             # 生成済み記事（日付_slug.md）
└── sample_articles/      # サンプル記事
```

## セットアップ

```bash
pip install -r requirements.txt
playwright install chromium
```

## 使い方

### 記事生成のみ（テスト）
```bash
python3 daily_pipeline.py --skip-post
```

### 特定トピックで生成
```bash
python3 daily_pipeline.py --topic "AIを使った転職活動" --skip-post
```

### 完全実行（生成+投稿）
```bash
python3 daily_pipeline.py
```

## cron設定

```cron
# 毎日8時に実行
0 8 * * * /home/agena/miniconda3/bin/python3 /path/to/daily_pipeline.py >> /home/agena/claude_org/ventures/logs/note_cron.log 2>&1
```

## note.comアカウント

- **Username**: aicareer523
- **Display Name**: AIキャリアラボ
- **Email**: ai.agenta523@gmail.com
- **Credentials**: `/home/agena/claude_org/agenta/credentials/note.json`

## 記事設定

- **ジャンル**: AI×キャリア
- **価格帯**: ¥300〜¥500
- **文字数**: 2000〜3000字
- **投稿頻度**: 毎日1本
- **使用モデル**: claude-haiku-4-5-20251001（コスト最小化）

## ブロッカー（2026-05-02現在）

1. **ログインレートリミット**: note.comのログインに一時的なレートリミットがかかっている。
   - 対応: 数時間後に再試行
2. **メール認証**: アカウントは作成済み・認証済み（email_confirmed_flag: true）だが、セッション維持の改善が必要。
   - 対応: note_login.pyで自動再ログイン処理を実装済み
