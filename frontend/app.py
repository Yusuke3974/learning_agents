"""Streamlitフロントエンド - 学習エージェントのUI

TeacherAgentの/askエンドポイントに接続して、チャット形式で学習をサポートします。
"""
import json
import os
from typing import Dict, List, Optional

import httpx
import streamlit as st

# API設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEACHER_API_URL = f"{API_BASE_URL}/teacher/ask"

# ページ設定
st.set_page_config(
    page_title="Learning Agents",
    page_icon="📚",
    layout="wide"
)

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = None  # {"questions": [], "current_question": 0, "answers": {}}
if "show_result" not in st.session_state:
    st.session_state.show_result = False


def call_teacher_agent(question: str, topic: Optional[str] = None, subject: Optional[str] = None) -> Dict:
    """TeacherAgentの/askエンドポイントを呼び出す
    
    Args:
        question: 質問
        topic: トピック（オプション）
        subject: 科目（オプション）
        
    Returns:
        APIレスポンス
    """
    try:
        payload = {"question": question}
        if topic:
            payload["topic"] = topic
        if subject:
            payload["subject"] = subject
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(TEACHER_API_URL, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"API呼び出しエラー: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"予期しないエラー: {str(e)}")
        return {"error": str(e)}


def display_quiz(questions: List[Dict]) -> Dict[str, str]:
    """クイズを表示し、回答を取得する
    
    Args:
        questions: クイズ問題のリスト
        
    Returns:
        回答辞書 {question_index: selected_answer}
    """
    answers = {}
    
    for idx, question in enumerate(questions):
        st.markdown("---")
        st.markdown(f"### 問題 {idx + 1}")
        st.markdown(f"**{question.get('question', '')}**")
        
        options = question.get("options", [])
        correct_answer = question.get("answer", "")
        
        if options:
            selected = st.radio(
                "選択してください:",
                options,
                key=f"quiz_{idx}",
                index=None
            )
            if selected:
                answers[str(idx)] = selected
        else:
            st.warning("選択肢がありません")
    
    return answers


def check_quiz_answers(questions: List[Dict], answers: Dict[str, str]) -> Dict:
    """クイズの回答をチェックする
    
    Args:
        questions: クイズ問題のリスト
        answers: 回答辞書
        
    Returns:
        結果辞書
    """
    results = {
        "total": len(questions),
        "correct": 0,
        "incorrect": 0,
        "details": []
    }
    
    for idx, question in enumerate(questions):
        user_answer = answers.get(str(idx), "")
        correct_answer = question.get("answer", "")
        is_correct = user_answer == correct_answer
        
        if is_correct:
            results["correct"] += 1
        else:
            results["incorrect"] += 1
        
        results["details"].append({
            "question": question.get("question", ""),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        })
    
    return results


def main():
    """メインアプリケーション"""
    st.title("📚 Learning Agents")
    st.markdown("AIエージェントベースの学習システム")
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        api_url = st.text_input("API URL", value=API_BASE_URL)
        if api_url != API_BASE_URL:
            st.session_state.api_base_url = api_url
        
        st.markdown("---")
        st.markdown("### 📋 使い方")
        st.markdown("""
        1. チャットで質問を入力する
        2. 「練習する」「復習する」ボタンで機能を呼び出す
        3. クイズに回答して学習を進める
        """)
    
    # クイズ状態がある場合は結果を表示
    if st.session_state.quiz_state and st.session_state.show_result:
        st.markdown("## 📊 クイズ結果")
        quiz_data = st.session_state.quiz_state
        
        if "questions" in quiz_data and "answers" in quiz_data:
            questions = quiz_data["questions"]
            answers = quiz_data["answers"]
            results = check_quiz_answers(questions, answers)
            
            # 結果サマリー
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総問題数", results["total"])
            with col2:
                st.metric("正解", results["correct"], delta=f"{results['correct']/results['total']*100:.1f}%")
            with col3:
                st.metric("不正解", results["incorrect"])
            
            # 詳細結果
            st.markdown("### 詳細結果")
            for idx, detail in enumerate(results["details"]):
                with st.expander(f"問題 {idx + 1}: {detail['question'][:50]}..."):
                    if detail["is_correct"]:
                        st.success(f"✅ 正解: {detail['correct_answer']}")
                    else:
                        st.error(f"❌ 不正解")
                        st.info(f"あなたの回答: {detail['user_answer']}")
                        st.success(f"正解: {detail['correct_answer']}")
            
            if st.button("🔄 新しいクイズを開始"):
                st.session_state.quiz_state = None
                st.session_state.show_result = False
                st.rerun()
        
        st.markdown("---")
    
    # クイズ状態がある場合はクイズを表示
    elif st.session_state.quiz_state and "questions" in st.session_state.quiz_state:
        st.markdown("## 📝 クイズ")
        questions = st.session_state.quiz_state["questions"]
        answers = display_quiz(questions)
        
        if st.button("✅ 回答を提出", type="primary"):
            st.session_state.quiz_state["answers"] = answers
            st.session_state.show_result = True
            st.rerun()
    
    # メインのチャットUI
    else:
        # クイックアクションボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 練習する", type="primary", use_container_width=True):
                with st.spinner("クイズを生成中..."):
                    response = call_teacher_agent("英語の冠詞の練習問題を出して", topic="English articles")
                    if "error" not in response:
                        question_type = response.get("question_type", "")
                        if question_type == "practice":
                            result_data = response.get("response", {})
                            if "questions" in result_data:
                                st.session_state.quiz_state = {
                                    "questions": result_data["questions"],
                                    "current_question": 0,
                                    "answers": {}
                                }
                                st.rerun()
        
        with col2:
            if st.button("🔄 復習する", type="secondary", use_container_width=True):
                with st.spinner("復習コンテンツを取得中..."):
                    response = call_teacher_agent("前回の内容を復習したい", topic="Python decorators")
                    if "error" not in response:
                        question_type = response.get("question_type", "")
                        result_data = response.get("response", {})
                        
                        if question_type == "review":
                            # 復習コンテンツを表示
                            st.markdown("## 🔄 復習コンテンツ")
                            if "summary" in result_data:
                                summary = result_data["summary"]
                                st.json(summary)
                            if "review_contents" in result_data:
                                st.markdown("### おすすめの復習内容")
                                for content in result_data["review_contents"]:
                                    with st.expander(content.get("title", "")):
                                        st.markdown(content.get("description", ""))
                        else:
                            # 説明を表示
                            st.info("説明依頼として処理されました")
                            if "answer" in result_data:
                                st.markdown(result_data["answer"])
        
        st.markdown("---")
        
        # チャット履歴を表示
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "response_data" in message:
                    with st.expander("レスポンス詳細"):
                        st.json(message["response_data"])
        
        # チャット入力
        if prompt := st.chat_input("質問を入力してください..."):
            # ユーザーメッセージを表示
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # API呼び出し
            with st.chat_message("assistant"):
                with st.spinner("考え中..."):
                    response = call_teacher_agent(prompt)
                    
                    if "error" in response:
                        st.error(f"エラーが発生しました: {response['error']}")
                    else:
                        question_type = response.get("question_type", "")
                        result_data = response.get("response", {})
                        routed_to = response.get("routed_to", "")
                        
                        # レスポンスタイプに応じて処理
                        if question_type == "practice":
                            # 練習問題依頼
                            if "questions" in result_data:
                                questions = result_data["questions"]
                                st.session_state.quiz_state = {
                                    "questions": questions,
                                    "current_question": 0,
                                    "answers": {}
                                }
                                st.success(f"クイズが生成されました（{len(questions)}問）")
                                st.rerun()
                            else:
                                st.info("練習問題を生成中です...")
                                st.json(result_data)
                        
                        elif question_type == "review":
                            # 復習依頼
                            st.markdown("### 🔄 復習コンテンツ")
                            if "summary" in result_data:
                                summary = result_data["summary"]
                                st.markdown(f"**直近のトピック**: {', '.join(summary.get('recent_topics', []))}")
                                st.markdown(f"**弱点**: {', '.join(summary.get('weak_areas', []))}")
                                st.markdown(f"**総セッション数**: {summary.get('total_sessions', 0)}")
                                st.markdown(f"**過去ノート数**: {summary.get('past_notes_count', 0)}")
                            
                            if "review_contents" in result_data:
                                st.markdown("### おすすめの復習内容")
                                for content in result_data["review_contents"]:
                                    with st.expander(content.get("title", "")):
                                        st.markdown(content.get("description", ""))
                        
                        else:
                            # 説明依頼
                            if "answer" in result_data:
                                st.markdown(result_data["answer"])
                            else:
                                st.json(result_data)
                        
                        # メッセージを履歴に追加
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"[{question_type}] 処理完了",
                            "response_data": response
                        })


if __name__ == "__main__":
    main()

