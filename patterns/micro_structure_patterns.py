import re

# =========================================================
# BASE BUILDING BLOCKS
# =========================================================

# ЛУК'ЯН
# АТАНÁС
# ВАЛЕ-РОНЬКА
# ЛЕСЬ¹      ← ¹²³ для надрядкових цифр у назвах
# АВЕР'ЯН    ← \u2019 правна лапка (Ukrainian apostrophe)
# ЛУК'ЯН     ← \u2018 ліва лапка
# ВАЛЕ-РОНЬКА ← \u0027 прямий апостроф / \u02BC modifier letter apostrophe
NAME = r"[\wА-ЯІЇЄҐЁа-яіїєґ''\u2018\u2019\u02BC`\-\u0301Á¹²³]+"

# =========================================================

# АВРАМКО, АВРАМОНЬКО, АВРАМОЧКО
# ОВРАМКО; ОВРАМОНЬКО
NAME_VARS = fr"{NAME}(?:,\s*{NAME}|;\s*{NAME})*"

# =========================================================

# (ЄВТУХ, ЯВТУХ)
# (ЛУКАШ)
HALF_OFFICIAL_VARS = (
    fr"\((?P<half_official_vars>{NAME_VARS})\)"
)

# =========================================================

# гр.;      лат.;      гр.*;
# лат.:     запозичене;    нов.;
# д.євр.;   сканд.;    тюрк.;   д-рус.;
# слов., нов.;   ← підтримка двох мов через кому
_LANG_ATOM = (
    r"(?:"
    r"англ(?:\.-сакс)?|"
    r"араб|арам|баск|болг|бр|"
    r"вірм|герм|фр|"
    r"д-євр|д\.євр|"              # д.євр (крапка без дефіса)
    r"слов|"
    r"гот|гр|грузин|"
    r"д\.-англ|д\.-герм|д\.-євр|д\.-інд|"
    r"д\.-рус|д-рус|"             # д-рус (дефіс без крапки)
    r"днн|єгип|ісп|"
    r"італ|кельт|кл|лат|лит|"
    r"молд|монг|нім|нов|"
    r"сканд|тюрк|"                # сканд, тюрк
    r"укр|sp|лап|"                # укр., sp., лап.
    r"та ін|"                     # та ін. (для "та ін.; те саме, що…")
    r"запозичене"
    r")"
)

ETYMOLOGY_LANG = (
    fr"{_LANG_ATOM}(?:\.\*?)?"                   # перша мова (+ опційна крапка/*?)
    fr"(?:,\s*{_LANG_ATOM}(?:\.\*?)?)?"          # опційна друга мова (слов., нов.;)
    r"[;:]"                                       # обов'язковий ; або :
)

# =========================================================

# eleutheros — вільний.
# Achilleus — ім'я героя Троянської війни.
# рим. родове ім'я Aurelius;
ETYMOLOGY_COMMENT = r".+?\."

# =========================================================

ETYMOLOGY_GROUP = (
    fr"(?P<etymology>{ETYMOLOGY_LANG})"
    fr"\s*"
    fr"(?P<etymology_comment>{ETYMOLOGY_COMMENT})"
)

# =========================================================
# OFFICIAL VARS
# =========================================================

# АГАФІЯ, ГАФІЯ
# АРТЁМ, АРТЁМІЙ; АРТЕМОН
OFFICIAL_VARS = (
    fr"(?P<official_vars>"
    fr"{NAME}"
    fr"(?:,\s*{NAME}|;\s*{NAME})*"
    fr")"
)

# =========================================================
# CORE FRAGMENTS — роздільник , (кома)
# =========================================================

