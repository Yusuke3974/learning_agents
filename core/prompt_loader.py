"""プロンプトローダー

エージェントのプロンプトテンプレートを読み込む共通モジュール
"""
import logging
from pathlib import Path
from typing import Optional

# ロギング設定
logger = logging.getLogger(__name__)

# プロンプトファイルのベースディレクトリ
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(agent_name: str) -> Optional[str]:
    """エージェントのプロンプトファイルを読み込む
    
    Args:
        agent_name: エージェント名（例: "teacher", "quiz", "review"）
        
    Returns:
        プロンプトテキスト（読み込めない場合はNone）
    """
    prompt_file = PROMPTS_DIR / f"{agent_name}_prompt.txt"
    
    try:
        if not prompt_file.exists():
            logger.warning(f"プロンプトファイルが見つかりません: {prompt_file}")
            return None
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()
        
        logger.info(f"プロンプトを読み込みました: {agent_name} ({len(prompt_text)}文字)")
        return prompt_text
        
    except Exception as e:
        logger.error(f"プロンプト読み込みエラー: {agent_name}, error={str(e)}", exc_info=True)
        return None


def get_prompt(agent_name: str) -> str:
    """エージェントのプロンプトを取得する（フォールバック付き）
    
    Args:
        agent_name: エージェント名
        
    Returns:
        プロンプトテキスト（読み込めない場合はデフォルトメッセージ）
    """
    prompt = load_prompt(agent_name)
    if prompt:
        return prompt
    
    # フォールバック: デフォルトメッセージ
    logger.warning(f"プロンプトが読み込めませんでした。デフォルトメッセージを使用: {agent_name}")
    return f"あなたは{agent_name}エージェントです。学習者のサポートを行います。"

