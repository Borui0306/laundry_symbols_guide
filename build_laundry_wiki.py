import os
import re
import time
import json
from typing import TypedDict, List, Dict, Literal
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from langgraph.graph import StateGraph, END

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
)
MODEL_NAME = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")

RAW_SOURCES = [
    {
        "id": "文獻 01",
        "title": "經濟部標檢局 CNS 8148 織物洗標國家標準指南",
        "content": "台灣 CNS 8148 與國際標準接軌，採用 5 種基本幾何圖形：水盆（水洗）、三角形（漂白）、正方形（乾燥）、熨斗（熨燙）、圓圈（專業維護）。圓點代表溫度：1點=30°C低溫、2點=40°C中溫、3點=60°C高溫。水盆或正方形下方的橫線代表機械力道溫和度：無線=標準、1條線=緩和、2條線=非常緩和。"
    },
    {
        "id": "文獻 02",
        "title": "ISO 3758 國際紡織品維護標籤符號標準",
        "content": "ISO 3758 規範全球通用洗標符號。任何圖形疊上打叉（✕）代表絕對禁止執行該動作。圓圈內寫 P 代表可使用四氯乙烯乾洗；圓圈內寫 F 代表僅限溫和碳氫溶劑乾洗；圓圈內寫 W 代表專業濕洗。"
    },
    {
        "id": "文獻 03",
        "title": "居家衣物漂白劑化學原理與纖維保護",
        "content": "含氯漂白水（次氯酸鈉）氧化力強，會破壞羊毛與蠶絲等蛋白質纖維並造成泛黃褪色。氧系漂白劑（過碳酸鈉）溫和護色。空心三角形允許任何漂白劑；三角形內有兩條斜線僅限氧系漂白（彩漂）；三角形打叉代表不可漂白。"
    },
    {
        "id": "文獻 04",
        "title": "針織毛衣與機能外套官方保養手冊",
        "content": "純羊毛毛衣吸水後重量增加，若使用正方形內含垂直線（吊掛晾乾）會拉長變形，必須使用正方形內含水平線（平放乾燥）。正方形內含圓圈代表機器滾筒烘乾。防水機能外套忌用高溫烘乾與乾洗溶劑，以免防水膜剝落。"
    },
    {
        "id": "文獻 05",
        "title": "熨燙溫度控制與常見布料燙傷預防",
        "content": "聚酯纖維與尼龍等合成纖維超過 110°C（1個點）會融化產生亮面燙傷。羊毛與絲綢可承受 150°C（2個點）。純棉與亞麻耐高溫可達 200°C（3個點）。熨斗下方蒸氣線打叉代表僅能乾燙、不可使用蒸氣。"
    }
]


class WikiState(TypedDict):
    sources: List[Dict[str, str]]
    current_idx: int
    wiki_pages: Dict[str, str]
    review_passed: bool
    review_feedback: str
    retry_count: int
    logs: List[str]


def call_llm_text(system_prompt: str, user_prompt: str) -> str:
    for attempt in range(5):
        try:
            time.sleep(10)
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=8192
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            wait_sec = 20 * (attempt + 1)
            print(f"[速率限制] 達到每分鐘 Token 上限，等待 {wait_sec} 秒後自動重試...")
            time.sleep(wait_sec)
    raise RuntimeError("超過最大重試次數。")


def parse_wiki_blocks(text: str) -> Dict[str, str]:
    pattern = r"===PAGE:\s*(.+?)\s*===\s*(.*?)(?=(?:===PAGE:|$))"
    matches = re.findall(pattern, text, re.DOTALL)
    pages = {}
    for title, body in matches:
        clean_title = title.strip().replace("[[", "").replace("]]", "")
        clean_body = body.strip()
        if clean_title and clean_body:
            pages[clean_title] = clean_body
    return pages


def ingest_node(state: WikiState) -> WikiState:
    idx = state["current_idx"]
    doc = state["sources"][idx]
    existing_keys = list(state["wiki_pages"].keys())

    sys_prompt = (
        "你是一位知識庫架構師，正在建立關於「衣物洗滌標示」的繁體中文 LLM Wiki。"
        "請嚴格使用以下分隔標籤格式輸出頁面（不要用 JSON，也不要用程式碼區塊）：\n"
        "===PAGE: 頁面標題===\n"
        "使用繁體中文撰寫的 Markdown 內容，並包含 [[頁面標題]] 雙向連結...\n"
        "每個頁面保持精簡白話（約 100 至 150 字）。"
    )
    user_prompt = (
        f"目前已建立的 Wiki 頁面：{existing_keys}\n"
        f"新匯入資料（{doc['id']} - {doc['title']}）：\n{doc['content']}\n\n"
        "請從以下主題中，挑選 1 到 3 個最相關的頁面進行建立或更新：\n"
        "00_洗滌標示系統總覽, 01_水洗符號與水溫控制, 02_漂白符號與化學藥劑, "
        "03_乾燥與烘乾方式, 04_熨燙溫度與蒸氣限制, 05_專業紡織品維護, 06_常見衣物材質實戰速查。"
    )

    raw_text = call_llm_text(sys_prompt, user_prompt)
    updated_pages = parse_wiki_blocks(raw_text)
    merged_pages = {**state["wiki_pages"], **updated_pages}

    logs = state["logs"] + [f"[資料擷取] 已處理 {doc['id']}《{doc['title']}》 → 目前累積 {len(merged_pages)} 個知識節點"]
    print(logs[-1])
    return {
        **state,
        "wiki_pages": merged_pages,
        "retry_count": 0,
        "logs": logs
    }


