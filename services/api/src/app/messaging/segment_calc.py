"""
Accurate SMS Segment Calculator and Text Shortening Utility.
Supports:
1. GSM 03.38 7-bit default alphabet + extension characters.
2. UCS-2 16-bit encoding detection for non-Latin / Indic / Cyrillic / Arabic / Emojis.
3. Multi-segment concatenation accounting (UDH headers).
4. Advisory message shortening with 'Reply MORE' pagination.
"""

from typing import Dict, List, Set, Tuple

# Standard GSM 7-bit basic character set
GSM7_BASIC: Set[str] = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ"
    " !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

# GSM 7-bit extension characters (each counts as 2 characters in GSM-7)
GSM7_EXTENDED: Set[str] = {"\x0c", "^", "{", "}", "\\", "[", "~", "]", "|", "€"}


def is_gsm7(text: str) -> bool:
    """Checks whether the entire text can be encoded within GSM 7-bit alphabet."""
    for char in text:
        if char not in GSM7_BASIC and char not in GSM7_EXTENDED:
            return False
    return True


def calculate_segments(text: str) -> Dict[str, int | str | bool]:
    """
    Calculates exact SMS segments, character counts, and encoding type.
    
    Returns dict:
      - encoding: 'GSM-7' | 'UCS-2'
      - character_count: total raw character count
      - encoded_length: effective units (accounting for 2-unit extended GSM chars or UTF-16 units)
      - segments: number of SMS segments required
      - characters_per_segment: payload limit per segment (single / multi)
      - remaining_in_current_segment: headroom before another segment is required
    """
    if not text:
        return {
            "encoding": "GSM-7",
            "character_count": 0,
            "encoded_length": 0,
            "segments": 1,
            "characters_per_segment": 160,
            "remaining_in_current_segment": 160,
        }

    if is_gsm7(text):
        encoding = "GSM-7"
        # Extended characters count as 2
        encoded_len = sum(2 if c in GSM7_EXTENDED else 1 for c in text)
        if encoded_len <= 160:
            segments = 1
            chars_per_seg = 160
            remaining = 160 - encoded_len
        else:
            chars_per_seg = 153
            segments = (encoded_len + chars_per_seg - 1) // chars_per_seg
            remaining = (segments * chars_per_seg) - encoded_len
    else:
        encoding = "UCS-2"
        # Each UTF-16 code unit counts (surrogate pairs for emojis count as 2 code units)
        encoded_len = len(text.encode("utf-16-be")) // 2
        if encoded_len <= 70:
            segments = 1
            chars_per_seg = 70
            remaining = 70 - encoded_len
        else:
            chars_per_seg = 67
            segments = (encoded_len + chars_per_seg - 1) // chars_per_seg
            remaining = (segments * chars_per_seg) - encoded_len

    return {
        "encoding": encoding,
        "character_count": len(text),
        "encoded_length": encoded_len,
        "segments": segments,
        "characters_per_segment": chars_per_seg,
        "remaining_in_current_segment": remaining,
    }


def shorten_to_segments(
    text: str,
    max_segments: int = 2,
    more_suffix: str = " ... [Reply MORE for details]"
) -> Tuple[str, str]:
    """
    Shortens text so that it strictly fits within `max_segments`.
    If truncated, appends `more_suffix` and returns (truncated_text, remaining_text).
    If it fits as-is, returns (text, "").
    """
    info = calculate_segments(text)
    if info["segments"] <= max_segments:
        return text, ""

    # Determine maximum permissible encoded units
    if info["encoding"] == "GSM-7":
        max_units = 160 if max_segments == 1 else max_segments * 153
    else:
        max_units = 70 if max_segments == 1 else max_segments * 67

    suffix_info = calculate_segments(more_suffix)
    target_units = max_units - suffix_info["encoded_length"]

    # Binary search or backward scan for word boundary
    words = text.split(" ")
    accumulated: List[str] = []
    
    for word in words:
        candidate = " ".join(accumulated + [word])
        cand_info = calculate_segments(candidate)
        if cand_info["encoded_length"] <= target_units:
            accumulated.append(word)
        else:
            break

    first_part = " ".join(accumulated) + more_suffix
    remaining_text = text[len(" ".join(accumulated)):].strip()

    return first_part, remaining_text