# АХІЛЛІЙ гр.; Achilleus — ім'я героя Троянської війни.
# КАРИНА ¹ лат.; carina — кіль корабля.   ← пробіл + надрядковий номер
ENTRY_CORE_ETYM = (
    fr"^(?P<name>{NAME})(?:\s[¹²³])?"     # ← опційний надрядковий номер
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================

# АГАФІЯ, ГАФІЯ гр.; agathē — добра.
ENTRY_CORE_OFFICIAL_ETYM = (
    fr"^(?P<name>{NAME})"
    fr",\s*"
    fr"{OFFICIAL_VARS}"
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================

# МАТВІЙ (МАТІЙ, МАТЯШ) д-євр.; ...
ENTRY_CORE_HALF_OFFICIAL_ETYM = (
    fr"^(?P<name>{NAME})"
    fr"\s*"
    fr"{HALF_OFFICIAL_VARS}"
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================

# УСТИМ, УСТИН (ЮСТИМ, ЮСТИН) лат.; ...
ENTRY_CORE_OFFICIAL_HALF_ETYM = (
    fr"^(?P<name>{NAME})"
    fr",\s*"
    fr"{OFFICIAL_VARS}"
    fr"\s*"
    fr"{HALF_OFFICIAL_VARS}"
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================
# CORE FRAGMENTS — роздільник ; (крапка з комою)
# =========================================================

# АВГУСТ; АВГУСТИН лат.; augustus — величний, священний.
# КЛИМ; КЛИМЕНТ, КЛИМЕНТІЙ лат.; ...
# КОРНЕЛІЙ; КОРНІЛО, КОРНІЛІЙ; КОРНІЙ лат.; ...
ENTRY_CORE_SEMI_OFFICIAL_ETYM = (
    fr"^(?P<name>{NAME})"
    fr";\s*"                       # ← ; замість ,
    fr"{OFFICIAL_VARS}"
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================

# ІМ'Я; ВАРІАНТ (НАПІВОФІЦ.) мова; ...
ENTRY_CORE_SEMI_OFFICIAL_HALF_ETYM = (
    fr"^(?P<name>{NAME})"
    fr";\s*"
    fr"{OFFICIAL_VARS}"
    fr"\s*"
    fr"{HALF_OFFICIAL_VARS}"
    fr"\s+"
    fr"{ETYMOLOGY_GROUP}"
)

# =========================================================
# WITH UNOFFICIAL VARS
# (unofficial_vars-варіант ЗАВЖДИ перед своїм чистим аналогом)
# =========================================================

# ---------------------------------------------------------
# УСТИМ, УСТИН (ЮСТИМ, ЮСТИН) лат.; ... УСТИМКО, УСТИМОНЬКО...
# ---------------------------------------------------------
ENTRY_WITH_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_OFFICIAL_HALF_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# ---------------------------------------------------------
# ІМ'Я; ОФІЦ. (НАПІВОФІЦ.) мова; ... НЕОФІЦ...
# ---------------------------------------------------------
ENTRY_WITH_SEMI_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_SEMI_OFFICIAL_HALF_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# ---------------------------------------------------------
# МАТВІЙ (МАТІЙ, МАТЯШ) д-євр.; ... МАТВІЙКО...
# ---------------------------------------------------------
ENTRY_WITH_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_HALF_OFFICIAL_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# ---------------------------------------------------------
# АГАФІЯ, ГАФІЯ гр.; agathē — добра. ГАФА, ГАФІЙКА...
# ---------------------------------------------------------
ENTRY_WITH_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_OFFICIAL_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# ---------------------------------------------------------
# ВАЛЕНТИН; ВАЛЕНТІЙ, ВАЛЕНТ лат.; ... ВАЛЬКО, ВАЛЯ...
# ---------------------------------------------------------
ENTRY_WITH_SEMI_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_SEMI_OFFICIAL_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# ---------------------------------------------------------
# АВТОНОМ гр.; autos — самозаконник. АВТОНОМКО, АВТОНОМОНЬКО...
# ---------------------------------------------------------
ENTRY_WITH_ETYM_GROUP_UNOFFICIAL_VARS = (
    fr"{ENTRY_CORE_ETYM}"
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# =========================================================
# COMPLETE ENTRY PATTERNS (без unofficial vars)
# =========================================================

# УСТИМ, УСТИН (ЮСТИМ, ЮСТИН) лат.; ...
ENTRY_WITH_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP = (
    fr"{ENTRY_CORE_OFFICIAL_HALF_ETYM}"
    fr"$"
)

# ІМ'Я; ОФІЦ. (НАПІВОФІЦ.) мова; ...
ENTRY_WITH_SEMI_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP = (
    fr"{ENTRY_CORE_SEMI_OFFICIAL_HALF_ETYM}"
    fr"$"
)

# МАТВІЙ (МАТІЙ, МАТЯШ) д-євр.; ...
ENTRY_WITH_HALF_OFFICIAL_VARS_ETYM_GROUP = (
    fr"{ENTRY_CORE_HALF_OFFICIAL_ETYM}"
    fr"$"
)

# АГАФІЯ, ГАФІЯ гр.; agathē — добра.
ENTRY_WITH_OFFICIAL_VARS_ETYM_GROUP = (
    fr"{ENTRY_CORE_OFFICIAL_ETYM}"
    fr"$"
)

# ФЛАВІАН; ФЛАВІЙ лат.; flavus — жовтий, золотавий; білявий.
ENTRY_WITH_SEMI_OFFICIAL_VARS_ETYM_GROUP = (
    fr"{ENTRY_CORE_SEMI_OFFICIAL_ETYM}"
    fr"$"
)

# АХІЛЛІЙ гр.; Achilleus — ім'я героя Троянської війни.
ENTRY_WITH_ETYM_GROUP = (
    fr"{ENTRY_CORE_ETYM}"
    fr"$"
)

# =========================================================
# LINK ENTRIES
# =========================================================

# АКСЄНІЯ div. ОКСАНА.
# АВЕРКІЙ, АВЕР'ЯН div. ОВЕРКІЙ.        ← NAME_VARS перед div.
# АТАНÁС, АТАНÁСІЙ, АФАНÁСІЙ div. ПАНÁС.
REF_ENTRY_WITH_EQ_ONLY = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"   # перше ім'я = name, решта = official_vars
    fr"\s+див\.\s+"
    fr"(?P<equivalent_name>{NAME})"
    fr"\.$"
)

# =========================================================

# ЛЕВКО div. 1) ЛЕВ; 2) ЛЕОНТІЙ.
# ОНІСЬКО div. 1) ОНІСИМ; 2) ОНІСІЙ.
REF_ENTRY_WITH_NUMBERED_REFS = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"
    fr"\s+див\.\s+"
    fr"(?P<refs>(?:\d+\)\s*{NAME}[;,\s]*)+)"
    fr"\.$"
)

# =========================================================

# РАДИМ слов.; те саме, що РАДОМИР.
# ЙВАН та ін.; те саме, що ІВАН.
REF_ENTRY_WITH_ETYM_SAME_NAME = (
    fr"^(?P<name>{NAME})"
    fr"\s+"
    fr"(?P<etymology>{ETYMOLOGY_LANG})"
    fr"\s*те\s+саме,\s+що\s+"
    fr"(?P<etym_same_name>{NAME})"
    fr"\.$"
)

# =========================================================

# УЛЯН лат.; те саме, що ЮЛІАН. УЛЯНКО...
REF_ENTRY_WITH_ETYM_SAME_NAME_UNOFFICIAL_VARS = (
    fr"^(?P<name>{NAME})"
    fr"\s+"
    fr"(?P<etymology>{ETYMOLOGY_LANG})"
    fr"\s*те\s+саме,\s+що\s+"
    fr"(?P<etym_same_name>{NAME})"
    fr"\.\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# =========================================================
# STANDALONE UNOFFICIAL VARS
# =========================================================

# АБАКУМКО, АБАКУМОНЬКО, АБАКУМОЧКО, АВАКУМКО, АВАКУМОНЬКО; БАКУМ.
# АРТЁМОЧКО, АРТЁМИК, АРТЁМЧИК, АРТЁМЦЬО.
UNOFFICIAL_VARS_ONLY = (
    fr"^(?P<unofficial_vars>{NAME_VARS})\.$"
)

# =========================================================
# FEMININE ENTRIES — HELPERS
# =========================================================

# Розширений unofficial_vars: дозволяє "... (дів. ще NAME)" після іменного списку
# Приклади:
#   ГАПА, ГАПОНЬКА... (дів. ще АГАФІЯ)
#   ЛЮБА...(дів. ще ЛЮБОВ); МИРОСЯ, МИРА... (дів. ще МИРОСЛАВА)
#   ІВАНКА, ІВАНЦЯ (дів. ще ІВАННА)         ← без крапок перед дужкою
# [іи] — бо в словнику трапляються обидва варіанти (U+0456 і / U+0438 и)
_XREF = fr"(?:\.\.\.)?(?:\s*\([дД][іи]в\.\s+ще\s+{NAME_VARS}\))?"

_FEM_UNOFFIC_EXT = (
    fr"(?P<unofficial_vars>"
    fr"{NAME_VARS}"
    fr"{_XREF}"
    fr"(?:;\s*{NAME_VARS}{_XREF})*"
    fr")"
)

# =========================================================
# FEMININE ENTRIES — CORE FRAGMENTS
# =========================================================

# АВГУСТА жін. до АВГУСТ.
# АРСЄНА, АРСЄНІЯ жін. до АРСЄН, АРСЄНІЙ.
# ← NAME (лише перше ім'я) + опційні official_vars через кому
FEM_CORE_FEM_FROM_MASC = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"  # АРСЄНІЯ або НАСТАСІЯ, НАСТЯ
    fr"\s+жін\.\s+до\s+"
    fr"(?P<base_name>{NAME_VARS})"               # може бути АРСЄН, АРСЄНІЙ
    fr"\."
)

# =========================================================

# ЄВГЕНІЯ (ЄВГЕНА, ІВГА, ЮГІНА) жін. до ЄВГЕН.
# ОЛЕКСАНДРА, ОЛЕКСАНДРІНА (ОЛЕСЯ) жін. до ОЛЕКСАНДР.
# УСТИНА, ЮСТИНА (УСТЯ, ВУСТЯ) жін. до УСТИН, ЮСТИН.
FEM_CORE_FEM_FROM_MASC_HALF = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"  # опційні офіц. варіанти через кому
    fr"\s*"
    fr"{HALF_OFFICIAL_VARS}"
    fr"\s+жін\.\s+до\s+"
    fr"(?P<base_name>{NAME_VARS})"
    fr"\."
)

# =========================================================

# МАР'ЯНА, МАРІА́ННА жін. до МАР'Я́Н, МАРІА́Н; можливо, контамінація імен…
FEM_CORE_FEM_FROM_MASC_NOTE = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"
    fr"\s+жін\.\s+до\s+"
    fr"(?P<base_name>{NAME_VARS})"
    fr";\s*"
    fr"(?P<note>.+?)\."              # довільний коментар
)

# =========================================================

# АНТОНИДА утв. від чол. імені АНТІН, АНТОН.
# ДАРІНА, ОДАРІНА, ОДАРКА утв. від чол. імені ДАРІЙ.
FEM_CORE_UTW_VID_MASC = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"  # ОДАРІНА, ОДАРКА
    fr"\s+утв\.\s+від\s+чол\.\s+імені\s+"
    fr"(?P<base_name>{NAME_VARS})"
    fr"\."
)

# =========================================================
# FEMININE ENTRIES — COMPLETE PATTERNS
# (unoffic ЗАВЖДИ перед чистим аналогом)
# =========================================================

# ЄВГЕНІЯ (ЄВГЕНА, ІВГА) жін. до ЄВГЕН. ЄВГЕНОНЬКА, ЄВГЕНОЧКА...
FEM_ENTRY_FEM_FROM_MASC_HALF_UNOFFICIAL_VARS = (
    fr"{FEM_CORE_FEM_FROM_MASC_HALF}"
    fr"\s+"
    fr"{_FEM_UNOFFIC_EXT}"
    fr"\.$"
)

# УСТИНА, ЮСТИНА (УСТЯ, ВУСТЯ) жін. до УСТИН, ЮСТИН.
FEM_ENTRY_FEM_FROM_MASC_HALF = (
    fr"{FEM_CORE_FEM_FROM_MASC_HALF}"
    fr"$"
)

# АВГУСТА жін. до АВГУСТ. ГУСТА, ГУСТЯ...
# АГАПІЯ жін. до АГАПІЙ. ГАПА, ГАПОНЬКА... (дів. ще АГАФІЯ).
FEM_ENTRY_FEM_FROM_MASC_UNOFFICIAL_VARS = (
    fr"{FEM_CORE_FEM_FROM_MASC}"
    fr"\s+"
    fr"{_FEM_UNOFFIC_EXT}"
    fr"\.$"
)

# МАР'ЯНА жін. до МАР'ЯН, МАРІАН; можливо, контамінація… МАР'ЯНОНЬКА…
FEM_ENTRY_FEM_FROM_MASC_NOTE_UNOFFICIAL_VARS = (
    fr"{FEM_CORE_FEM_FROM_MASC_NOTE}"
    fr"\s+"
    fr"{_FEM_UNOFFIC_EXT}"
    fr"\.$"
)

# ДАРІЯ, ДАР'Я жін. до ДАРІЙ. Дів. ДАРІНА.
FEM_ENTRY_FEM_FROM_MASC_WITH_REF = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"
    fr"\s+жін\.\s+до\s+"
    fr"(?P<base_name>{NAME_VARS})"
    fr"\.\s+"
    fr"[Дд][іи]в\.\s+"
    fr"(?P<equivalent_name>{NAME})"
    fr"\.$"
)

