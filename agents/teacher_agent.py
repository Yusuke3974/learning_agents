"""教師エージェント - 学習コンテンツの提供と説明を行う"""
import logging
import os
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.a2a import create_task_message, send_task
from core.prompt_loader import get_prompt

# ロギング設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teacher", tags=["teacher"])

# エージェント名
AGENT_NAME = "teacher"

# プロンプトを読み込む（起動時に1回だけ実行）
AGENT_PROMPT = get_prompt(AGENT_NAME)
logger.info(f"[{AGENT_NAME}] エージェントプロンプトを読み込みました（{len(AGENT_PROMPT) if AGENT_PROMPT else 0}文字）")


class QuestionType(str, Enum):
    """質問の種類"""
    EXPLANATION = "explanation"  # 説明依頼
    PRACTICE = "practice"  # 練習問題依頼
    REVIEW = "review"  # 復習依頼


class AskRequest(BaseModel):
    """質問リクエスト"""
    question: str
    topic: Optional[str] = None
    subject: Optional[str] = None


class AskResponse(BaseModel):
    """質問レスポンス"""
    question_type: QuestionType
    response: dict
    routed_to: Optional[str] = None


def classify_question(question: str) -> QuestionType:
    """質問の種類を分類する
    
    Args:
        question: ユーザーの質問
        
    Returns:
        質問の種類（QuestionType）
    """
    question_lower = question.lower()
    
    # 復習依頼のキーワード
    review_keywords = [
        "復習", "前回", "以前", "再度", "もう一度", 
        "review", "revisit", "again", "previous"
    ]
    
    # 練習問題依頼のキーワード
    practice_keywords = [
        "練習", "練習問題", "問題", "クイズ", "テスト",
        "practice", "exercise", "quiz", "problem", "test"
    ]
    
    # キーワードチェック
    if any(keyword in question_lower for keyword in review_keywords):
        logger.info(f"質問を復習依頼として分類: {question}")
        return QuestionType.REVIEW
    
    if any(keyword in question_lower for keyword in practice_keywords):
        logger.info(f"質問を練習問題依頼として分類: {question}")
        return QuestionType.PRACTICE
    
    # デフォルトは説明依頼
    logger.info(f"質問を説明依頼として分類: {question}")
    return QuestionType.EXPLANATION


async def call_quiz_agent(topic: Optional[str], subject: Optional[str]) -> dict:
    """QuizAgentにクイズ生成を依頼する（A2A形式）
    
    Args:
        topic: トピック
        subject: 科目
        
    Returns:
        QuizAgentからのレスポンス
    """
    message_data = {}
    if topic:
        message_data["topic"] = topic
    if subject:
        message_data["subject"] = subject
    message_data["level"] = "intermediate"  # デフォルト値
    message_data["question_type"] = "multiple_choice"  # デフォルト値
    
    task_message = create_task_message(
        sender=AGENT_NAME,
        receiver="quiz",
        message=message_data
    )
    
    logger.info(
        f"[{AGENT_NAME}] QuizAgentにクイズ生成を依頼: "
        f"task_id={task_message.task_id}, topic={topic}, subject={subject}"
    )
    
    result = await send_task("/quiz/generate-quiz", task_message)
    return result


async def call_review_agent(topic: Optional[str], user_id: Optional[str] = None) -> dict:
    """ReviewAgentに復習コンテンツを依頼する（A2A形式）
    
    Args:
        topic: トピック
        user_id: ユーザーID（オプション、デフォルトは"default_user"）
        
    Returns:
        ReviewAgentからのレスポンス
    """
    message_data = {
        "user_id": user_id or "default_user"
    }
    if topic:
        message_data["topic"] = topic
    
    task_message = create_task_message(
        sender=AGENT_NAME,
        receiver="review",
        message=message_data
    )
    
    logger.info(
        f"[{AGENT_NAME}] ReviewAgentに復習コンテンツを依頼: "
        f"task_id={task_message.task_id}, topic={topic}, user_id={message_data['user_id']}"
    )
    
    result = await send_task("/review/review", task_message)
    return result


