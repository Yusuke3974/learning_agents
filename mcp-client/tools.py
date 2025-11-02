"""MCPツール実装

各MCPツールの実装とモックレスポンスを定義します。
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 親ディレクトリをパスに追加して、mcp_clientモジュールをインポート可能にする
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 相対インポートを使用（mcp-clientディレクトリ内のモジュール）
try:
    from mcp_client.client import MCPClient
except ImportError:
    # フォールバック: 相対インポートを使用
    from .client import MCPClient

# ロギング設定
logger = logging.getLogger(__name__)

# グローバルMCPクライアントインスタンス
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """MCPクライアントインスタンスを取得
    
    Returns:
        MCPクライアントインスタンス
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def call_dictionary(word: str, language: str = "en") -> Dict[str, Any]:
    """英単語定義を取得する（MCP経由）
    
    Args:
        word: 単語
        language: 言語（デフォルト: "en"）
        
    Returns:
        単語の定義情報
    """
    logger.info(f"[MCP] dictionary呼び出し: word={word}, language={language}")
    
    client = get_mcp_client()
    arguments = {"word": word, "language": language}
    
    result = await client.call_tool("dictionary", arguments, use_mock=True)
    
    # モックレスポンスを生成（実際のMCP実装時は不要）
    if result.get("mock"):
        result = _mock_dictionary(word, language)
    
    logger.info(f"[MCP] dictionary結果: word={word}, result={result.get('status')}")
    return result


async def call_code_explainer(code: str, language: str = "python") -> Dict[str, Any]:
    """コードスニペットの解説を取得する（MCP経由）
    
    Args:
        code: コードスニペット
        language: プログラミング言語（デフォルト: "python"）
        
    Returns:
        コードの解説
    """
    logger.info(
        f"[MCP] code_explainer呼び出し: language={language}, "
        f"code_length={len(code)}"
    )
    
    client = get_mcp_client()
    arguments = {"code": code, "language": language}
    
    result = await client.call_tool("code_explainer", arguments, use_mock=True)
    
    # モックレスポンスを生成（実際のMCP実装時は不要）
    if result.get("mock"):
        result = _mock_code_explainer(code, language)
    
    logger.info(f"[MCP] code_explainer結果: language={language}, result={result.get('status')}")
    return result