# БОГДАНА жін. до БОГДАН.
FEM_ENTRY_FEM_FROM_MASC = (
    fr"{FEM_CORE_FEM_FROM_MASC}"
    fr"$"
)

# АНТОНИДА утв. від чол. імені АНТІН, АНТОН. АНТОСЯ, ТОНЯ... (дів. ще АНТОНІНА); НІДА.
FEM_ENTRY_UTW_VID_MASC_UNOFFICIAL_VARS = (
    fr"{FEM_CORE_UTW_VID_MASC}"
    fr"\s+"
    fr"{_FEM_UNOFFIC_EXT}"
    fr"\.$"
)

# РАФАЛІНА утв. від чол. імені РАФАЇЛ.
FEM_ENTRY_UTW_VID_MASC = (
    fr"{FEM_CORE_UTW_VID_MASC}"
    fr"$"
)

# МА́РТА те саме, що МА́РФА. МА́РТОНЬКА, МА́РТОЧКА...
FEM_TE_SAME_UNOFFICIAL_VARS = (
    fr"^(?P<name>{NAME})"
    fr"(?:,\s*(?P<official_vars>{NAME_VARS}))?"
    fr"\s+те\s+саме,\s+що\s+"
    fr"(?P<etym_same_name>{NAME})"
    fr"\.\s+"
    fr"{_FEM_UNOFFIC_EXT}"
    fr"\.$"
)

