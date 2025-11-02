"""復習エージェント - 学習内容の復習とフィードバックを提供"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.a2a import TaskMessage
from core.prompt_loader import get_prompt

# MCPクライアントのインポート（ディレクトリ名の調整が必要な場合あり）
try:
    from mcp_client import call_past_notes
except ImportError:
    # フォールバック: 直接toolsモジュールからインポート
    import sys
    from pathlib import Path
    mcp_client_path = Path(__file__).parent.parent / "mcp-client"
    if str(mcp_client_path) not in sys.path:
        sys.path.insert(0, str(mcp_client_path))
    from tools import call_past_notes

# ロギング設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])

# エージェント名
AGENT_NAME = "review"

# プロンプトを読み込む（起動時に1回だけ実行）
AGENT_PROMPT = get_prompt(AGENT_NAME)
logger.info(f"[{AGENT_NAME}] エージェントプロンプトを読み込みました（{len(AGENT_PROMPT) if AGENT_PROMPT else 0}文字）")

# 学習ログのベースディレクトリ
LEARNING_LOGS_DIR = Path("data/learning_logs")


class LearningLogEntry(BaseModel):
    """学習ログエントリ"""
    topic: str
    timestamp: str
    score: Optional[float] = None
    status: str  # "completed", "in_progress", "failed"
    notes: Optional[str] = None


class LearningLogs(BaseModel):
    """学習ログ"""
    user_id: str
    entries: List[LearningLogEntry] = []


class ReviewContent(BaseModel):
    """復習コンテンツ"""
    type: str  # "quiz", "recommendation"
    title: str
    description: str
    topic: str
    action_url: Optional[str] = None


class ReviewSummary(BaseModel):
    """復習要約"""
    recent_topics: List[str]
    weak_areas: List[str]
    last_studied: Optional[str] = None
    total_sessions: int = 0
    past_notes_count: int = 0  # MCP経由で取得した過去ノート数


class ReviewRequest(BaseModel):
    """復習リクエスト"""
    user_id: str
    topic: Optional[str] = None


class ReviewResponse(BaseModel):
    """復習レスポンス"""
    summary: ReviewSummary
    review_contents: List[ReviewContent]


async def load_learning_logs(user_id: str) -> LearningLogs:
    """学習ログを読み込む
    
    Args:
        user_id: ユーザーID
        
    Returns:
        学習ログデータ
    """
    log_file = LEARNING_LOGS_DIR / f"{user_id}.json"
    
    logger.info(f"学習ログを読み込み: {log_file}")
    
    # ディレクトリが存在しない場合は作成
    LEARNING_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # ファイルが存在しない場合はモックデータを返す
    if not log_file.exists():
        logger.warning(f"学習ログファイルが見つかりません: {log_file}。モックデータを使用します。")
        return generate_mock_learning_logs(user_id)
    
    try:
        async with aiofiles.open(log_file, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            
        logs = LearningLogs(**data)
        logger.info(f"学習ログを読み込み完了: {len(logs.entries)}件のエントリ")
        return logs
        
    except json.JSONDecodeError as e:
        logger.error(f"JSONパースエラー: {e}")
        logger.warning("モックデータを使用します。")
        return generate_mock_learning_logs(user_id)
    except Exception as e:
        logger.error(f"学習ログ読み込みエラー: {e}")
        logger.warning("モックデータを使用します。")
        return generate_mock_learning_logs(user_id)


def generate_mock_learning_logs(user_id: str) -> LearningLogs:
    """モック学習ログを生成する
    
    Args:
        user_id: ユーザーID
        
    Returns:
        モック学習ログデータ
    """
    logger.info(f"モック学習ログを生成: user_id={user_id}")
    
    # モックデータ: 過去1週間分の学習ログ
    now = datetime.now()
    mock_entries = [
        LearningLogEntry(
            topic="Python decorators",
            timestamp=str(now.timestamp() - 86400 * 1),  # 1日前
            score=0.65,
            status="completed",
            notes="デコレータの基本的な使い方は理解できたが、応用に苦戦"
        ),
        LearningLogEntry(
            topic="Python list comprehensions",
            timestamp=str(now.timestamp() - 86400 * 2),  # 2日前
            score=0.85,
            status="completed",
            notes="理解度は高いが、複雑な条件式での使い方をもう一度確認"
        ),
        LearningLogEntry(
            topic="English articles (a, an, the)",
            timestamp=str(now.timestamp() - 86400 * 3),  # 3日前
            score=0.45,
            status="completed",
            notes="冠詞の使い分けが難しい。特に定冠詞と不定冠詞の区別"
        ),
        LearningLogEntry(
            topic="Python decorators",
            timestamp=str(now.timestamp() - 86400 * 5),  # 5日前
            score=0.55,
            status="completed",
            notes="初回学習。概念は理解できたが、実践で使えない"
        ),
        LearningLogEntry(
            topic="English grammar: past tense",
            timestamp=str(now.timestamp() - 86400 * 7),  # 7日前
            score=0.70,
            status="completed",
            notes="基本的な過去形は理解できた"
        ),
    ]
    
    return LearningLogs(user_id=user_id, entries=mock_entries)


async def analyze_learning_logs(
    logs: LearningLogs,
    user_id: str,
    topic: Optional[str] = None
) -> ReviewSummary:
    """学習ログを分析して要約を生成する（MCP統合版）
    
    Args:
        logs: 学習ログデータ
        user_id: ユーザーID
        topic: トピック（オプション、MCPノート取得用）
        
    Returns:
        復習要約
    """
    logger.info(f"[{AGENT_NAME}] 学習ログを分析: {len(logs.entries)}件のエントリ")
    
    if not logs.entries:
        return ReviewSummary(
            recent_topics=[],
            weak_areas=[],
            total_sessions=0,
            past_notes_count=0
        )
    
    # エントリを日時でソート（新しい順）
    sorted_entries = sorted(
        logs.entries,
        key=lambda e: float(e.timestamp),
        reverse=True
    )
    
    # 直近のトピック（最新5件）
    recent_topics = list(set([e.topic for e in sorted_entries[:5]]))
    
    # 弱点（スコアが0.6未満のトピック）
    weak_areas = []
    topic_scores = {}
    topic_counts = {}
    
    for entry in logs.entries:
        if entry.score is not None:
            if entry.topic not in topic_scores:
                topic_scores[entry.topic] = []
                topic_counts[entry.topic] = 0
            topic_scores[entry.topic].append(entry.score)
            topic_counts[entry.topic] += 1
    
    # トピックごとの平均スコアを計算
    for topic, scores in topic_scores.items():
        avg_score = sum(scores) / len(scores)
        if avg_score < 0.6:
            weak_areas.append(f"{topic} (平均スコア: {avg_score:.2f})")
    
    # 最後に学習した日時
    last_studied = None
    if sorted_entries:
        last_timestamp = float(sorted_entries[0].timestamp)
        last_studied = datetime.fromtimestamp(last_timestamp).isoformat()
    
    # MCP経由で過去ノートを取得
    past_notes_count = 0
    try:
        logger.info(
            f"[{AGENT_NAME}] MCP経由で過去ノートを取得: user_id={user_id}, topic={topic}"
        )
        mcp_result = await call_past_notes(
            user_id=user_id,
            topic=topic,
            limit=10
        )
        if mcp_result.get("status") == "success":
            past_notes_data = mcp_result.get("data", {})
            past_notes_count = past_notes_data.get("count", 0)
            logger.info(
                f"[{AGENT_NAME}] MCP過去ノート取得完了: "
                f"user_id={user_id}, count={past_notes_count}"
            )
        else:
            logger.warning(
                f"[{AGENT_NAME}] MCP過去ノート取得に失敗: user_id={user_id}"
            )
    except Exception as e:
        logger.error(
            f"[{AGENT_NAME}] MCP過去ノート取得エラー: user_id={user_id}, error={str(e)}",
            exc_info=True
        )
    
    summary = ReviewSummary(
        recent_topics=recent_topics,
        weak_areas=weak_areas,
        last_studied=last_studied,
        total_sessions=len(logs.entries),
        past_notes_count=past_notes_count
    )
    
    logger.info(
        f"[{AGENT_NAME}] 分析完了: 直近トピック={len(recent_topics)}件, "
        f"弱点={len(weak_areas)}件, 総セッション数={summary.total_sessions}, "
        f"過去ノート数={past_notes_count}"
    )
    
    return summary


def generate_review_contents(
    summary: ReviewSummary,
    requested_topic: Optional[str] = None
) -> List[ReviewContent]:
    """復習コンテンツを生成する
    
    Args:
        summary: 復習要約
        requested_topic: リクエストされたトピック（オプション）
        
    Returns:
        復習コンテンツのリスト（1〜2件）
    """
    logger.info("復習コンテンツを生成")
    
    contents = []
    
    # リクエストされたトピックがある場合は優先
    if requested_topic:
        contents.append(ReviewContent(
            type="quiz",
            title=f"{requested_topic}の復習クイズ",
            description=f"{requested_topic}に関する理解度を確認するためのクイズです。",
            topic=requested_topic,
            action_url=f"/quiz/generate-quiz?topic={requested_topic}"
        ))
        
        if len(contents) < 2 and summary.weak_areas:
            # 弱点から1件追加
            weak_topic = summary.weak_areas[0].split(" (")[0]
            if weak_topic != requested_topic:
                contents.append(ReviewContent(
                    type="recommendation",
                    title=f"{weak_topic}をもう一度学習",
                    description=f"過去のスコアが低かったため、{weak_topic}の復習をおすすめします。",
                    topic=weak_topic,
                    action_url=f"/teacher/ask?topic={weak_topic}"
                ))
    
    else:
        # 弱点を優先
        if summary.weak_areas:
            weak_topic = summary.weak_areas[0].split(" (")[0]
            contents.append(ReviewContent(
                type="quiz",
                title=f"{weak_topic}の復習クイズ",
                description=f"過去のスコアが低かったため、{weak_topic}の復習をおすすめします。",
                topic=weak_topic,
                action_url=f"/quiz/generate-quiz?topic={weak_topic}"
            ))
        
        # 直近のトピックから1件追加（弱点と重複しない場合）
        if len(contents) < 2 and summary.recent_topics:
            for topic in summary.recent_topics:
                if not any(c.topic == topic for c in contents):
                    contents.append(ReviewContent(
                        type="recommendation",
                        title=f"{topic}の復習",
                        description=f"最近学習した{topic}について、もう一度確認することをおすすめします。",
                        topic=topic,
                        action_url=f"/teacher/ask?topic={topic}"
                    ))
                    break
    
    # コンテンツが空の場合はデフォルト
    if not contents:
        default_topic = summary.recent_topics[0] if summary.recent_topics else "Python basics"
        contents.append(ReviewContent(
            type="recommendation",
            title="学習を継続しましょう",
            description="新しいトピックの学習をおすすめします。",
            topic=default_topic,
            action_url=f"/teacher/ask?topic={default_topic}"
        ))
    
    # 1〜2件に制限
    contents = contents[:2]
    
    logger.info(f"復習コンテンツ生成完了: {len(contents)}件")
    return contents


@router.get("/")
async def review_root():
    """復習エージェントのルートエンドポイント"""
    return {"agent": "review", "status": "ready"}


@router.post("/schedule")
async def schedule_review():
    """復習スケジュールを作成（プレースホルダー）"""
    return {"message": "Review scheduling endpoint - to be implemented"}


@router.post("/review")
async def review_content_a2a(task_message: TaskMessage) -> dict:
    """復習コンテンツを提供するエンドポイント（A2A形式）
    
    A2A形式のTaskMessageを受け取り、復習コンテンツを生成します。
    TaskMessage.messageには以下のフィールドが含まれます:
    - user_id: ユーザーID（必須）
    - topic: トピック（オプション）
    """
    logger.info(
        f"[{AGENT_NAME}] A2Aタスク受信: task_id={task_message.task_id}, "
        f"sender={task_message.sender}, receiver={task_message.receiver}"
    )
    logger.debug(f"[{AGENT_NAME}] タスクメッセージ: {task_message.message}")
    
    try:
        # TaskMessage.messageからリクエストパラメータを取得
        message = task_message.message
        user_id = message.get("user_id", "default_user")
        topic = message.get("topic")
        
        if not user_id:
            logger.error(
                f"[{AGENT_NAME}] ユーザーIDが指定されていません: task_id={task_message.task_id}"
            )
            raise HTTPException(
                status_code=400,
                detail="user_idフィールドが必要です"
            )
        
        logger.info(
            f"[{AGENT_NAME}] 復習リクエスト処理開始: task_id={task_message.task_id}, "
            f"user_id={user_id}, topic={topic}"
        )
        
        # 学習ログを読み込む
        logs = await load_learning_logs(user_id)
        
        # 学習ログを分析して要約を生成（MCP統合版）
        summary = await analyze_learning_logs(
            logs=logs,
            user_id=user_id,
            topic=topic
        )
        
        # 復習コンテンツを生成
        review_contents = generate_review_contents(
            summary=summary,
            requested_topic=topic
        )
        
        response_data = ReviewResponse(
            summary=summary,
            review_contents=review_contents
        )
        
        logger.info(
            f"[{AGENT_NAME}] 復習コンテンツ生成完了: task_id={task_message.task_id}, "
            f"要約トピック={len(summary.recent_topics)}件, "
            f"復習コンテンツ={len(review_contents)}件"
        )
        
        # A2A形式のレスポンスを返す
        return {
            "task_id": task_message.task_id,
            "sender": AGENT_NAME,
            "receiver": task_message.sender,
            "result": response_data.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{AGENT_NAME}] 復習コンテンツ生成中にエラーが発生: task_id={task_message.task_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"復習コンテンツ生成中にエラーが発生しました: {str(e)}"
        )


@router.post("/review-legacy", response_model=ReviewResponse)
async def review_content(request: ReviewRequest) -> ReviewResponse:
    """復習コンテンツを提供するエンドポイント（レガシー形式、後方互換性のため）
    
    リクエスト例:
    {
        "user_id": "user123",
        "topic": "Python decorators"  # オプション
    }
    """
    logger.info(
        f"[{AGENT_NAME}] レガシー形式の復習リクエスト受信: "
        f"user_id={request.user_id}, topic={request.topic}"
    )
    
    try:
        # 学習ログを読み込む
        logs = await load_learning_logs(request.user_id)
        
        # 学習ログを分析して要約を生成（MCP統合版）
        summary = await analyze_learning_logs(
            logs=logs,
            user_id=request.user_id,
            topic=request.topic
        )
        
        # 復習コンテンツを生成
        review_contents = generate_review_contents(
            summary=summary,
            requested_topic=request.topic
        )
        
        response = ReviewResponse(
            summary=summary,
            review_contents=review_contents
        )
        
        logger.info(
            f"[{AGENT_NAME}] 復習コンテンツ生成完了: "
            f"要約トピック={len(summary.recent_topics)}件, "
            f"復習コンテンツ={len(review_contents)}件"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"[{AGENT_NAME}] 復習コンテンツ生成中にエラーが発生: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"復習コンテンツ生成中にエラーが発生しました: {str(e)}"
        )


@router.post("/feedback")
async def provide_feedback():
    """学習フィードバックを提供（プレースホルダー）"""
    return {"message": "Feedback endpoint - to be implemented"}
