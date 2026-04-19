"""
キャリア相談AI - エンジニアのためのAIメンター
Streamlit メインアプリケーション
"""

import os
import streamlit as st
from dotenv import load_dotenv

# ローカル開発時のみ .env を読み込む（Streamlit Cloud では Secrets を使用）
load_dotenv()

from core.agent import chat, chat_premium
from core.license import verify_license

# ページ設定
st.set_page_config(
    page_title="キャリア相談AI | エンジニア専門AIメンター",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

FREE_LIMIT = 10

# --- サイドバー ---
with st.sidebar:
    st.title("💼 CareerAI")
    st.caption("エンジニア専門AIメンター")

    st.divider()

    # 使い方説明
    st.subheader("使い方")
    st.markdown(
        """
1. チャット欄にキャリアの悩みを入力する
2. AIが具体的なアドバイスを返答する
3. 会話を続けて深掘りする

**相談できること:**
- 転職・キャリアチェンジ
- スキルアップ・学習計画
- 年収・待遇交渉
- フリーランス転向
- 技術選定・市場価値確認
"""
    )

    st.divider()

    # プレミアムプラン
    st.subheader("プレミアムプラン")

    if not st.session_state.is_premium:
        remaining = FREE_LIMIT - st.session_state.usage_count
        st.info(f"無料版: 残り **{remaining}** 回 / {FREE_LIMIT}回")

        with st.expander("ライセンスキーで認証する"):
            license_input = st.text_input(
                "ライセンスキー",
                type="password",
                placeholder="XXXX-XXXX-XXXX-XXXX",
                key="license_key_input",
            )
            if st.button("認証する", use_container_width=True):
                if license_input:
                    with st.spinner("認証中..."):
                        result = verify_license(license_input)
                    if result["valid"]:
                        st.session_state.is_premium = True
                        st.success(f"認証成功！\n{result['email']}")
                        st.rerun()
                    else:
                        st.error(result["error"])
                else:
                    st.warning("ライセンスキーを入力してください")

        st.markdown(
            """
**プレミアムプランの特典:**
- 無制限相談
- Claude Sonnet（高精度モデル）使用
- より詳細な回答・分析

[プレミアムプランを購入（¥2,000/月）](https://gumroad.com/l/career-ai-monthly)
"""
        )
    else:
        st.success("プレミアムプラン 有効")
        st.caption("Claude Sonnet（高精度モデル）で無制限相談中")

    st.divider()

    # 会話リセット
    if st.button("会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- メインエリア ---
st.title("キャリア相談AI")
st.caption("エンジニアのためのAIメンター - 転職・スキルアップ・年収交渉をサポート")

# 使用制限チェック（無料版）
if not st.session_state.is_premium and st.session_state.usage_count >= FREE_LIMIT:
    st.warning(
        f"今月の無料相談回数（{FREE_LIMIT}回）に達しました。\n\n"
        "引き続きご利用いただくには、サイドバーからプレミアムプランをご購入ください。"
    )
    st.markdown(
        "[プレミアムプランを購入（¥2,000/月）](https://gumroad.com/l/career-ai-monthly)",
        unsafe_allow_html=False,
    )
    st.stop()

# ウェルカムメッセージ（会話が空のとき）
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "こんにちは！エンジニア専門のキャリアアドバイザーAIです。\n\n"
            "転職・スキルアップ・年収交渉・フリーランス転向など、キャリアに関することを何でもご相談ください。\n\n"
            "まず、現在の**経験年数**と**主な技術スタック**、そして**一番の悩み**を教えていただけますか？"
        )

# 会話履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# チャット入力
if prompt := st.chat_input("キャリアの悩みを相談してください..."):
    # ユーザーメッセージを追加・表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI応答を生成
    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            try:
                if st.session_state.is_premium:
                    response_text = chat_premium(st.session_state.messages)
                else:
                    response_text = chat(st.session_state.messages)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}\nしばらくしてから再試行してください。")
                st.stop()

        st.markdown(response_text)

    # 会話履歴・カウンター更新
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    if not st.session_state.is_premium:
        st.session_state.usage_count += 1

    st.rerun()