def verify_node(state: WikiState) -> WikiState:
    wiki_text = "\n\n".join(f"===PAGE: {k}===\n{v}" for k, v in state["wiki_pages"].items())
    sys_prompt = (
        "你是一位嚴謹的品質審核員，負責檢查給初學者看的「衣物洗滌標示」繁體中文 Wiki。"
        "請檢查內容是否符合 CNS 8148 / ISO 3758 事實標準、對新手是否白話好懂，以及是否包含 [[跨頁連結]]。"
        "回覆開頭請嚴格以 'STATUS: PASS' 或 'STATUS: FAIL' 起始，後方接一句繁體中文審核說明。"
    )
    user_prompt = f"請審核以下 Wiki 頁面內容：\n{wiki_text}"

    reply = call_llm_text(sys_prompt, user_prompt).strip()
    passed = "STATUS: PASS" in reply.upper()
    feedback = reply.replace("STATUS: PASS", "").replace("STATUS: FAIL", "").strip(" ：:\n")
    status_label = "通過" if passed else "未通過"

    logs = state["logs"] + [f"[品質檢查] 結果={status_label}｜意見：{feedback}"]
    print(logs[-1])
    return {
        **state,
        "review_passed": passed,
        "review_feedback": feedback,
        "logs": logs
    }


def refine_node(state: WikiState) -> WikiState:
    wiki_text = "\n\n".join(f"===PAGE: {k}===\n{v}" for k, v in state["wiki_pages"].items())
    sys_prompt = (
        "你是一位 Wiki 編輯，負責根據審核意見修正錯誤條目。"
        "請嚴格使用以下分隔標籤格式，僅輸出有修改的頁面（全部使用繁體中文，不要用 JSON）：\n"
        "===PAGE: 頁面標題===\n"
        "修正後的繁體中文 Markdown 內容..."
    )
    user_prompt = (
        f"目前 Wiki 內容：\n{wiki_text}\n\n"
        f"需要修正的審核意見：\n{state['review_feedback']}"
    )

    raw_text = call_llm_text(sys_prompt, user_prompt)
    fixed_pages = parse_wiki_blocks(raw_text)
    merged_pages = {**state["wiki_pages"], **fixed_pages}

    logs = state["logs"] + [f"[自動修正] 已依據審核意見完成第 {state['retry_count'] + 1} 次條目修訂"]
    print(logs[-1])
    return {
        **state,
        "wiki_pages": merged_pages,
        "retry_count": state["retry_count"] + 1,
        "logs": logs
    }


def advance_node(state: WikiState) -> WikiState:
    return {
        **state,
        "current_idx": state["current_idx"] + 1
    }


def export_node(state: WikiState) -> WikiState:
    os.makedirs("wiki_output", exist_ok=True)
    for title, content in state["wiki_pages"].items():
        safe_name = title.replace("/", "_") + ".md"
        with open(os.path.join("wiki_output", safe_name), "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}\n")

    with open(os.path.join("wiki_output", "wiki_db.json"), "w", encoding="utf-8") as f:
        json.dump({
            "pages": state["wiki_pages"],
            "pipeline_logs": state["logs"]
        }, f, ensure_ascii=False, indent=2)

    logs = state["logs"] + ["[匯出完成] 已將所有 Markdown 知識檔與 wiki_db.json 儲存至 ./wiki_output/"]
    print(logs[-1])
    return {**state, "logs": logs}


def route_after_verify(state: WikiState) -> Literal["refine", "advance", "export"]:
    if not state["review_passed"] and state["retry_count"] < 1:
        return "refine"
    if state["current_idx"] + 1 < len(state["sources"]):
        return "advance"
    return "export"


def build_graph():
    workflow = StateGraph(WikiState)
    workflow.add_node("ingest", ingest_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("advance", advance_node)
    workflow.add_node("export", export_node)

    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "verify")
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "refine": "refine",
            "advance": "advance",
            "export": "export"
        }
    )
    workflow.add_edge("refine", "verify")
    workflow.add_edge("advance", "ingest")
    workflow.add_edge("export", END)
    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    initial_state: WikiState = {
        "sources": RAW_SOURCES,
        "current_idx": 0,
        "wiki_pages": {},
        "review_passed": False,
        "review_feedback": "",
        "retry_count": 0,
        "logs": []
    }
    app.invoke(initial_state)