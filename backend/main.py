from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return "Nothing to find here!"