# =========================================================
# АСЯ скороч. варіант імені АНАСТАСІЯ... АСЕНЬКА, АСЕЧКА.
# РАЇНА можливо, фонетичний варіант імені Раїса. РАЇНОНЬКА, РАЯ.
# ЛЄСЯ скороч. варіант від ряду імен... ЛЕСЕНЬКА, ЛЕСЕЧКА...
# Загальний паттерн: NAME + вільний текст + . + unofficial_vars.
#
# КРИТИЧНО: \s+ між іменем та описом запобігає двом видам помилок:
#   1. Бектрекінг NAME обійти lookahead (бо NAME не може бектрекнути крізь пробіл)
#   2. Статті вигляду "ДАРІЯ, ДАР'Я жін. до..." — кома після імені не є пробілом
#
# Lookaheads перевіряються ПІСЛЯ пробілу — тобто на першому символі опису:
#   (?!жін\.\s+до)  — не жін. до
#   (?!утв\.\s+від) — не утв. від чол. імені
#   (?![Дд][іи]в\.) — не посилальна стаття
FEM_FREE_TEXT_UNOFFICIAL_VARS = (
    fr"^(?P<name>{NAME})(?:\s[¹²³])?"
    fr"\s+"                                # пробіл після імені — ОБОВ'ЯЗКОВИЙ
    fr"(?!жін\.\s+до)"                    # опис ≠ жін. до
    fr"(?!утв\.\s+від)"                   # опис ≠ утв. від чол. імені
    fr"(?![Дд][іи]в\.)"                   # опис ≠ Дів./Див.
    fr"(?P<description>.+?)\."
    fr"\s+"
    fr"(?P<unofficial_vars>{NAME_VARS})"
    fr"\.$"
)

