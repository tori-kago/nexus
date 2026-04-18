from pydub import AudioSegment
import os
import sys

def trim_audio(input_path, output_path, start_sec=0, end_sec=20):
    """
    將音檔切分出指定片段
    """
    if not os.path.exists(input_path):
        print(f"❌ 找不到原始音檔: {input_path}")
        return

    print(f"✂️ 正在讀取音檔: {input_path}")
    audio = AudioSegment.from_file(input_path)
    
    # pydub 使用毫秒 (ms)
    start_ms = start_sec * 1000
    end_ms = end_sec * 1000
    
    trimmed = audio[start_ms:end_ms]
    
    print(f"💾 正在儲存切片至: {output_path} ({start_sec}s -> {end_sec}s)")
    trimmed.export(output_path, format="wav")
    print("✅ 切分完成！")

if __name__ == "__main__":
    # 預設參數，你可以根據需要修改
    # 假設你的原始長音檔放在 reference_audio/long_audio.wav
    source = "test_ref.wav" 
    target = "test_ref_7.wav"
    
    # 如果有提供命令行參數
    if len(sys.argv) > 1:
        source = sys.argv[1]
    
    if os.path.exists(source):
        trim_audio(source, target, start_sec=0, end_sec=7)
    else:
        print(f"💡 請將你的 3 分鐘音檔放在 {source}")
        print(f"或者執行: python services/tts/trim_audio.py <你的音檔路徑>")
