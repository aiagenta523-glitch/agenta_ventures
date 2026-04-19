# CareerAI デプロイ手順（Streamlit Cloud）

## 前提条件

- GitHubアカウント（リポジトリ: `aiagenta523-glitch/agenta_ventures`）
- Anthropic APIキー（`ANTHROPIC_API_KEY`）
- Gumroad APIアクセストークン（`GUMROAD_ACCESS_TOKEN`）

## ステップ1: Streamlit Cloud アカウント作成

1. [https://share.streamlit.io](https://share.streamlit.io) にアクセス
2. 「Sign in with GitHub」をクリック
3. GitHubアカウント（`aiagenta523-glitch`）でログイン
4. Streamlit Cloudへのリポジトリアクセスを承認

## ステップ2: アプリのデプロイ

1. Streamlit Cloud ダッシュボードで「**New app**」をクリック

2. 以下を設定:
   ```
   Repository:  aiagenta523-glitch/agenta_ventures
   Branch:      main
   Main file:   app.py
   ```

3. 「**Advanced settings**」を展開

4. 「**Secrets**」に以下を入力:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-xxxx..."
   GUMROAD_ACCESS_TOKEN = "C1iVMaAFp7nJ9DnDFMJkHHVDZ8c0jppWjmC_piDvZpI"
   ```

5. 「**Deploy!**」をクリック

## ステップ3: デプロイ確認

デプロイには通常2〜5分かかります。

完了すると以下のURLが発行されます:
```
https://aiagenta523-glitch-agenta-ventures-app-XXXXX.streamlit.app
```

動作確認:
- [ ] アプリが表示されること
- [ ] チャットが動作すること（Claude APIが応答すること）
- [ ] ライセンスキー認証が動作すること
- [ ] 無料版の10回制限が動作すること

## ステップ4: Gumroad商品の公開

StreamlitのURLが確定したら、Gumroad商品を公開します。

```bash
# Gumroad商品を公開（API経由）
curl -X PUT "https://api.gumroad.com/v2/products/0cLA422g9idvoU7_StDrwg==" \
  -H "Authorization: Bearer C1iVMaAFp7nJ9DnDFMJkHHVDZ8c0jppWjmC_piDvZpI" \
  -d "published=true"
```

または Gumroad ダッシュボードから手動で「Publish」をクリック。

## トラブルシューティング

### アプリが起動しない場合

**エラー: `ModuleNotFoundError`**
```
requirements.txt の依存パッケージを確認してください。
Streamlit Cloud は requirements.txt を自動で読み込みます。
```

**エラー: `ANTHROPIC_API_KEY not found`**
```
Secrets の設定を確認してください。
Settings → Secrets → 変数名と値を再確認。
```

**エラー: `StreamlitAPIException`**
```
app.py の先頭で st.set_page_config() を呼んでいることを確認。
他のStreamlitコマンドより前に実行する必要があります。
```

### ライセンス認証が失敗する場合

1. `GUMROAD_ACCESS_TOKEN` が正しく設定されているか確認
2. Gumroad商品が公開済み（Published）であることを確認
3. `core/license.py` の `PRODUCT_PERMALINK` が `"career-ai-monthly"` になっているか確認

## ローカル開発環境のセットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/aiagenta523-glitch/agenta_ventures.git
cd agenta_ventures

# 2. 仮想環境を作成・有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 依存パッケージをインストール
pip install -r requirements.txt

# 4. 環境変数を設定
cp .env.example .env
# .env を編集して APIキーを入力

# 5. アプリを起動
streamlit run app.py
# → http://localhost:8501 でアクセス可能
```

## テストの実行

```bash
# ユニットテスト（APIキー不要）
python -m pytest tests/ -v

# 特定テストのみ実行
python -m pytest tests/test_license.py -v
```

## アップデートのデプロイ

Streamlit Cloud は GitHub の `main` ブランチへのプッシュを自動検知してデプロイします。

```bash
git add .
git commit -m "fix: ..."
git push origin main
# → Streamlit Cloud が自動的に再デプロイ
```
