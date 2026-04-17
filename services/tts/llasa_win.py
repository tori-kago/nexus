import torch
import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from xcodec2.modeling_xcodec2 import XCodec2Model
import uuid
import os
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLaSA-Windows")

app = FastAPI(title="Nexus LLaSA TTS Service (Windows/CUDA)")

# --- 配置 ---
MODEL_ID = "HKUSTAudio/LLaSA-3B"
CODEC_ID = "HKUSTAudio/xcodec2"

# Windows/CUDA 設備檢測
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    logger.info(f"✅ 檢測到 NVIDIA GPU: {torch.cuda.get_device_name(0)}")
else:
    DEVICE = torch.device("cpu")
    logger.warning("⚠️ 未檢測到 CUDA，將使用 CPU 運行")

OUTPUT_DIR = "temp_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 模型載入 ---
logger.info(f"[*] 正在載入 LLaSA-3B 模型 (使用 CUDA/FP16)...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# Windows 下 CUDA 支持良好，直接使用 FP16 與 auto 映射
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, 
    torch_dtype=torch.float16, 
    device_map="auto"
)

logger.info(f"[*] 正在載入 XCodec2 編碼器...")
codec_model = XCodec2Model.from_pretrained(CODEC_ID)
codec_model.to(DEVICE)
codec_model.eval()

class TTSRequest(BaseModel):
    text: str
    prompt_text: str = ""
    prompt_wav_path: str = ""

@app.post("/tts")
async def generate_tts(req: TTSRequest):
    try:
        logger.info(f"🎤 收到請求: {req.text[:30]}...")
        
        # 1. 格式化 Prompt
        input_text = f"<|user|>\n{req.prompt_text} {req.text}\n<|assistant|>\n"
        
        # 2. Tokenize
        inputs = tokenizer(input_text, return_tensors="pt").to(DEVICE)
        
        # 3. 推理生成
        with torch.no_grad():
            output_tokens = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.8,
                top_p=0.95
            )
        
        # 4. 截取生成的音訊 Token
        gen_tokens = output_tokens[0][inputs['input_ids'].shape[1]:]
        
        # 5. XCodec2 解碼
        audio_waveform = codec_model.decode(gen_tokens.unsqueeze(0))
        
        # 6. 儲存檔案
        file_id = str(uuid.uuid4())
        file_path = os.path.join(OUTPUT_DIR, f"{file_id}.wav")
        
        audio_data = audio_waveform[0].cpu().numpy()
        sf.write(file_path, audio_data, 16000)
        
        abs_path = os.path.abspath(file_path)
        logger.info(f"✅ 生成成功: {abs_path}")
        
        return {
            "status": "success", 
            "url": abs_path, 
            "trace_id": file_id
        }

    except Exception as e:
        logger.error(f"❌ 生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Windows 下建議明確指定 0.0.0.0 方便區域網路調用
    uvicorn.run(app, host="0.0.0.0", port=9001)
