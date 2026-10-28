from fastapi import FastAPI

app = FastAPI(title="Attendance Manager API")

@app.get("/")
def home():
    return {"message": "Attendance Manager API is running"}