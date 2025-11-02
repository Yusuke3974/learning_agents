"""クイズエージェント - クイズの生成と評価を行う"""
import json
import logging
import os
import random
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.a2a import TaskMessage
from core.prompt_loader import get_prompt

# ロギング設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])

# エージェント名
AGENT_NAME = "quiz"

# プロンプトを読み込む（起動時に1回だけ実行）
AGENT_PROMPT = get_prompt(AGENT_NAME)
logger.info(f"[{AGENT_NAME}] エージェントプロンプトを読み込みました（{len(AGENT_PROMPT) if AGENT_PROMPT else 0}文字）")


class QuestionOption(BaseModel):
    """クイズの選択肢"""
    option: str
    is_correct: bool


class Question(BaseModel):
    """クイズの問題"""
    question: str
    options: List[str]
    answer: str


class GenerateQuizRequest(BaseModel):
    """クイズ生成リクエスト"""
    topic: str
    level: Optional[str] = "intermediate"
    question_type: Optional[str] = "multiple_choice"


class GenerateQuizResponse(BaseModel):
    """クイズ生成レスポンス"""
    questions: List[Question]


async def generate_quiz_with_openai(
    topic: str,
    level: str,
    question_type: str
) -> GenerateQuizResponse:
    """OpenAI APIを使ってクイズを生成する
    
    Args:
        topic: トピック
        level: レベル（beginner, intermediate, advanced）
        question_type: 問題タイプ（multiple_choice, true_false等）
        
    Returns:
        生成されたクイズ
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        logger.warning("OPENAI_API_KEYが設定されていません。ダミー回答を返します。")
        return generate_fallback_quiz(topic, level, question_type)
    
    try:
        import openai
        
        logger.info(f"OpenAI APIを使用してクイズを生成: topic={topic}, level={level}, type={question_type}")
        
        client = openai.AsyncOpenAI(api_key=openai_api_key)
        
        # 問題数をランダムに決定（1〜3問）
        num_questions = random.randint(1, 3)
        
        # システムプロンプトで出力形式を指定して安定性を保つ
        # エージェントプロンプトをベースに、JSON形式の指示を追加
        base_prompt = AGENT_PROMPT if AGENT_PROMPT else "あなたは優秀なクイズ作成者です。"
        
        system_prompt = f"""{base_prompt}

指定されたトピック、難易度、問題タイプに基づいて、
以下のJSON形式でクイズを生成してください。

形式:
{
  "questions": [
    {
      "question": "問題文",
      "options": ["選択肢1", "選択肢2", "選択肢3", "選択肢4"],
      "answer": "正解の選択肢"
    }
  ]
}

重要:
- 選択肢は4つにしてください
- answerフィールドには、正解の選択肢のテキストをそのまま記載してください
- 選択肢の順序はランダムにしてください
- 問題は実践的で理解を深められる内容にしてください
- JSONのみを返答し、余計な説明は不要です"""

        user_prompt = f"""トピック: {topic}
難易度: {level}
問題タイプ: {question_type}
問題数: {num_questions}問

