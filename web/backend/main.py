from fastapi import FastAPI

app = FastAPI(
    title="Dormitory Laundry API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {"message": "Welcome to Dormitory Laundry"}


@app.get("/health")
def health():
    return {"status": "ok"}