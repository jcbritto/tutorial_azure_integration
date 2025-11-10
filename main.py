from fastapi import FastAPI

app = FastAPI(
    title="Tutorial Azure Integration API",
    description="API básica para o tutorial de integração com o Azure."
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
