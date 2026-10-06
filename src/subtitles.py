"""Сборка SRT-субтитров из таймингов сегментов озвучки."""


def _ts(ms):
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap(text, width=42):
    """Переносит длинную реплику на 1-2 строки (читабельно на экране)."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines[:2])  # не больше 2 строк


def build_srt(segments, out_path):
    """segments: [{text, start_ms, end_ms}] -> пишет SRT-файл."""
    blocks = []
    for i, seg in enumerate(segments, 1):
        blocks.append(
            f"{i}\n{_ts(seg['start_ms'])} --> {_ts(seg['end_ms'])}\n{_wrap(seg['text'])}\n"
        )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))
    return out_path
