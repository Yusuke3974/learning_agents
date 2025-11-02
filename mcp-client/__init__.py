"""MCP（Model Context Protocol）クライアント

エージェントからMCPサーバーへの接続とツール呼び出しを管理します。
"""

from mcp_client.client import MCPClient
from mcp_client.tools import (
    call_code_explainer,
    call_dictionary,
    call_past_notes,
)

__all__ = [
    "MCPClient",
    "call_dictionary",
    "call_code_explainer",
    "call_past_notes",
]

# 注: `mcp-client`ディレクトリ名をPythonモジュールとして使用する場合、
# インポートパスは環境に応じて調整が必要です。
# 実際のMCP SDK統合時には、パッケージ構造を再検討してください。

