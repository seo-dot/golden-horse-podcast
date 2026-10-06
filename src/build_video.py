"""Сборка видео для YouTube через ffmpeg: заставка + фон-фото машины + вшитые субтитры.

Итог: 1920x1080 MP4 =
  [заставка ~3с: фото машины + название + Octane] + [основная часть: фото + аудио + субтитры].

Требует ffmpeg в системе. Шрифт берётся из assets/font.ttf или системного Poppins/DejaVu.
"""
import os
import re
import shutil
import subprocess
from . import config

W, H = 1920, 1080


def _font_path():
    for p in [
        config.ASSETS_DIR / "font.ttf",
        "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(str(p)):
            return str(p)
    return ""


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def _esc_drawtext(text):
    """Экранирование текста для drawtext."""
    text = text.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"’")
    return text


def _bg_filter():
    """Заполнить кадр фото машины (crop-to-fill). Без затемняющей плашки —
    субтитры в картинку больше НЕ вшиваем (они идут отдельной дорожкой YouTube)."""
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"


def _build_intro(image, title_text, intro_path, seconds=3):
    """Титульная заставка: ЧЁТКОЕ фото машины (без размытия) + лёгкое затемнение +
    тёмная плашка в нижней трети, поверх которой название авто и 'OCTANE RENT'.
    """
    custom = config.ASSETS_DIR / "intro.mp4"
    if custom.exists():
        shutil.copy(str(custom), intro_path)
        return intro_path

    font = _font_path()
    title = _esc_drawtext(title_text)
    plate_y = int(H * 2 / 3)          # плашка в нижней трети кадра
    plate_h = H - plate_y
    draw = (
        # лёгкое общее затемнение — фото машины остаётся хорошо видно
        f"drawbox=x=0:y=0:w={W}:h={H}:color=black@0.28:t=fill,"
        # тёмная плашка в нижней трети под текст
        f"drawbox=x=0:y={plate_y}:w={W}:h={plate_h}:color=black@0.55:t=fill,"
        # название авто — крупно, по центру плашки
        f"drawtext=text='{title}':fontcolor=white:fontsize=96:"
        f"x=(w-text_w)/2:y={plate_y}+70:box=0"
        + (f":fontfile='{font}'" if font else "")
        + ","
        # бренд под названием
        f"drawtext=text='GOLDEN HORSE':fontcolor=white:fontsize=50:"
        f"x=(w-text_w)/2:y={plate_y}+200:alpha=0.92"
        + (f":fontfile='{font}'" if font else "")
    )
    # НЕТ boxblur — фон остаётся чётким фото машины (crop-to-fill)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{draw}"
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", image,
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(seconds), "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-shortest", intro_path,
    ])
    return intro_path


def _build_main(image, audio, main_path):
    """Основная часть: фото машины на весь кадр + аудио. Субтитры НЕ вшиваются;
    остаётся только маленькая подпись-логотип 'octane.rent' в углу."""
    font = _font_path()
    vf = _bg_filter()
    # маленькая подпись-логотип в левом нижнем углу
    brand = "golden-horse.ae"
    vf += (
        f",drawtext=text='{brand}':fontcolor=white:fontsize=34:x=60:y={H-70}:alpha=0.9"
        + (f":fontfile='{font}'" if font else "")
    )
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", image, "-i", audio,
        "-vf", vf, "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-r", "30", "-c:a", "aac", "-b:a", "192k", "-shortest", main_path,
    ])
    return main_path


def _concat(intro_path, main_path, out_path):
    _run([
        "ffmpeg", "-y", "-i", intro_path, "-i", main_path,
        "-filter_complex",
        "[0:v]setsar=1[v0];[1:v]setsar=1[v1];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", out_path,
    ])
    return out_path


def build_video(image_path, audio_path, title_text, out_path, tmp_dir=None):
    """Собирает финальное видео (без вшитых субтитров). Возвращает {path, duration_sec}."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg не найден в системе")
    tmp_dir = tmp_dir or os.path.dirname(out_path)
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # запасная картинка, если фото машины не скачалось
    if not image_path or not os.path.exists(image_path):
        image_path = _placeholder_image(tmp_dir)

    intro = os.path.join(tmp_dir, "_intro.mp4")
    main = os.path.join(tmp_dir, "_main.mp4")
    _build_intro(image_path, title_text, intro, seconds=config.INTRO_SECONDS)
    _build_main(image_path, audio_path, main)
    _concat(intro, main, out_path)

    for f in (intro, main):
        try:
            os.remove(f)
        except OSError:
            pass
    return {"path": out_path, "duration_sec": int(_probe_duration(out_path))}


def _placeholder_image(tmp_dir):
    path = os.path.join(tmp_dir, "_placeholder.png")
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x0B0B0F:s={W}x{H}",
          "-frames:v", "1", path])
    return path


def download_image(url, out_path):
    """Скачивает фото машины (для видео). Возвращает путь или None."""
    if not url:
        return None
    try:
        import requests
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 OctanePodcastBot"})
        r.raise_for_status()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(r.content)
        return out_path
    except Exception as e:
        print(f"[video] фото не скачалось ({e}) — будет заглушка")
        return None