async def call_past_notes(
    user_id: str,
    topic: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """過去のノートを取得する（MCP経由）
    
    Args:
        user_id: ユーザーID
        topic: トピック（オプション、フィルタリング用）
        limit: 取得件数（デフォルト: 10）
        
    Returns:
        過去のノートリスト
    """
    logger.info(
        f"[MCP] past_notes呼び出し: user_id={user_id}, topic={topic}, limit={limit}"
    )
    
    client = get_mcp_client()
    arguments = {
        "user_id": user_id,
        "topic": topic,
        "limit": limit
    }
    
    result = await client.call_tool("past_notes", arguments, use_mock=True)
    
    # モックレスポンスを生成（実際のMCP実装時は不要）
    if result.get("mock"):
        result = _mock_past_notes(user_id, topic, limit)
    
    logger.info(
        f"[MCP] past_notes結果: user_id={user_id}, "
        f"notes_count={len(result.get('notes', []))}"
    )
    return result


def _mock_dictionary(word: str, language: str) -> Dict[str, Any]:
    """dictionaryツールのモックレスポンス
    
    Args:
        word: 単語
        language: 言語
        
    Returns:
        モックレスポンス
    """
    logger.debug(f"[MCP] モックdictionaryレスポンス生成: word={word}")
    
    # モックデータ
    mock_definitions = {
        "decorator": {
            "word": "decorator",
            "definitions": [
                "A function that modifies another function or class",
                "In Python, a decorator is a design pattern that allows you to wrap a function or method"
            ],
            "examples": [
                "The @property decorator makes a method accessible like an attribute",
                "Function decorators are commonly used for logging or authentication"
            ]
        },
        "comprehension": {
            "word": "comprehension",
            "definitions": [
                "A concise way to create lists, dictionaries, or sets in Python",
                "A syntactic construct that creates a collection from an iterable"
            ],
            "examples": [
                "List comprehension: [x**2 for x in range(10)]",
                "Dictionary comprehension: {k: v for k, v in items}"
            ]
        },
        "article": {
            "word": "article",
            "definitions": [
                "A word (a, an, the) used before nouns to specify grammatical definiteness",
                "In English, articles are used to indicate whether a noun is specific or general"
            ],
            "examples": [
                "Use 'a' before consonant sounds: a cat, a university",
                "Use 'an' before vowel sounds: an apple, an hour",
                "Use 'the' for specific nouns: the cat I saw yesterday"
            ]
        }
    }
    
    word_lower = word.lower()
    if word_lower in mock_definitions:
        definition_data = mock_definitions[word_lower]
    else:
        definition_data = {
            "word": word,
            "definitions": [
                f"A word meaning '{word}' (definition will be provided by actual dictionary API)"
            ],
            "examples": []
        }
    
    return {
        "tool": "dictionary",
        "status": "success",
        "data": definition_data,
        "message": f"Definition retrieved for '{word}'",
        "mock": True
    }


def _mock_code_explainer(code: str, language: str) -> Dict[str, Any]:
    """code_explainerツールのモックレスポンス
    
    Args:
        code: コードスニペット
        language: プログラミング言語
        
    Returns:
        モックレスポンス
    """
    logger.debug(f"[MCP] モックcode_explainerレスポンス生成: language={language}")
    
    # コードの簡易分析
    lines = code.split('\n')
    num_lines = len(lines)
    
    # モック解説
    explanation = f"""
このコードは{language}で書かれています。
行数: {num_lines}行

【主な機能】
- コードの機能についての説明
- 重要な概念やパターン
- 使用例やベストプラクティス

【詳細解説】
（実際のMCP実装時は、実際のコード解析結果が返されます）
"""
    
    return {
        "tool": "code_explainer",
        "status": "success",
        "data": {
            "language": language,
            "explanation": explanation.strip(),
            "summary": f"{language}コードの解説（{num_lines}行）",
            "concepts": [],
            "examples": []
        },
        "message": f"Code explanation generated for {language} code",
        "mock": True
    }


def _mock_past_notes(
    user_id: str,
    topic: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """past_notesツールのモックレスポンス
    
    Args:
        user_id: ユーザーID
        topic: トピック（オプション）
        limit: 取得件数
        
    Returns:
        モックレスポンス
    """
    logger.debug(
        f"[MCP] モックpast_notesレスポンス生成: user_id={user_id}, "
        f"topic={topic}, limit={limit}"
    )
    
    # モックノートデータ
    mock_notes = [
        {
            "id": "note_1",
            "user_id": user_id,
            "topic": "Python decorators",
            "content": "デコレータは関数を拡張するためのパターンです。@記号を使って関数を修飾します。",
            "created_at": "2025-11-01T10:00:00Z",
            "tags": ["Python", "デコレータ", "関数"]
        },
        {
            "id": "note_2",
            "user_id": user_id,
            "topic": "English articles",
            "content": "冠詞の使い分け：a/anは不定冠詞、theは定冠詞。初出はa/an、既出はthe。",
            "created_at": "2025-11-02T14:30:00Z",
            "tags": ["英語", "冠詞", "文法"]
        },
        {
            "id": "note_3",
            "user_id": user_id,
            "topic": "Python list comprehensions",
            "content": "リスト内包表記は [式 for 要素 in イテラブル] の形式。if句でフィルタリングも可能。",
            "created_at": "2025-11-03T09:15:00Z",
            "tags": ["Python", "リスト", "内包表記"]
        }
    ]
    
    # トピックでフィルタリング
    if topic:
        filtered_notes = [
            note for note in mock_notes
            if topic.lower() in note["topic"].lower()
        ]
    else:
        filtered_notes = mock_notes
    
    # 件数制限
    notes = filtered_notes[:limit]
    
    return {
        "tool": "past_notes",
        "status": "success",
        "data": {
            "user_id": user_id,
            "topic": topic,
            "notes": notes,
            "count": len(notes),
            "total_count": len(filtered_notes)
        },
        "message": f"Retrieved {len(notes)} notes for user {user_id}",
        "mock": True
    }