async def call_openai_api(question: str, topic: Optional[str] = None) -> dict:
    """OpenAI APIを使って質問に直接回答する
    
    Args:
        question: ユーザーの質問
        topic: トピック（オプション）
        
    Returns:
        OpenAI APIからのレスポンス
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        logger.warning("OPENAI_API_KEYが設定されていません。代替回答を返します。")
        # OpenAI APIキーが設定されていない場合は代替回答
        return {
            "answer": f"質問「{question}」について説明します。\n\n"
                     f"この機能を完全に利用するには、OpenAI APIキーの設定が必要です。"
                     f"現在は簡易的な回答のみを提供しています。",
            "model": "none",
            "source": "fallback"
        }
    
    # OpenAI APIが利用可能な場合の実装
    # 注: openaiパッケージがインストールされていない場合はスキップ
    try:
        import openai
        
        logger.info(f"OpenAI APIを呼び出し: {question}")
        
        client = openai.AsyncOpenAI(api_key=openai_api_key)
        
        prompt = f"以下の質問について分かりやすく説明してください:\n\n{question}"
        if topic:
            prompt += f"\n\nトピック: {topic}"
        
        # エージェントプロンプトをシステムメッセージに使用
        system_message = AGENT_PROMPT if AGENT_PROMPT else "あなたは優秀な教師です。質問に分かりやすく、丁寧に回答してください。"
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        answer = response.choices[0].message.content
        
        logger.info(f"OpenAI APIからの応答を取得: {len(answer)}文字")
        
        return {
            "answer": answer,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "source": "openai"
        }
        
    except ImportError:
        logger.warning("openaiパッケージがインストールされていません。代替回答を返します。")
        return {
            "answer": f"質問「{question}」について説明します。\n\n"
                     f"OpenAI APIを使用するには、openaiパッケージのインストールと"
                     f"OPENAI_API_KEYの設定が必要です。",
            "model": "none",
            "source": "fallback"
        }
    except Exception as e:
        logger.error(f"OpenAI API呼び出しエラー: {e}")
        return {
            "answer": f"質問「{question}」について説明します。\n\n"
                     f"OpenAI API呼び出し中にエラーが発生しました: {str(e)}",
            "model": "none",
            "source": "error",
            "error": str(e)
        }


@router.get("/")
async def teacher_root():
    """教師エージェントのルートエンドポイント"""
    return {"agent": "teacher", "status": "ready"}


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """ユーザーの質問を受け取り、種類に応じて適切なエージェントに転送する
    
    処理フロー:
    1. 質問の種類を分類
    2. 種類に応じて適切なエージェントに転送
       - 練習問題依頼 → QuizAgent
       - 復習依頼 → ReviewAgent
       - 説明依頼 → OpenAI API（直接回答）
    """
    logger.info(f"質問を受信: {request.question}")
    
    # 質問の種類を分類
    question_type = classify_question(request.question)
    logger.info(f"質問タイプ: {question_type.value}")
    
    response_data: dict
    routed_to: Optional[str] = None
    
    try:
        if question_type == QuestionType.PRACTICE:
            # 練習問題依頼 → QuizAgentに転送
            logger.info(f"[{AGENT_NAME}] 練習問題依頼としてQuizAgentに転送します")
            a2a_response = await call_quiz_agent(
                topic=request.topic,
                subject=request.subject
            )
            # A2A形式のレスポンスからresultを取得
            response_data = a2a_response.get("result", a2a_response)
            routed_to = "quiz_agent"
            
        elif question_type == QuestionType.REVIEW:
            # 復習依頼 → ReviewAgentに転送
            logger.info(f"[{AGENT_NAME}] 復習依頼としてReviewAgentに転送します")
            # ユーザーIDは将来的にリクエストから取得できるように拡張可能
            a2a_response = await call_review_agent(topic=request.topic, user_id="default_user")
            # A2A形式のレスポンスからresultを取得
            response_data = a2a_response.get("result", a2a_response)
            routed_to = "review_agent"
            
        else:
            # 説明依頼 → OpenAI APIで直接回答
            logger.info(f"[{AGENT_NAME}] 説明依頼としてOpenAI APIで直接回答します")
            response_data = await call_openai_api(
                question=request.question,
                topic=request.topic
            )
            routed_to = "openai_api"
        
        logger.info(
            f"[{AGENT_NAME}] 質問処理完了: question_type={question_type.value}, "
            f"routed_to={routed_to}"
        )
        
        return AskResponse(
            question_type=question_type,
            response=response_data,
            routed_to=routed_to
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"質問処理中にエラーが発生: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"質問の処理中にエラーが発生しました: {str(e)}"
        )


@router.post("/explain")
async def explain_topic():
    """トピックの説明を提供（プレースホルダー）"""
    return {"message": "Explanation endpoint - to be implemented"}


@router.get("/topics")
async def list_topics():
    """利用可能なトピック一覧を取得（プレースホルダー）"""
    return {"topics": []}
