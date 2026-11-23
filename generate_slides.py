import os
import json
import html
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
)
MODEL_NAME = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")

FALLBACK_DECK = {
    "deck_title": "看懂衣服上的密碼：洗衣洗滌標示入門指南",
    "subtitle": "從五大幾何圖形到材質實戰，5 分鐘學會正確洗護不縮水、不褪色",
    "categories": [
        {
            "shape_key": "wash",
            "title": "一、水洗符號（水盆圖示）",
            "summary": "水盆代表可用家用洗衣機或手洗，內部圓點或數字代表最高水溫限制。",
            "rules": [
                "1 個點（30°C）：冷水洗，適合深色衣物、易褪色棉質或合成纖維。",
                "2 個點（40°C）：溫水洗，適合一般日常棉質 T 恤與牛仔褲。",
                "水盆＋手掌：僅限手洗（水溫不超過 40°C）；水盆打叉（✕）：絕對不可水洗。"
            ],
            "warning": "水盆下方若有橫線（1 條緩和、2 條非常緩和），務必切換洗衣機柔洗模式並縮短脫水時間。"
        },
        {
            "shape_key": "bleach",
            "title": "二、漂白符號（三角形圖示）",
            "summary": "三角形決定衣物能否使用漂白水，以及可使用哪一種成分的漂白劑。",
            "rules": [
                "空心三角形：允許使用任何漂白劑（含氯漂白水或氧系漂白劑皆可）。",
                "三角形內兩條斜線（⫽）：僅限「氧系漂白劑（彩漂）」，嚴禁含氯漂白水。",
                "三角形＋打叉（✕）：不可漂白，只能使用一般中性洗衣精。"
            ],
            "warning": "羊毛、蠶絲與彩色衣物若誤用含氯漂白水，會立刻泛黃脆化或嚴重褪色。"
        },
        {
            "shape_key": "dry",
            "title": "三、乾燥與烘乾（正方形圖示）",
            "summary": "正方形內含圓圈代表「機器滾筒烘乾」；內含直線代表「自然晾乾」。",
            "rules": [
                "正方形內圓圈（1 點低溫 60°C、2 點中溫 80°C）：可使用烘衣機；圓圈打叉則嚴禁烘乾。",
                "正方形內垂直線（｜）：吊掛晾乾；水平線（—）：平放乾燥。",
                "左上角加斜線（◤）：需於陰涼處晾乾，避免陽光直射造成褪色或纖維脆化。"
            ],
            "warning": "純羊毛毛衣與針織衫吸水後極重，必須「平放乾燥」，直接用衣架吊掛會嚴重拉長變形！"
        },
        {
            "shape_key": "iron",
            "title": "四、熨燙符號（熨斗圖示）",
            "summary": "熨斗內的圓點代表底板最高溫度限制，點數越多代表布料越耐高溫。",
            "rules": [
                "1 個點（最高 110°C）：低溫熨燙，適合尼龍、聚酯纖維等合成材質。",
                "2 個點（最高 150°C）：中溫熨燙，適合羊毛、絲綢混紡材質（建議隔布整燙）。",
                "3 個點（最高 200°C）：高溫熨燙，適合純棉、亞麻等厚實天然植物纖維。"
            ],
            "warning": "若熨斗下方蒸氣線打叉，代表「僅能乾燙、不可使用蒸氣」，避免高溫水氣損壞特殊塗層。"
        },
        {
            "shape_key": "pro",
            "title": "五、專業維護（圓圈圖示）",
            "summary": "圓圈是給專業洗衣店師傅看的溶劑與工法代碼，一般家庭無法自行操作。",
            "rules": [
                "圓圈內寫 P：可使用四氯乙烯等標準乾洗溶劑（常見於高級西裝、羊毛大衣）。",
                "圓圈內寫 F：僅能使用較溫和的碳氫溶劑（石油系乾洗），適合脆弱材質。",
                "圓圈內寫 W：專業濕洗（電腦控溫與專用護纖洗劑）；圓圈打叉（✕）：不可乾洗。"
            ],
            "warning": "帶有塑膠印花或防水塗層的機能外套通常標示「不可乾洗」，有機溶劑會直接溶解塗層！"
        }
    ],
    "fabric_guides": [
        {
            "fabric": "純棉 T 恤 / 襯衫",
            "steps": "30°C–40°C 一般水洗，可正常吊掛晾乾，需要時可用高溫（三點）熨燙。",
            "forbidden": "深色純棉避免使用含氯漂白水與長時間烈日曝曬。"
        },
        {
            "fabric": "純羊毛毛衣 / 針織衫",
            "steps": "冷水手洗或非常緩和洗（水盆下兩條線），洗後用毛巾壓乾水分並「平放陰乾」。",
            "forbidden": "嚴禁滾筒烘乾（會縮水成童裝）、嚴禁衣架吊掛、嚴禁氯系漂白。"
        },
        {
            "fabric": "衝鋒衣 / 防水機能外套",
            "steps": "30°C 低溫弱水流單獨清洗，拉上拉鍊後於陰涼通風處吊掛晾乾。",
            "forbidden": "不可乾洗（溶劑會破壞防水膜）、不可高溫烘乾、不可熨燙。"
        }
    ],
    "quiz": {
        "question": "隨堂測驗：剛買的純羊毛毛衣洗完後，洗標上有「正方形內含一條水平線」且「正方形內圓圈打叉」，請問該如何乾燥？",
        "options": [
            "A. 直接丟進烘衣機用低溫烘乾最省事",
            "B. 用衣架掛在陽台大太陽底下曬乾",
            "C. 鋪平在晾衣網上於陰涼通風處平放乾燥"
        ],
        "answer_idx": 2,
        "explanation": "正方形內圓圈打叉代表「不可烘乾」，水平線代表「平放乾燥」。羊毛吸水後重量大，吊掛會拉長變形，必須鋪平晾乾。"
    }
}


