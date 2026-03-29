from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Automotive24 API werkt!"}

handler = Mangum(app)