# залишаємо старий аліас для зворотної сумісності
FEM_REF_ENTRY_FEM_FROM_MASC = FEM_ENTRY_FEM_FROM_MASC

# =========================================================
# ENTRY_PATTERNS
# Порядок: специфічніший → загальніший.
# unofficial_vars-варіант ЗАВЖДИ перед своїм чистим аналогом,
# бо ETYMOLOGY_COMMENT = .+?\.  з'їдає unofficial_vars при $ на кінці.
# Посилальні (ref_*) — перед чистими entry, бо .+?. поглинає "те саме що".
# =========================================================

ENTRY_PATTERNS: dict[str, re.Pattern] = {

    # ── офіц(,) + напівофіц. + неофіц. ───────────────────────────────
    "off_half_etym_unoffic": re.compile(
        ENTRY_WITH_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    # ── офіц(;) + напівофіц. + неофіц. ───────────────────────────────
    "semi_off_half_etym_unoffic": re.compile(
        ENTRY_WITH_SEMI_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    # ── напівофіц. + неофіц. ──────────────────────────────────────────
    "half_etym_unoffic": re.compile(
        ENTRY_WITH_HALF_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    # ── офіц(,) + неофіц. ─────────────────────────────────────────────
    "off_etym_unoffic": re.compile(
        ENTRY_WITH_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    # ── офіц(;) + неофіц. ─────────────────────────────────────────────
    "semi_off_etym_unoffic": re.compile(
        ENTRY_WITH_SEMI_OFFICIAL_VARS_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    # ── тільки етимологія + неофіц. ───────────────────────────────────
    "etym_unoffic": re.compile(
        ENTRY_WITH_ETYM_GROUP_UNOFFICIAL_VARS,
        re.DOTALL,
    ),

    # ── посилальні (перед чистими entry, бо .+?. поглинає "те саме що")
    "ref_etym_same_unoffic": re.compile(
        REF_ENTRY_WITH_ETYM_SAME_NAME_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "ref_etym_same": re.compile(
        REF_ENTRY_WITH_ETYM_SAME_NAME,
        re.DOTALL,
    ),
    "ref_numbered": re.compile(           # ЛЕВКО div. 1) ЛЕВ; 2) ЛЕОНТІЙ.
        REF_ENTRY_WITH_NUMBERED_REFS,
        re.DOTALL,
    ),
    "ref_eq": re.compile(                 # оновлений: NAME_VARS перед div.
        REF_ENTRY_WITH_EQ_ONLY,
        re.DOTALL,
    ),

    # ── чисті entry-паттерни (без unofficial_vars) ────────────────────
    "off_half_etym": re.compile(
        ENTRY_WITH_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP,
        re.DOTALL,
    ),
    "semi_off_half_etym": re.compile(
        ENTRY_WITH_SEMI_OFFICIAL_VARS_HALF_OFFICIAL_VARS_ETYM_GROUP,
        re.DOTALL,
    ),
    "half_etym": re.compile(
        ENTRY_WITH_HALF_OFFICIAL_VARS_ETYM_GROUP,
        re.DOTALL,
    ),
    "off_etym": re.compile(
        ENTRY_WITH_OFFICIAL_VARS_ETYM_GROUP,
        re.DOTALL,
    ),
    "semi_off_etym": re.compile(          # ФЛАВІАН; ФЛАВІЙ лат.; …
        ENTRY_WITH_SEMI_OFFICIAL_VARS_ETYM_GROUP,
        re.DOTALL,
    ),
    "etym": re.compile(
        ENTRY_WITH_ETYM_GROUP,
        re.DOTALL,
    ),

    # ── тільки варіанти без етимології ────────────────────────────────
    "unofficial_vars_only": re.compile(   # АБАКУМКО, АВАКУМКО; БАКУМ.
        UNOFFICIAL_VARS_ONLY,
        re.DOTALL,
    ),

    # ── жіночі форми (unoffic перед чистим, half перед простим) ──────
    "fem_half_unoffic": re.compile(       # ЄВГЕНІЯ (ЄВГЕНА) жін. до ЄВГЕН. ЄВГЕНОНЬКА...
        FEM_ENTRY_FEM_FROM_MASC_HALF_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "fem_half": re.compile(               # УСТИНА, ЮСТИНА (УСТЯ) жін. до УСТИН, ЮСТИН.
        FEM_ENTRY_FEM_FROM_MASC_HALF,
        re.DOTALL,
    ),
    "fem_unoffic": re.compile(            # АВГУСТА жін. до АВГУСТ. ГУСТА... / ... (дів. ще X).
        FEM_ENTRY_FEM_FROM_MASC_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "fem_note_unoffic": re.compile(       # МАР'ЯНА жін. до МАР'ЯН; можливо, контамінація… МАР'ЯНОНЬКА…
        FEM_ENTRY_FEM_FROM_MASC_NOTE_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "fem_with_ref": re.compile(           # ДАРІЯ, ДАР'Я жін. до ДАРІЙ. Дів. ДАРІНА.
        FEM_ENTRY_FEM_FROM_MASC_WITH_REF,
        re.DOTALL,
    ),
    "fem_from_masc": re.compile(          # БОГДАНА жін. до БОГДАН.
        FEM_ENTRY_FEM_FROM_MASC,
        re.DOTALL,
    ),
    "fem_utw_unoffic": re.compile(        # АНТОНИДА утв. від чол. імені АНТІН. АНТОСЯ... (дів. ще X); НІДА.
        FEM_ENTRY_UTW_VID_MASC_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "fem_utw": re.compile(                # РАФАЛІНА утв. від чол. імені РАФАЇЛ.
        FEM_ENTRY_UTW_VID_MASC,
        re.DOTALL,
    ),
    "fem_te_same_unoffic": re.compile(    # МА́РТА те саме, що МА́РФА. МА́РТОНЬКА...
        FEM_TE_SAME_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
    "fem_free_text_unoffic": re.compile(  # АСЯ скороч. варіант… АСЕНЬКА. / РАЇНА можливо… РАЯ.
        FEM_FREE_TEXT_UNOFFICIAL_VARS,
        re.DOTALL,
    ),
}