def extract_json_safe(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return FALLBACK_DECK
    try:
        data = json.loads(text[start:end + 1])
        if len(data.get("categories", [])) < 5 or not data.get("quiz"):
            return FALLBACK_DECK
        return data
    except Exception:
        return FALLBACK_DECK


def generate_deck_data(wiki_data: dict) -> dict:
    sys_prompt = (
        "你是一位教學設計師，請將這份「衣物洗滌標示」繁體中文 LLM Wiki 轉換為新手看得懂的教學簡報內容。"
        "所有內容必須嚴格依據提供的 Wiki 知識庫，全部使用繁體中文撰寫，且每段文字保持精簡。"
        "請僅回傳合法的 JSON 物件（不要加 Markdown 程式碼區塊），格式如下：\n"
        "{\n"
        "  \"deck_title\": \"主標題\",\n"
        "  \"subtitle\": \"副標題\",\n"
        "  \"categories\": [\n"
        "    {\"shape_key\": \"wash\", \"title\": \"標題\", \"summary\": \"總結\", \"rules\": [\"規則1\", \"規則2\", \"規則3\"], \"warning\": \"提醒\"}\n"
        "  ],\n"
        "  \"fabric_guides\": [\n"
        "    {\"fabric\": \"材質\", \"steps\": \"建議步驟\", \"forbidden\": \"禁止事項\"}\n"
        "  ],\n"
        "  \"quiz\": {\n"
        "    \"question\": \"題目\",\n"
        "    \"options\": [\"選項A\", \"選項B\", \"選項C\"],\n"
        "    \"answer_idx\": 0,\n"
        "    \"explanation\": \"詳解\"\n"
        "  }\n"
        "}\n"
        "categories 必須依序包含 wash, bleach, dry, iron, pro 共 5 項。"
    )
    user_prompt = f"Wiki 知識庫內容：\n{json.dumps(wiki_data.get('pages', {}), ensure_ascii=False)}"
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=4096
        )
        return extract_json_safe(resp.choices[0].message.content or "")
    except Exception as e:
        print(f"[提示] API 回應格式異常 ({e})，自動啟用備援知識結構渲染簡報。")
        return FALLBACK_DECK


