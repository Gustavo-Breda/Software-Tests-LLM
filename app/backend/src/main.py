from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Pipeline de QA Assistant - Backend rodando!"}
