"""A2A（Agent-to-Agent）通信プロトコル

すべてのエージェント間通信を統一形式で管理します。
"""
import logging
import os
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

# ロギング設定
logger = logging.getLogger(__name__)

# 内部APIのベースURL（環境変数で設定可能、デフォルトはローカル）
INTERNAL_API_BASE_URL = os.getenv("INTERNAL_API_BASE_URL", "http://localhost:8000")


class TaskMessage(BaseModel):
    """A2Aタスクメッセージ
    
    すべてのエージェント間通信はこの形式を使用します。
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="タスクの一意ID")
    sender: str = Field(..., description="送信元エージェント名")
    receiver: str = Field(..., description="受信先エージェント名")
    message: Dict[str, Any] = Field(..., description="タスクの詳細メッセージ（エージェント固有のデータ）")
    timestamp: Optional[str] = None


async def send_task(endpoint: str, message: TaskMessage) -> Dict[str, Any]:
    """A2A形式でタスクを送信する
    
    Args:
        endpoint: 送信先エンドポイント（例: "/quiz/generate-quiz"）
        message: タスクメッセージ
        
    Returns:
        受信先エージェントからのレスポンス
        
    Raises:
        HTTPException: 通信エラーが発生した場合
    """
    url = f"{INTERNAL_API_BASE_URL}{endpoint}"
    
    # メッセージをJSONに変換
    payload = message.model_dump()
    
    logger.info(
        f"[A2A] タスク送信: task_id={message.task_id}, "
        f"sender={message.sender} -> receiver={message.receiver}, "
        f"endpoint={endpoint}"
    )
    logger.debug(f"[A2A] タスクペイロード: {payload}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                f"[A2A] タスク受信完了: task_id={message.task_id}, "
                f"receiver={message.receiver} -> sender={message.sender}"
            )
            logger.debug(f"[A2A] タスクレスポンス: {result}")
            
            return result
            
    except httpx.TimeoutException as e:
        logger.error(
            f"[A2A] タイムアウト: task_id={message.task_id}, "
            f"sender={message.sender} -> receiver={message.receiver}, "
            f"endpoint={endpoint}, error={str(e)}"
        )
        raise HTTPException(
            status_code=504,
            detail=f"エージェント通信がタイムアウトしました: {message.receiver}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"[A2A] HTTPエラー: task_id={message.task_id}, "
            f"sender={message.sender} -> receiver={message.receiver}, "
            f"endpoint={endpoint}, status={e.response.status_code}, "
            f"error={str(e)}"
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"エージェント通信エラー: {message.receiver} ({e.response.status_code})"
        )
    except httpx.HTTPError as e:
        logger.error(
            f"[A2A] 通信エラー: task_id={message.task_id}, "
            f"sender={message.sender} -> receiver={message.receiver}, "
            f"endpoint={endpoint}, error={str(e)}"
        )
        raise HTTPException(
            status_code=503,
            detail=f"エージェント通信に失敗しました: {message.receiver} ({str(e)})"
        )
    except Exception as e:
        logger.error(
            f"[A2A] 予期しないエラー: task_id={message.task_id}, "
            f"sender={message.sender} -> receiver={message.receiver}, "
            f"endpoint={endpoint}, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"エージェント通信で予期しないエラーが発生しました: {str(e)}"
        )


def create_task_message(
    sender: str,
    receiver: str,
    message: Dict[str, Any],
    task_id: Optional[str] = None
) -> TaskMessage:
    """A2Aタスクメッセージを作成するヘルパー関数
    
    Args:
        sender: 送信元エージェント名
        receiver: 受信先エージェント名
        message: タスクの詳細メッセージ
        task_id: タスクID（指定しない場合は自動生成）
        
    Returns:
        タスクメッセージ
    """
    return TaskMessage(
        task_id=task_id or str(uuid.uuid4()),
        sender=sender,
        receiver=receiver,
        message=message
    )

