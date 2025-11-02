# learning_agents

AIエージェントベースの学習システム

## プロジェクト構成

```
learning_agents/
├── agents/          # AIエージェント（Teacher, Quiz, Review）
├── core/            # 共通ロジック（A2A通信、MCP処理）
├── frontend/        # Streamlit UI
├── mcp-client/      # MCPクライアント
├── data/            # データディレクトリ
│   └── learning_logs/  # 学習ログ
└── main.py          # FastAPIサーバー
```

## セットアップ

### 依存関係のインストール

```bash
uv sync
```

### 環境変数（オプション）

```bash
# OpenAI APIキー（説明機能を使用する場合）
export OPENAI_API_KEY=your_api_key_here

# APIベースURL（デフォルト: http://localhost:8000）
export API_BASE_URL=http://localhost:8000
```

## 使用方法

### 1. FastAPIサーバーの起動

```bash
# 方法1: main.pyから直接起動
uv run python main.py

# 方法2: uvicornを使用
uv run uvicorn main:app --reload
```

サーバーは `http://localhost:8000` で起動します。

### 2. Streamlit UIの起動

別のターミナルで：

```bash
uv run streamlit run frontend/app.py
```

ブラウザで `http://localhost:8501` にアクセスします。

## 機能

### エージェント

- **TeacherAgent**: 質問の種類を分類し、適切なエージェントに転送
  - `/teacher/ask` (POST): 質問を受け取り、種類に応じて処理

- **QuizAgent**: クイズの生成と評価
  - `/quiz/generate-quiz` (POST): クイズを生成

- **ReviewAgent**: 学習内容の復習とフィードバック
  - `/review/review` (POST): 復習コンテンツを提供

### A2A通信

すべてのエージェント間通信はA2A（Agent-to-Agent）形式で統一されています。

- `core/a2a.py`: A2A通信基盤
- `TaskMessage`: 統一されたタスクメッセージ形式

### MCP統合

MCP（Model Context Protocol）クライアントが実装されています。

- `dictionary`: 英単語定義取得
- `code_explainer`: コードスニペットの解説
- `past_notes`: 過去ノート取得

### UI機能

- チャット形式で質問を入力
- 「練習する」「復習する」ボタン
- クイズの表示と回答
- 回答後の正誤判定と解説

## APIエンドポイント

### TeacherAgent

- `GET /teacher/`: ステータス確認
- `POST /teacher/ask`: 質問を受け取り、種類に応じて処理

### QuizAgent

- `GET /quiz/`: ステータス確認
- `POST /quiz/generate-quiz`: クイズを生成（A2A形式）

### ReviewAgent

- `GET /review/`: ステータス確認
- `POST /review/review`: 復習コンテンツを提供（A2A形式）

## 動作確認方法

### 1. APIサーバーの起動確認

サーバーを起動後、以下でステータスを確認できます：

```bash
# ルートエンドポイント
curl http://localhost:8000/

# 各エージェントのステータス確認
curl http://localhost:8000/teacher/
curl http://localhost:8000/quiz/
curl http://localhost:8000/review/
```

### 2. TeacherAgentの動作確認

#### 説明依頼のテスト

```bash
curl -X POST http://localhost:8000/teacher/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Pythonのデコレータを説明して",
    "topic": "Python decorators"
  }'
```

#### 練習問題依頼のテスト

```bash
curl -X POST http://localhost:8000/teacher/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "英語の冠詞の練習問題を出して",
    "topic": "English articles",
    "subject": "英語"
  }'
```

#### 復習依頼のテスト

```bash
curl -X POST http://localhost:8000/teacher/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "前回の内容を復習したい",
    "topic": "Python decorators"
  }'
```

### 3. QuizAgentの動作確認（A2A形式）

```bash
curl -X POST http://localhost:8000/quiz/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-123",
    "sender": "test",
    "receiver": "quiz",
    "message": {
      "topic": "Python decorators",
      "level": "intermediate",
      "question_type": "multiple_choice"
    }
  }'
```

### 4. ReviewAgentの動作確認（A2A形式）

```bash
curl -X POST http://localhost:8000/review/review \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-456",
    "sender": "test",
    "receiver": "review",
    "message": {
      "user_id": "default_user",
      "topic": "Python decorators"
    }
  }'
```

### 5. Streamlit UIでの動作確認

1. **サーバーとUIの起動**
   ```bash
   # ターミナル1: APIサーバー
   uv run uvicorn main:app --reload
   
   # ターミナル2: Streamlit UI
   uv run streamlit run frontend/app.py
   ```

2. **ブラウザで `http://localhost:8501` にアクセス**

3. **基本的な操作**
   - **チャット入力**: 画面下部のテキストボックスに質問を入力
   - **練習するボタン**: クイックアクションから「📝 練習する」をクリック
   - **復習するボタン**: クイックアクションから「🔄 復習する」をクリック

4. **クイズの操作**
   - クイズが表示されたら、各問題のラジオボタンで回答を選択
   - 「✅ 回答を提出」ボタンをクリック
   - 結果画面で正誤判定と詳細を確認
   - 「🔄 新しいクイズを開始」でリセット

5. **テストケース例**
   - 説明依頼: 「Pythonのリスト内包表記を説明して」
   - 練習依頼: 「英語の前置詞の練習問題を出して」
   - 復習依頼: 「前回学習した内容を復習したい」

### 6. エージェント定義の確認

```bash
# エージェント定義ファイルの確認
cat .well-known/agent.json

# プロンプトファイルの確認
cat prompts/teacher_prompt.txt
cat prompts/quiz_prompt.txt
cat prompts/review_prompt.txt
```

### 7. ログの確認

すべてのエージェント間通信とMCP呼び出しはログに記録されます：

```bash
# APIサーバーのログを確認
# ターミナルで以下のようなログが出力されます：
# [A2A] タスク送信: task_id=xxx, sender=teacher -> receiver=quiz
# [quiz] A2Aタスク受信: task_id=xxx, sender=teacher, receiver=quiz
# [MCP] past_notes呼び出し: user_id=default_user
```

### 8. FastAPI自動ドキュメント

ブラウザで以下のURLにアクセスしてAPIドキュメントを確認：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 開発

### テスト

```bash
# APIサーバーを起動
uv run uvicorn main:app --reload

# 別のターミナルでStreamlit UIを起動
uv run streamlit run frontend/app.py
```

### ログ

すべてのエージェント間通信とMCP呼び出しはログに記録されます。

## 将来の拡張

- 実際のMCP SDKとの統合
- データベースとの統合（現在はモックデータ）
- より高度なUI機能
- マルチユーザー対応
