"""Озвучка сценария: чередуем два голоса (псевдо-два-ведущих) и склеиваем в один MP3.

Провайдеры: AWS Polly (по умолчанию), ttsmp3.com (запасной).
Требует ffmpeg в системе (pydub его использует). В GitHub Actions ставим через apt.
"""
import io
import os
import tempfile
from . import config

try:
    from pydub import AudioSegment
except Exception:  # pydub может отсутствовать при статической проверке
    AudioSegment = None


def _voice_for(speaker, provider):
    if provider == "polly":
        return {
            "A": config.POLLY_VOICE_A, "B": config.POLLY_VOICE_B,
            "G": config.POLLY_VOICE_G, "E": config.POLLY_VOICE_E,
        }.get(speaker, config.POLLY_VOICE_A)
    if provider == "gtts":
        # для gTTS "голос" = tld (акцент)
        return {
            "A": config.GTTS_TLD_A, "B": config.GTTS_TLD_B,
            "G": config.GTTS_TLD_G, "E": config.GTTS_TLD_E,
        }.get(speaker, config.GTTS_TLD_A)
    return {
        "A": config.TTSMP3_VOICE_A, "B": config.TTSMP3_VOICE_B,
        "G": config.TTSMP3_VOICE_G, "E": config.TTSMP3_VOICE_E,
    }.get(speaker, config.TTSMP3_VOICE_A)


# ---------- gTTS (бесплатно, без ключа) ----------

# Лёгкий сдвиг высоты по ролям, чтобы 4 "ведущих" отличались (gTTS — один голос).
_GTTS_PITCH = {"A": 0.5, "B": -1.5, "G": -2.5, "E": 1.5}


def _gtts_segment(text, tld):
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang=config.GTTS_LANG, tld=tld, slow=False).write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def _pitch_shift(seg, semitones):
    if not semitones:
        return seg
    new_rate = int(seg.frame_rate * (2.0 ** (semitones / 12.0)))
    shifted = seg._spawn(seg.raw_data, overrides={"frame_rate": new_rate})
    return shifted.set_frame_rate(seg.frame_rate)


# ---------- Polly ----------

def _polly_client():
    import boto3
    return boto3.client(
        "polly",
        aws_access_key_id=config.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY or None,
        region_name=config.AWS_REGION,
    )


def _polly_segment(client, text, voice):
    resp = client.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=voice,
        Engine=config.POLLY_ENGINE,
    )
    return resp["AudioStream"].read()


# ---------- ttsmp3.com ----------

def _ttsmp3_segment(text, voice):
    import requests
    # У ttsmp3 есть форма/эндпоинт; для автоматизации нужен платный API-ключ.
    data = {"msg": text, "lang": voice, "source": "api"}
    if config.TTSMP3_API_KEY:
        data["apikey"] = config.TTSMP3_API_KEY
    r = requests.post("https://ttsmp3.com/makemp3_new.php", data=data, timeout=60)
    r.raise_for_status()
    url = r.json().get("URL")
    if not url:
        raise RuntimeError(f"ttsmp3 не вернул URL: {r.text[:200]}")
    audio = requests.get(url, timeout=60)
    audio.raise_for_status()
    return audio.content


# ---------- Общая сборка ----------

def synthesize(lines, out_path):
    """lines: [{'speaker','text'}]; сохраняет склеенный MP3 в out_path."""
    if AudioSegment is None:
        raise RuntimeError("pydub недоступен — установи requirements и ffmpeg")

    provider = config.TTS_PROVIDER
    client = _polly_client() if provider == "polly" else None

    # Опциональная аудио-заставка (assets/intro.mp3) идёт ПЕРВОЙ, чтобы тайминги
    # субтитров считались уже с её учётом.
    combined = AudioSegment.silent(duration=0)
    intro_path = config.ASSETS_DIR / "intro.mp3"
    if intro_path.exists():
        try:
            combined += AudioSegment.from_file(intro_path)[:4000].fade_out(1500)
        except Exception as e:
            print(f"[tts] intro пропущен: {e}")
    combined += AudioSegment.silent(duration=400)

    pause = AudioSegment.silent(duration=350)  # пауза между репликами
    segments = []  # тайминги для субтитров

    for ln in lines:
        voice = _voice_for(ln["speaker"], provider)
        text = ln["text"]
        if provider == "polly":
            audio_bytes = _polly_segment(client, text, voice)
        elif provider == "gtts":
            audio_bytes = _gtts_segment(text, voice)
        else:
            audio_bytes = _ttsmp3_segment(text, voice)
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        if provider == "gtts":
            seg = _pitch_shift(seg, _GTTS_PITCH.get(ln["speaker"], 0))
        start_ms = len(combined)
        combined += seg
        segments.append({"speaker": ln["speaker"], "text": text,
                         "start_ms": start_ms, "end_ms": len(combined)})
        combined += pause

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    combined.export(out_path, format="mp3", bitrate="128k",
                    tags={"artist": config.PODCAST_AUTHOR, "album": config.PODCAST_TITLE})
    return {
        "path": out_path,
        "duration_sec": int(len(combined) / 1000),
        "bytes": os.path.getsize(out_path),
        "segments": segments,
    }