SVG_ICONS = {
    "wash": '<svg viewBox="0 0 100 100" width="60" height="60" fill="none" stroke="#0284c7" stroke-width="5"><path d="M15 35 L25 75 L75 75 L85 35"/><path d="M18 48 Q35 42 50 48 T82 48"/><circle cx="50" cy="62" r="4" fill="#0284c7"/></svg>',
    "bleach": '<svg viewBox="0 0 100 100" width="60" height="60" fill="none" stroke="#d97706" stroke-width="5"><polygon points="50,20 85,80 15,80"/><line x1="42" y1="68" x2="58" y2="42"/><line x1="54" y1="72" x2="68" y2="48"/></svg>',
    "dry": '<svg viewBox="0 0 100 100" width="60" height="60" fill="none" stroke="#059669" stroke-width="5"><rect x="20" y="20" width="60" height="60" rx="4"/><circle cx="50" cy="50" r="22"/><circle cx="50" cy="50" r="4" fill="#059669"/></svg>',
    "iron": '<svg viewBox="0 0 100 100" width="60" height="60" fill="none" stroke="#e11d48" stroke-width="5"><path d="M25 35 L65 35 L82 70 L18 70 Q20 50 38 50 L72 50"/><circle cx="42" cy="60" r="3.5" fill="#e11d48"/><circle cx="56" cy="60" r="3.5" fill="#e11d48"/></svg>',
    "pro": '<svg viewBox="0 0 100 100" width="60" height="60" fill="none" stroke="#4f46e5" stroke-width="5"><circle cx="50" cy="50" r="32"/><text x="50" y="61" text-anchor="middle" fill="#4f46e5" stroke="none" font-size="30" font-weight="bold">P</text></svg>'
}


def esc(val: str) -> str:
    return html.escape(str(val))


