# English display names for the dashboard.
# The source CSV only has Korean names, so the UI layer converts them here:
#   - industries: hand-written English names (63 codes in the 2023-2025 data)
#   - districts: proper nouns, so they are romanized (Revised Romanization, simplified)

INDUSTRY_NAMES_EN = {
    "CS100001": "Korean Restaurant", "CS100002": "Chinese Restaurant",
    "CS100003": "Japanese Restaurant", "CS100004": "Western Restaurant",
    "CS100005": "Bakery", "CS100006": "Fast Food", "CS100007": "Fried Chicken",
    "CS100008": "Snack Bar (Bunsik)", "CS100009": "Pub / Bar",
    "CS100010": "Coffee & Beverages",
    "CS200001": "Tutoring Academy", "CS200002": "Language School",
    "CS200003": "Arts School", "CS200005": "Sports Lessons",
    "CS200006": "Medical Clinic", "CS200007": "Dental Clinic",
    "CS200008": "Korean Medicine Clinic", "CS200016": "Billiards Hall",
    "CS200017": "Golf Driving Range", "CS200019": "PC Bang (Internet Cafe)",
    "CS200024": "Sports Club / Gym", "CS200025": "Auto Repair",
    "CS200026": "Car Detailing", "CS200028": "Hair Salon",
    "CS200029": "Nail Salon", "CS200030": "Skin Care",
    "CS200031": "Laundry", "CS200032": "Appliance Repair",
    "CS200033": "Real Estate Agency", "CS200034": "Motel / Inn",
    "CS200036": "Gosiwon (Studio Lodging)", "CS200037": "Karaoke (Noraebang)",
    "CS300001": "Supermarket", "CS300002": "Convenience Store",
    "CS300003": "Computers & Peripherals", "CS300004": "Mobile Phones",
    "CS300006": "Rice & Grains", "CS300007": "Butcher", "CS300008": "Seafood",
    "CS300009": "Fruits & Vegetables", "CS300010": "Side-Dish Shop",
    "CS300011": "Clothing", "CS300014": "Shoes", "CS300015": "Bags",
    "CS300016": "Eyewear", "CS300017": "Watches & Jewelry",
    "CS300018": "Pharmacy", "CS300019": "Medical Devices",
    "CS300020": "Bookstore", "CS300021": "Stationery", "CS300022": "Cosmetics",
    "CS300024": "Sporting Goods", "CS300025": "Bicycles & Other Vehicles",
    "CS300026": "Toys", "CS300027": "Textiles", "CS300028": "Florist",
    "CS300029": "Pet Supplies", "CS300031": "Furniture",
    "CS300032": "Home Appliances", "CS300033": "Hardware Store",
    "CS300035": "Interior", "CS300036": "Lighting", "CS300043": "E-commerce",
}

import re

# Common words translated before romanizing the rest of a district name.
_END = r"(?=$|[\s()·,])"
_WORDS = [
    (r"_", " "),
    (r"(\d+)번(?:\s*출구)?", r" Exit \1"),
    (r"관광특구", " Tourist Zone"),
    (r"전통시장" + _END, " Traditional Market"),
    (r"시장" + _END, " Market"),
    (r"(?<=[가-힣])역" + _END, " Station"),
    (r"아파트" + _END, " Apt."),
    (r"사거리" + _END, " Intersection"),
    (r"주민센터" + _END, " Community Center"),
    (r"공원" + _END, " Park"),
    (r"초등학교" + _END, " Elementary School"),
    (r"중학교" + _END, " Middle School"),
    (r"고등학교" + _END, " High School"),
    (r"대학교" + _END, " University"),
    (r"구청" + _END, " District Office"),
    (r"상가" + _END, " Shopping Arcade"),
    (r"거리" + _END, " Street"),
]

_INITIAL = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "",
            "j", "jj", "ch", "k", "t", "p", "h"]
_MEDIAL = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe",
           "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
# Final consonant written at the end of a syllable (index 0 = none).
_FINAL = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p",
          "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]
# Final consonant carried over when the next syllable starts with a silent ㅇ.
_LIAISON = ["", "g", "kk", "ks", "n", "nj", "n", "d", "r", "lg", "lm", "lb", "ls",
            "lt", "lp", "r", "m", "b", "ps", "s", "ss", "ng", "j", "ch", "k", "t",
            "p", ""]


def _decompose(char):
    code = ord(char) - 0xAC00
    if 0 <= code < 11172:
        return code // 588, (code % 588) // 28, code % 28
    return None


def romanize(text):
    # Convert Hangul syllables to Latin letters; other characters are kept as is.
    for pattern, english in _WORDS:
        text = re.sub(pattern, english, text)
    parts = [_decompose(char) or char for char in text]
    out = []
    for index, part in enumerate(parts):
        if isinstance(part, str):
            out.append(part)
            continue
        initial, medial, final = part
        nxt = parts[index + 1] if index + 1 < len(parts) else None
        nxt = nxt if isinstance(nxt, tuple) else None
        prev = parts[index - 1] if index > 0 else None
        prev_final = prev[2] if isinstance(prev, tuple) else 0

        onset = _INITIAL[initial]
        if initial == 11 and prev_final:          # silent ㅇ: sound already carried over
            onset = ""
        elif initial == 5:                        # ㄹ after a consonant
            if prev_final == 8:
                onset = "l"                       # ㄹㄹ -> ll
            elif prev_final in (4, 16, 21, 1, 17):
                onset = "n"                       # e.g. 종로 Jongno, 청량리 Cheongnyangni
                if prev_final == 4:
                    onset = "l"                   # ㄴㄹ -> ll (신림 Sillim)

        coda = _FINAL[final]
        if final and nxt:
            if nxt[0] == 11:                      # next syllable starts with silent ㅇ
                coda = _LIAISON[final]
            elif final == 4 and nxt[0] == 5:
                coda = "l"                        # ㄴㄹ -> ll
            elif coda == "k" and nxt[0] in (2, 5, 6):
                coda = "ng"                       # ㄱ before ㄴ/ㄹ/ㅁ (독립 Dongnip)
            elif coda == "p" and nxt[0] in (2, 5, 6):   # 왕십리 Wangsimni
                coda = "m"
            elif coda == "t" and nxt[0] in (2, 6):
                coda = "n"
        out.append(onset + _MEDIAL[medial] + coda)

    result = re.sub(r"\s+", " ", "".join(out)).strip()
    result = re.sub(r"\s+([),])", r"\1", result)
    result = re.sub(r"(\S)\(", r"\1 (", result)
    return re.sub(r"(^|[\s(·/-])([a-z])", lambda m: m.group(1) + m.group(2).upper(), result)


def industry_name(code, korean_name):
    return INDUSTRY_NAMES_EN.get(code) or romanize(korean_name)


def district_name(korean_name):
    return romanize(korean_name)
