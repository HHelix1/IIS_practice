# app_simple.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API работает!"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/test")
def test(data: dict):
    return {"received": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")