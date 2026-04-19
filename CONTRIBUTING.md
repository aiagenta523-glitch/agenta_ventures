# Contributing to CareerAI

CareerAIへの貢献を歓迎します！バグ報告・機能提案・コードの改善など、あらゆる形での参加をお待ちしています。

## 開発環境のセットアップ

```bash
git clone https://github.com/aiagenta523-glitch/agenta_ventures.git
cd agenta_ventures
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env に ANTHROPIC_API_KEY を設定
```

## コントリビューションの流れ

1. このリポジトリを Fork する
2. フィーチャーブランチを作成する: `git checkout -b feature/your-feature`
3. 変更をコミットする: `git commit -m 'Add: your feature'`
4. ブランチにプッシュする: `git push origin feature/your-feature`
5. Pull Request を作成する

## コーディング規約

- **フォーマット**: `black` を使用（`pip install black && black .`）
- **型ヒント**: 新規関数には型ヒントを追加する
- **ドキュメント**: 公開関数にはdocstringを記載する
- **テスト**: 新機能にはユニットテストを追加する

## テスト

```bash
# テストの実行
python -m pytest tests/ -v

# カバレッジ確認
python -m pytest tests/ --cov=core --cov-report=term-missing
```

## バグ報告

バグを発見した場合は [GitHub Issues](https://github.com/aiagenta523-glitch/agenta_ventures/issues) で報告してください。

報告に含めると助かる情報:
- 再現手順
- 期待される動作
- 実際の動作
- エラーメッセージ（あれば）
- 環境情報（OS・Pythonバージョン）

## 機能提案

新機能の提案も GitHub Issues で受け付けています。
実装前に Issue でディスカッションすることをお勧めします。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。