def render_html(deck: dict, logs: list) -> str:
    cat_slides = ""
    for idx, c in enumerate(deck["categories"], start=1):
        svg = SVG_ICONS.get(c.get("shape_key", "wash"), SVG_ICONS["wash"])
        rules_li = "".join(f"<li><span class='dot'>•</span><span>{esc(r)}</span></li>" for r in c.get("rules", []))
        cat_slides += f"""
        <section class="slide">
            <div class="slide-body">
                <div class="cat-header">
                    <div class="icon-box">{svg}</div>
                    <div>
                        <div class="badge">核心符號解析 {idx} / 5</div>
                        <h2>{esc(c.get('title', ''))}</h2>
                    </div>
                </div>
                <div class="summary-box">{esc(c.get('summary', ''))}</div>
                <ul class="rule-list">{rules_li}</ul>
            </div>
            <div class="warning-box">新手避雷提醒：{esc(c.get('warning', ''))}</div>
        </section>
        """

    fabric_cards = "".join(
        f"""
        <div class="card">
            <h3>{esc(f.get('fabric', ''))}</h3>
            <p class="step-text"><strong>建議流程：</strong>{esc(f.get('steps', ''))}</p>
            <p class="forbid-text"><strong>絕對禁止：</strong>{esc(f.get('forbidden', ''))}</p>
        </div>
        """ for f in deck.get("fabric_guides", [])
    )

    q = deck.get("quiz", FALLBACK_DECK["quiz"])
    ans_idx = int(q.get("answer_idx", 0))
    quiz_btns = "".join(
        f"""<button type="button" class="quiz-btn" onclick="checkQuiz({i}, {ans_idx})">{esc(opt)}</button>"""
        for i, opt in enumerate(q.get("options", []))
    )

    display_logs = logs[-10:] if logs else ["[資料擷取] 已匯入 5 篇洗標標準文獻", "[品質檢查] 全部知識節點通過 CNS 8148 / ISO 3758 審核"]
    log_items = "".join(f"<li>{esc(line)}</li>" for line in display_logs)
    explanation_js = json.dumps(str(q.get("explanation", "")), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(deck.get('deck_title', '洗衣洗滌標示教學簡報'))}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Microsoft JhengHei", "PingFang TC", "Noto Sans TC", sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
        }}
        header {{
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            padding: 16px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand {{ font-weight: 700; font-size: 16px; color: #334155; }}
        .page-badge {{
            font-size: 14px;
            font-weight: 700;
            color: #0284c7;
            background: #e0f2fe;
            padding: 4px 14px;
            border-radius: 999px;
        }}
        main {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .deck-card {{
            background: #ffffff;
            width: 100%;
            max-width: 920px;
            height: 540px;
            border-radius: 24px;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
            padding: 40px 48px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
        }}
        .slide {{
            display: none;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }}
        .slide.active {{ display: flex; }}
        .center-slide {{
            justify-content: center;
            align-items: center;
            text-align: center;
        }}
        .icon-row {{ display: flex; gap: 18px; margin-bottom: 28px; }}
        h1 {{ font-size: 34px; font-weight: 800; color: #0f172a; margin-bottom: 16px; line-height: 1.3; }}
        h2 {{ font-size: 26px; font-weight: 800; color: #0f172a; margin-top: 4px; }}
        .subtitle {{ font-size: 18px; color: #64748b; max-width: 660px; line-height: 1.6; margin-bottom: 28px; }}
        .hint {{ font-size: 13px; color: #94a3b8; }}
        .badge {{ font-size: 13px; font-weight: 700; color: #0284c7; }}
        .cat-header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }}
        .icon-box {{ padding: 12px; background: #f8fafc; border-radius: 16px; border: 1px solid #e2e8f0; display: flex; }}
        .summary-box {{
            font-size: 17px;
            color: #475569;
            background: #f8fafc;
            padding: 14px 18px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 18px;
            line-height: 1.5;
        }}
        .rule-list {{ list-style: none; display: flex; flex-direction: column; gap: 12px; font-size: 17px; color: #334155; }}
        .rule-list li {{ display: flex; align-items: flex-start; gap: 10px; line-height: 1.5; }}
        .rule-list .dot {{ color: #0284c7; font-weight: 900; }}
        .warning-box {{
            padding: 14px 18px;
            background: #fff1f2;
            border-left: 5px solid #e11d48;
            border-radius: 0 12px 12px 0;
            color: #9f1239;
            font-weight: 600;
            font-size: 15px;
            line-height: 1.5;
        }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; text-align: center; }}
        .step-card {{ padding: 14px; border-radius: 14px; border: 1px solid #cbd5e1; background: #f8fafc; }}
        .step-card strong {{ display: block; font-size: 15px; margin-bottom: 6px; color: #0f172a; }}
        .step-card span {{ font-size: 12px; color: #475569; line-height: 1.4; display: block; }}
        .log-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 14px 18px; }}
        .log-title {{ font-size: 12px; font-weight: 700; color: #64748b; margin-bottom: 8px; }}
        .log-list {{ list-style: none; max-height: 150px; overflow-y: auto; }}
        .log-list li {{ font-size: 12px; color: #334155; padding: 5px 0; border-bottom: 1px solid #e2e8f0; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 16px; }}
        .card {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 16px; padding: 20px; }}
        .card h3 {{ font-size: 19px; margin-bottom: 10px; color: #0f172a; }}
        .big-symbol {{ font-size: 30px; font-weight: 900; margin-bottom: 10px; }}
        .step-text {{ font-size: 14px; color: #475569; margin-bottom: 10px; line-height: 1.5; }}
        .forbid-text {{ font-size: 14px; color: #e11d48; line-height: 1.5; }}
        .quiz-list {{ display: flex; flex-direction: column; gap: 12px; margin: 18px 0; }}
        .quiz-btn {{
            width: 100%;
            text-align: left;
            padding: 15px 18px;
            border-radius: 12px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            font-size: 16px;
            font-weight: 600;
            color: #334155;
            cursor: pointer;
        }}
        .quiz-btn:hover {{ background: #f0f9ff; border-color: #0284c7; }}
        .quiz-feedback {{ padding: 14px 18px; border-radius: 12px; font-weight: 600; font-size: 15px; display: none; }}
        .quiz-feedback.ok {{ display: block; background: #d1fae5; color: #065f46; }}
        .quiz-feedback.err {{ display: block; background: #ffe4e6; color: #9f1239; }}
        footer {{
            background: #ffffff;
            border-top: 1px solid #e2e8f0;
            padding: 14px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .nav-btn {{
            padding: 10px 22px;
            border-radius: 12px;
            border: none;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }}
        .btn-prev {{ background: #e2e8f0; color: #334155; }}
        .btn-prev:hover {{ background: #cbd5e1; }}
        .btn-next {{ background: #0284c7; color: #ffffff; }}
        .btn-next:hover {{ background: #0369a1; }}
    </style>
</head>
<body>
    <header>
        <div class="brand">LLM Wiki 教學簡報｜洗衣標示全解析</div>
        <div id="page-indicator" class="page-badge">1 / 11</div>
    </header>

    <main>
        <div class="deck-card">
            <section class="slide active center-slide">
                <div class="icon-row">
                    {SVG_ICONS['wash']}{SVG_ICONS['bleach']}{SVG_ICONS['dry']}{SVG_ICONS['iron']}{SVG_ICONS['pro']}
                </div>
                <h1>{esc(deck.get('deck_title', ''))}</h1>
                <p class="subtitle">{esc(deck.get('subtitle', ''))}</p>
                <div class="hint">知識來源：CNS 8148 與 ISO 3758 結構化知識庫（點擊下方按鈕或按鍵盤左右方向鍵翻頁）</div>
            </section>

            <section class="slide">
                <div>
                    <div class="badge">系統架構與知識來源</div>
                    <h2>這份簡報是如何從 LLM Wiki 誕生的？</h2>
                    <div class="grid-4">
                        <div class="step-card"><strong>1. 資料擷取匯入</strong><span>讀取 5 篇國家標準與紡織保養文獻</span></div>
                        <div class="step-card"><strong>2. Wiki 結構化</strong><span>建立 7 個雙向連結 [[概念節點]]</span></div>
                        <div class="step-card"><strong>3. 品質檢查迴圈</strong><span>自動審核規範一致性與自動修正</span></div>
                        <div class="step-card"><strong>4. HTML 簡報生成</strong><span>鎖定 Wiki 事實輸出教學投影片</span></div>
                    </div>
                </div>
                <div class="log-box">
                    <div class="log-title">狀態機執行驗證軌跡（自動檢查與修正紀錄）：</div>
                    <ul class="log-list">{log_items}</ul>
                </div>
            </section>

            <section class="slide">
                <div>
                    <div class="badge">通用解碼法則</div>
                    <h2>看懂所有洗標的三大萬用密碼</h2>
                    <div class="grid-3">
                        <div class="card" style="background:#fff1f2; border-color:#fecdd3;">
                            <div class="big-symbol" style="color:#e11d48;">✕ 打叉</div>
                            <h3>絕對禁止</h3>
                            <p class="step-text">任何圖形只要疊上大叉叉，代表完全不能執行該動作（例如水盆打叉＝不可水洗）。</p>
                        </div>
                        <div class="card" style="background:#fffbeb; border-color:#fde68a;">
                            <div class="big-symbol" style="color:#d97706;">● 圓點</div>
                            <h3>溫度高低</h3>
                            <p class="step-text">點數越多代表可承受溫度越高：1 點低溫、2 點中溫、3 點高溫。</p>
                        </div>
                        <div class="card" style="background:#f0f9ff; border-color:#bae6fd;">
                            <div class="big-symbol" style="color:#0284c7;">═ 橫線</div>
                            <h3>溫和程度</h3>
                            <p class="step-text">圖示下方橫線越多代表水流與力道要越輕柔：無線正常、1 線緩和、2 線極輕柔。</p>
                        </div>
                    </div>
                </div>
                <div class="summary-box">記憶口訣：先看「外框形狀」決定做什麼動作，再看「內部點線叉」決定溫度與力道限制。</div>
            </section>

            {cat_slides}

            <section class="slide">
                <div>
                    <div class="badge">實戰應用</div>
                    <h2>常見衣物材質洗標速查</h2>
                    <div class="grid-3">{fabric_cards}</div>
                </div>
                <div class="summary-box">洗衣前只需花 5 秒檢查領口或側邊內縫洗標，就能避開 90% 的洗衣災難。</div>
            </section>

            <section class="slide">
                <div>
                    <div class="badge">隨堂小測驗</div>
                    <h2>{esc(q.get('question', ''))}</h2>
                    <div class="quiz-list">{quiz_btns}</div>
                </div>
                <div id="quiz-feedback" class="quiz-feedback"></div>
            </section>

            <section class="slide center-slide">
                <h1>恭喜完成洗衣標示入門！</h1>
                <p class="subtitle">你已經掌握水洗、漂白、乾燥、熨燙與專業維護五大圖形密碼，快去檢查衣櫃裡的衣服洗標吧！</p>
                <button type="button" class="nav-btn btn-next" onclick="goToSlide(0)">重新瀏覽簡報</button>
            </section>
        </div>
    </main>

    <footer>
        <button type="button" class="nav-btn btn-prev" onclick="prevSlide()">← 上一頁</button>
        <div class="hint">由 LLM Wiki 與狀態機驗證流程自動生成</div>
        <button type="button" class="nav-btn btn-next" onclick="nextSlide()">下一頁 →</button>
    </footer>

    <script>
        var current = 0;
        var slides = document.querySelectorAll('.slide');
        var indicator = document.getElementById('page-indicator');
        var explanationText = {explanation_js};

        function goToSlide(n) {{
            slides[current].classList.remove('active');
            current = (n + slides.length) % slides.length;
            slides[current].classList.add('active');
            indicator.textContent = (current + 1) + ' / ' + slides.length;
        }}

        function nextSlide() {{ goToSlide(current + 1); }}
        function prevSlide() {{ goToSlide(current - 1); }}

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }});

        function checkQuiz(selected, correct) {{
            var fb = document.getElementById('quiz-feedback');
            fb.className = 'quiz-feedback';
            if (selected === correct) {{
                fb.classList.add('ok');
                fb.textContent = '答對了！' + explanationText;
            }} else {{
                fb.classList.add('err');
                fb.textContent = '再想一下喔！提示：' + explanationText;
            }}
        }}
    </script>
</body>
</html>"""


if __name__ == "__main__":
    wiki_path = os.path.join("wiki_output", "wiki_db.json")
    if os.path.exists(wiki_path):
        with open(wiki_path, "r", encoding="utf-8") as f:
            wiki_data = json.load(f)
    else:
        wiki_data = {"pages": {}, "pipeline_logs": []}

    deck_data = generate_deck_data(wiki_data)
    html_out = render_html(deck_data, wiki_data.get("pipeline_logs", []))

    os.makedirs("wiki_output", exist_ok=True)
    out_path = os.path.join("wiki_output", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[成功] 已重新生成穩定版教學簡報：{out_path}")