from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import traceback
from openvoice_engine import engine

app = FastAPI(title="CalmChat TTS Service (OpenVoice V2)")


class RegisterRequest(BaseModel):
    sample_audio_path: str


class SynthesizeRequest(BaseModel):
    text: str
    embedding_path: str


@app.post("/register")
def register_voice(payload: RegisterRequest):
    try:
        embedding_path = engine.extract_embedding(payload.sample_audio_path)
    except Exception as e:
        traceback.print_exc()
        raise

    return {"embedding_path": embedding_path}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest):
    try:
        audio_bytes = engine.synthesize(payload.text, payload.embedding_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"합성 실패: {e}")

    return Response(content=audio_bytes, media_type="audio/wav")


@app.get("/health")
def health():
    return {"status": "ok"}