上記の条件でクイズを生成してください。"""

        # JSON形式での出力を強制
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        answer_text = response.choices[0].message.content
        
        logger.info(f"OpenAI APIからの応答: {len(answer_text)}文字")
        
        # JSONパース
        try:
            quiz_data = json.loads(answer_text)
            questions_data = quiz_data.get("questions", [])
            
            # データ検証と変換
            questions = []
            for q_data in questions_data:
                question = Question(
                    question=q_data.get("question", ""),
                    options=q_data.get("options", []),
                    answer=q_data.get("answer", "")
                )
                questions.append(question)
            
            if not questions:
                logger.warning("生成されたクイズが空でした。フェールバックを使用します。")
                return generate_fallback_quiz(topic, level, question_type)
            
            logger.info(f"クイズ生成完了: {len(questions)}問")
            return GenerateQuizResponse(questions=questions)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSONパースエラー: {e}, レスポンス: {answer_text}")
            # JSONパースに失敗した場合はフェールバック
            return generate_fallback_quiz(topic, level, question_type)
            
    except ImportError:
        logger.warning("openaiパッケージがインストールされていません。ダミー回答を返します。")
        return generate_fallback_quiz(topic, level, question_type)
    except Exception as e:
        logger.error(f"OpenAI API呼び出しエラー: {e}")
        return generate_fallback_quiz(topic, level, question_type)


def generate_fallback_quiz(
    topic: str,
    level: str,
    question_type: str
) -> GenerateQuizResponse:
    """フェールバック：ダミークイズを生成する
    
    Args:
        topic: トピック
        level: レベル
        question_type: 問題タイプ
        
    Returns:
        ダミークイズ
    """
    logger.info(f"フェールバック：ダミークイズを生成: topic={topic}")
    
    # ダミークイズのテンプレート
    dummy_questions = [
        Question(
            question=f"{topic}について、基本的な概念は何ですか？",
            options=[
                "概念A",
                "概念B",
                "概念C（正解）",
                "概念D"
            ],
            answer="概念C（正解）"
        ),
        Question(
            question=f"{topic}を使用する際の注意点は？",
            options=[
                "注意点1",
                "注意点2（正解）",
                "注意点3",
                "注意点4"
            ],
            answer="注意点2（正解）"
        )
    ]
    
    # ランダムに1〜2問を選択
    num_questions = random.randint(1, 2)
    selected_questions = random.sample(dummy_questions, min(num_questions, len(dummy_questions)))
    
    return GenerateQuizResponse(questions=selected_questions)


@router.get("/")
async def quiz_root():
    """クイズエージェントのルートエンドポイント"""
    return {"agent": "quiz", "status": "ready"}


@router.post("/generate")
async def generate_quiz():
    """クイズを生成（プレースホルダー）"""
    return {"message": "Quiz generation endpoint - to be implemented"}


@router.post("/generate-quiz")
async def generate_quiz_from_request_a2a(task_message: TaskMessage) -> dict:
    """クイズを生成するエンドポイント（A2A形式）
    
    A2A形式のTaskMessageを受け取り、クイズを生成します。
    TaskMessage.messageには以下のフィールドが含まれます:
    - topic: トピック（必須）
    - level: レベル（オプション、デフォルト: "intermediate"）
    - question_type: 問題タイプ（オプション、デフォルト: "multiple_choice"）
    """
    logger.info(
        f"[{AGENT_NAME}] A2Aタスク受信: task_id={task_message.task_id}, "
        f"sender={task_message.sender}, receiver={task_message.receiver}"
    )
    logger.debug(f"[{AGENT_NAME}] タスクメッセージ: {task_message.message}")
    
    try:
        # TaskMessage.messageからリクエストパラメータを取得
        message = task_message.message
        topic = message.get("topic", "")
        level = message.get("level", "intermediate")
        question_type = message.get("question_type", "multiple_choice")
        
        if not topic:
            logger.error(f"[{AGENT_NAME}] トピックが指定されていません: task_id={task_message.task_id}")
            raise HTTPException(
                status_code=400,
                detail="topicフィールドが必要です"
            )
        
        logger.info(
            f"[{AGENT_NAME}] クイズ生成開始: task_id={task_message.task_id}, "
            f"topic={topic}, level={level}, type={question_type}"
        )
        
        # OpenAI APIを使ってクイズを生成
        result = await generate_quiz_with_openai(
            topic=topic,
            level=level,
            question_type=question_type
        )
        
        logger.info(
            f"[{AGENT_NAME}] クイズ生成完了: task_id={task_message.task_id}, "
            f"questions={len(result.questions)}問"
        )
        
        # A2A形式のレスポンスを返す
        return {
            "task_id": task_message.task_id,
            "sender": AGENT_NAME,
            "receiver": task_message.sender,
            "result": result.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{AGENT_NAME}] クイズ生成中にエラーが発生: task_id={task_message.task_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"クイズ生成中にエラーが発生しました: {str(e)}"
        )


@router.post("/generate-quiz-legacy", response_model=GenerateQuizResponse)
async def generate_quiz_from_request(request: GenerateQuizRequest) -> GenerateQuizResponse:
    """クイズを生成するエンドポイント（レガシー形式、後方互換性のため）
    
    リクエスト例:
    {
        "topic": "Python decorators",
        "level": "intermediate",
        "question_type": "multiple_choice"
    }
    """
    logger.info(
        f"[{AGENT_NAME}] レガシー形式のクイズ生成リクエスト受信: "
        f"topic={request.topic}, level={request.level}, type={request.question_type}"
    )
    
    try:
        # OpenAI APIを使ってクイズを生成
        result = await generate_quiz_with_openai(
            topic=request.topic,
            level=request.level or "intermediate",
            question_type=request.question_type or "multiple_choice"
        )
        
        logger.info(f"[{AGENT_NAME}] クイズ生成完了: {len(result.questions)}問")
        return result
        
    except Exception as e:
        logger.error(f"[{AGENT_NAME}] クイズ生成中にエラーが発生: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"クイズ生成中にエラーが発生しました: {str(e)}"
        )


@router.post("/evaluate")
async def evaluate_answer():
    """回答を評価（プレースホルダー）"""
    return {"message": "Answer evaluation endpoint - to be implemented"}
