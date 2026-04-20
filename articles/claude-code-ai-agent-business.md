---
title: "Claude Codeで個人開発を自動化した話 ― AIエージェントに事業を任せてみた"
emoji: "🤖"
type: "idea"
topics: ["ClaudeCode", "個人開発", "AIエージェント", "副業", "エンジニア"]
published: false
---

AIが「コードを書く手伝い」から「事業を動かす主体」に変わりつつある2026年、私はClaude Codeに一つの実験をしました。**自律的なAI組織を構築し、そこに¥5,000の初期資金を与えて「稼いでこい」と言ったらどうなるか**――。

この記事では、そのプロセスで気づいた「AIエージェントに個人開発を任せるための設計思想」と、副産物として生まれた具体的な成果物（転職相談AI「CareerAI」）の話をします。

---

## 目次

1. [きっかけ：「AIに事業を作らせたらどうなる？」という問い](#1-きっかけ)
2. [構造設計：Claude Code組織の作り方](#2-構造設計)
3. [CLAUDE.mdが鍵：AIに「文脈と権限」を渡す技術](#3-claudemdが鍵)
4. [実際に起きたこと：72時間でMVPが生まれるまで](#4-実際に起きたこと)
5. [技術スタックと実装の核心](#5-技術スタックと実装の核心)
6. [失敗と学び：自律エージェントが詰まるポイント](#6-失敗と学び)
7. [次のフェーズへ：CareerAIと自動化の未来](#7-次のフェーズへ)
8. [あなたも試せる：最小構成から始める方法](#8-あなたも試せる)

---

## 1. きっかけ：「AIに事業を作らせたらどうなる？」という問い

個人開発者として長年生きてきて、壁にぶつかる場所はいつも同じでした。

**コードは書ける。でも、事業にならない。**

マーケティング、コンテンツ制作、競合分析、収益化設計――これらは「コードを書く」スキルとは別の能力を要求します。一人では全部できない。チームを組む資金もない。そこで思ったのです。

「Claude Codeに組織を作らせたらどうだろう」

---

## 2. 構造設計：Claude Code組織の作り方

私が作った組織は、ディレクトリ構造とCLAUDE.mdファイルの組み合わせで動きます。

```
claude_org/
├── agenta/          # 受付・タスク管理
├── ventures/
│   ├── ceo/         # 全体戦略・PDCA統括
│   ├── strategy/    # 市場調査・アイデア生成
│   ├── execution/   # 実装・コンテンツ制作
│   ├── review/      # KPI評価
│   └── finance/     # P&L管理
├── finance/
│   └── cfo/         # 予算管理
└── shared/
    ├── roles/       # 各ロールの定義
    └── conventions.md
```

ポイントは**役割の分離**です。

CEOは「何をするか」を決め、Strategyは「何が市場に刺さるか」を調べ、Executionは「実際に作る」。各チームはCLAUDE.mdで自分の責務を持ち、`handoff/` ディレクトリ経由で成果物を受け渡します。

Claudeに対して言っているのは「あなたは今、ventures/ceoというロールで動いてください」という文脈付けだけです。残りはCLAUDE.mdが担います。

---

## 3. CLAUDE.mdが鍵：AIに「文脈と権限」を渡す技術

このシステムで最も重要なファイルはCLAUDE.mdです。

通常のClaude Codeセッションは文脈がリセットされます。しかし、CLAUDE.mdを適切に書くことで、「このセッションが何のためのもので、どこまで自律的に動いて良いか」をAIに伝えることができます。

例えば、ventures/ceo/CLAUDE.mdの冒頭：

```markdown
# Ventures CEO

## ミッション
claude_orgの利益を最大化する。¥5,000の初期資金を起点に収益を生み出す。

## 権限
- ventures内の組織構造を自由に改編できる
- 戦略のピボットを自律的に判断できる
```

**「何をして良いか」と「何をしてはいけないか」を明示する**。これだけで、AIは過度に確認を求めることなく自律的に動きます。

### 特に重要な3つの要素

**① オーナー依存を最小化する原則**

```markdown
## オーナー依存を最小化する原則（最重要）
オーナーへの依頼は最後の手段。以下の順序で必ず検討する：
1. APIで自動化できないか？
2. 既存の認証情報で代替できないか？
3. 別の手段で同じ目的を達成できないか？
4. どうしてもオーナーが必要な場合のみ依頼する
```

この一文が、AIを「何かあればすぐ人間に確認する受け身な存在」から「自分でまず考えて動く能動的な存在」に変えます。

**② handoffプロトコル**

成果物は必ず`handoff/`ディレクトリ経由で受け渡します。Claudeは複数セッションにまたがって記憶を持てませんが、ファイルは残ります。前のセッションの成果が次のセッションへの入力になる構造です。

**③ ログ記録の義務化**

```bash
python3 log_task.py \
  '{"task_id":"ceo_hourly","role":"ventures/ceo","action":"completed",
    "summary":"今回の判断・行動を一行で"}'
```

AIが何をしたかを記録させることで、複数セッションにわたる継続性が生まれます。

---

## 4. 実際に起きたこと：72時間でMVPが生まれるまで

### Day 1: 戦略フェーズ

CEOとして起動したClaude Codeがまず行ったのは**市場調査**でした。

- エンジニア転職相談 AI の競合をWebで調査
- 日本のエンジニア転職市場の規模を把握
- Gumroad・Zenn・noteなどの収益化プラットフォームを比較
- 「初期コスト¥0で始められるか」を全候補で検証

出てきた結論：**「エンジニア特化の転職相談AI」はニーズがあり、初期コスト¥0で始められる**。

### Day 2: 実装フェーズ

Executionチームに移行。実装するものが決まりました：

- Streamlit + Anthropic APIのチャットアプリ
- 無料版（月10回）/ 有料版（無制限）の2段階
- Gumroadでライセンスキー販売
- プロンプトキャッシュでAPI費用を最適化

6時間後、コードが完成しました。

### Day 3: コンテンツフェーズ

コードだけでは売れません。Zenn・Qiita記事の原稿を制作し、Gumroad商品ページの説明文も作りました。

この時点での状態：
- ✅ コード完成・GitHubプッシュ済み
- ✅ Gumroad商品作成済み（ドラフト）
- ✅ Zenn記事原稿完成
- ⏳ デプロイ先（Streamlit Cloud）: オーナー操作待ち

---

## 5. 技術スタックと実装の核心

### 使用技術

| 技術 | 用途 |
|------|------|
| Python 3.11 | アプリケーション本体 |
| Streamlit | UIフレームワーク |
| Anthropic Python SDK | Claude API呼び出し |
| Gumroad API | ライセンス認証 |

### プロンプトキャッシュの実装

最もコストに効く工夫がプロンプトキャッシュです。システムプロンプト（約2,000トークン）を毎回送るのではなく、初回だけ送ってキャッシュします。

```python
def create_career_message(self, conversation_history: list, user_message: str) -> dict:
    system_with_cache = [
        {
            "type": "text",
            "text": CAREER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}  # プロンプトキャッシュ
        }
    ]
    return {
        "system": system_with_cache,
        "messages": conversation_history + [
            {"role": "user", "content": user_message}
        ]
    }
```

同一会話内でシステムプロンプトへのトークン費用が約90%削減されます。

### Gumroadライセンス認証

```python
def verify_license(self, license_key: str, product_id: str) -> dict:
    response = requests.post(
        "https://api.gumroad.com/v2/licenses/verify",
        data={"product_id": product_id, "license_key": license_key}
    )
    if response.status_code == 200:
        data = response.json()
        return {"valid": data.get("success", False), "uses": data.get("uses", 0)}
    return {"valid": False, "uses": 0}
```

サーバーサイドにデータベース不要でライセンス管理できます。

---

## 6. 失敗と学び：自律エージェントが詰まるポイント

### ① 「人間操作の壁」

Streamlit Cloud、HuggingFace Spaces、Vercel――いずれも「ブラウザでアカウント作成」が必要です。APIだけでは突破できません。

**対策**: デプロイが必要なアーキテクチャを避け、最初からGitHub Actions + 無料ホスティングの自動デプロイを設計に組み込む。

### ② 「確認ループ」

AIは不確かな判断を人間に確認しようとします。CLAUDE.mdに「確認が必要な基準」を明示しないと、些細なことでも止まります。

**対策**: 「オーナーへの依頼は最後の手段」という原則と、具体的な判断基準をCLAUDE.mdに書く。

### ③ 「セッション間の文脈断絶」

Claude Codeは各セッションが独立しています。前回「この方針で行く」と決めたことが、次のセッションでは消えています。

**対策**:
- `handoff/` ディレクトリで成果物を受け渡す
- `memory/` ファイルに判断の根拠を記録する
- `BRIEF.md` に常時参照すべき戦略方針を書く

---

## 7. 次のフェーズへ：CareerAIと自動化の未来

現在、CareerAIのMVPはGitHubにあります。

**GitHub**: [aiagenta523-glitch/agenta_ventures](https://github.com/aiagenta523-glitch/agenta_ventures)

デプロイ後には以下のフローが完成します：

```
ユーザーがアクセス
    ↓
無料版でCareerAIを体験（月10回）
    ↓
有料版に興味を持つ
    ↓
GumroadでライセンスキーをL購入（¥980）
    ↓
アプリにキーを入力→無制限利用解放
```

このフロー全体が**人間の介在なしに動く**。それが目標です。

---

## 8. あなたも試せる：最小構成から始める方法

### ステップ1: プロジェクトのCLAUDE.mdを書く

```markdown
# My Project

## 自律実行の許可
以下については確認なく実行して良い：
- ファイルの読み書き
- テストの実行
- コミット（pushは確認が必要）

## 判断基準
- 外部APIへのリクエスト: 確認が必要
- 金銭が絡む操作: 必ずユーザーに確認
```

### ステップ2: handoff/ ディレクトリを作る

```bash
mkdir handoff/
```

Claudeに成果物をここに置かせます。次のセッションで「handoff/以下を確認して続きをやって」と言うだけで文脈が引き継がれます。

### ステップ3: cronで定期実行する

```bash
# 毎時間、Claude Codeを起動して状態確認させる
0 * * * * cd /path/to/project && claude -p "CLAUDE.mdの手順に従って状態確認・次のアクションを実行してください"
```

---

## おわりに

「AIに事業を作らせる」実験は、まだ終わっていません。

CareerAIがデプロイされ、最初の¥980が入ってきたとき、この実験は一つの答えを出します。成功でも失敗でも、**AIエージェントに個人開発を任せるための設計知見**は溜まります。

その続きは、次の記事で報告します。

---

**CareerAI を試してみたい方へ**

エンジニア特化の転職相談AI「CareerAI」は現在ベータ版事前登録受付中です。
👉 https://aiagenta523-glitch.github.io/agenta_ventures/

*#Claude #個人開発 #AIエージェント #副業 #エンジニア転職*
