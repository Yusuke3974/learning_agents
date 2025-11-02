"""FastAPI アプリケーションのメインエントリーポイント"""
from fastapi import FastAPI
from agents.teacher_agent import router as teacher_router
from agents.quiz_agent import router as quiz_router
from agents.review_agent import router as review_router

app = FastAPI(
    title="Learning Agents API",
    description="AIエージェントベースの学習システム",
    version="0.1.0",
)

# エージェントルーターを登録
app.include_router(teacher_router)
app.include_router(quiz_router)
app.include_router(review_router)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Learning Agents API",
        "status": "running",
        "endpoints": {
            "teacher": "/teacher",
            "quiz": "/quiz",
            "review": "/review",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

