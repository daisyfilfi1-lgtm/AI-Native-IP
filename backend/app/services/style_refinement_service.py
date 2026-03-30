"""
文案迭代优化与 IP 风格学习：对话式反馈 → 改写 → 总结沉淀到 strategy_config.style_learnings，
供后续选题/原创/仿写生成时注入提示词。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import ContentDraft, IP
from app.services.ai_client import chat_feedback

logger = logging.getLogger(__name__)

MAX_LEARNINGS = 40
MAX_FEEDBACK_LOG = 30

# 历史记录里没有 assistant_reply（旧数据）时占位，保证多轮 messages 角色交替
_FALLBACK_ASSISTANT_REPLY = "（已按你的说明改好了。你可以继续说下一条修改意见。）"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_style_learnings_texts(db: Session, ip_id: str, limit: int = 25) -> List[str]:
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip or not isinstance(ip.strategy_config, dict):
        return []
    raw = ip.strategy_config.get("style_learnings") or []
    out: List[str] = []
    for item in raw[-limit:]:
        if isinstance(item, dict) and item.get("text"):
            t = str(item["text"]).strip()
            if t:
                out.append(t[:500])
        elif isinstance(item, str) and item.strip():
            out.append(item.strip()[:500])
    return out


def append_style_learning(db: Session, ip_id: str, text: str) -> int:
    """追加一条学习要点，返回当前条数。"""
    t = (text or "").strip()
    if not t:
        return 0
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return 0
    cfg = dict(ip.strategy_config or {})
    learnings: List[Any] = list(cfg.get("style_learnings") or [])
    learnings.append({"text": t[:400], "created_at": _utc_now_iso(), "source": "user_iteration"})
    if len(learnings) > MAX_LEARNINGS:
        learnings = learnings[-MAX_LEARNINGS:]
    cfg["style_learnings"] = learnings
    ip.strategy_config = cfg
    flag_modified(ip, "strategy_config")
    db.commit()
    # 同步到 Memory 向量库（独立会话，失败不影响主流程）
    try:
        from app.services.style_learning_memory_sync import sync_style_learning_after_commit

        sync_style_learning_after_commit(ip_id, t)
    except Exception as ex:
        logger.warning("style learning memory sync skipped: %s", ex)
    return len(learnings)


def record_rewrite_feedback(
    db: Session,
    *,
    draft_id: str,
    ip_id: str,
    rewrite_reason: str,
    user_comment: Optional[str],
) -> bool:
    """写入草稿上的「重写原因」反馈。草稿不存在或 IP 不匹配时返回 False。"""
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == draft_id).first()
    if not draft or draft.ip_id != ip_id:
        return False
    wf = dict(draft.workflow or {})
    log = list(wf.get("refine_feedback_log") or [])
    log.append(
        {
            "at": _utc_now_iso(),
            "rewrite_reason": rewrite_reason,
            "user_comment": (user_comment or "").strip()[:2000],
        }
    )
    if len(log) > MAX_FEEDBACK_LOG:
        log = log[-MAX_FEEDBACK_LOG:]
    wf["refine_feedback_log"] = log
    draft.workflow = wf
    flag_modified(draft, "workflow")
    db.commit()
    return True


def _strip_markdown_code_fence(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    从模型输出中取出第一个平衡的 {...}，避免正文里含 '}' 或 Gemini 包在 markdown 里时解析失败。
    仅在双引号字符串内识别转义，与 JSON 一致。
    """
    s = text
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    i = start
    while i < len(s):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
        i += 1
    return None


def _parse_json_sections(raw: str) -> Dict[str, str]:
    raw = _strip_markdown_code_fence((raw or "").strip())
    blob = raw
    try:
        data = json.loads(blob)
        if isinstance(data, dict):
            pass
        else:
            raise ValueError("not an object")
    except (json.JSONDecodeError, ValueError):
        extracted = _extract_first_json_object(raw)
        if not extracted:
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                raise ValueError("模型未返回可解析的 JSON")
            extracted = m.group(0)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise ValueError("模型返回的 JSON 格式无效") from e
    if not isinstance(data, dict):
        raise ValueError("模型未返回 JSON 对象")
    return {
        "hook": str(data.get("hook") or "").strip(),
        "story": str(data.get("story") or "").strip(),
        "opinion": str(data.get("opinion") or "").strip(),
        "cta": str(data.get("cta") or "").strip(),
    }


def _recompute_workflow_body(wf: Dict[str, Any]) -> None:
    """合并 hook/story/opinion/cta 后同步 workflow.body，避免与正文脱节。"""
    parts = [str(wf.get(k) or "").strip() for k in ("hook", "story", "opinion", "cta")]
    lines = [p for p in parts if p]
    wf["body"] = "\n\n".join(lines)


def _format_sections_digest(sections: Dict[str, str], *, max_each: int = 200) -> str:
    """改稿后给用户的「助手回复」摘要，用于多轮对话里的 assistant 角色（贴近 Gemini 的连续对话体感）。"""
    labels = [("钩子", "hook"), ("故事", "story"), ("观点", "opinion"), ("结尾", "cta")]
    lines: List[str] = []
    for zh, key in labels:
        t = (sections.get(key) or "").strip()
        if not t:
            continue
        snip = t[:max_each] + ("…" if len(t) > max_each else "")
        lines.append(f"【{zh}】{snip}")
    head = "好的，已按你的说明更新了本篇口播稿，你可以继续说要改哪里：\n"
    if not lines:
        return "好的，已按你的说明更新了本篇；若某段为空，请再说明要补什么。"
    return head + "\n".join(lines)


def refine_draft_with_feedback(
    db: Session,
    *,
    draft_id: str,
    ip_id: str,
    user_feedback: str,
    client_hook: Optional[str] = None,
    client_story: Optional[str] = None,
    client_opinion: Optional[str] = None,
    client_cta: Optional[str] = None,
) -> Dict[str, Any]:
    """根据自然语言反馈改写 hook/story/opinion/cta，并写回草稿。

    若前端传入 client_* 四段（与页面当前编辑态一致），先合并进 workflow 再改稿，避免用户本地改过段落却仍按数据库旧稿改写。
    """
    feedback = (user_feedback or "").strip()
    if not feedback:
        raise ValueError("反馈内容不能为空")

    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == draft_id).first()
    if not draft or draft.ip_id != ip_id:
        raise ValueError("草稿不存在")

    wf = dict(draft.workflow or {})
    if any(
        x is not None
        for x in (client_hook, client_story, client_opinion, client_cta)
    ):
        if client_hook is not None:
            wf["hook"] = client_hook
        if client_story is not None:
            wf["story"] = client_story
        if client_opinion is not None:
            wf["opinion"] = client_opinion
        if client_cta is not None:
            wf["cta"] = client_cta
        _recompute_workflow_body(wf)
        draft.workflow = wf
        flag_modified(draft, "workflow")
        db.flush()

    hook = str(wf.get("hook") or "")
    story = str(wf.get("story") or "")
    opinion = str(wf.get("opinion") or "")
    cta = str(wf.get("cta") or "")
    title = str(wf.get("title") or wf.get("topic") or "未命名")

    # 多轮对话：OpenAI/Gemini 兼容的 system + user/assistant 交替（体感接近 Gemini 连续对话）
    prev_hist = list(wf.get("refine_history") or [])

    learnings = get_style_learnings_texts(db, ip_id)
    learnings_block = "\n".join(f"- {x}" for x in learnings) if learnings else "（暂无历史学习要点）"

    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    self_name = (ip.nickname or ip.name or "IP") if ip else "IP"

    system_prompt = f"""你是帮助创作者改短视频口播稿的助手，交流方式像 Gemini：简洁、有同理心、支持多轮连续改稿。

## 任务
根据用户说明，修改四个板块：钩子、故事/案例、观点/干货、结尾（CTA）。保持与 IP「{self_name}」人设一致，语言口语化、适合口播。

## 该 IP 已积累的文案要点（须遵守）
{learnings_block}

## 输出格式（必须严格遵守）
只输出一个 JSON 对象，不要 markdown 代码块，不要 JSON 以外的说明文字：
{{"hook":"...","story":"...","opinion":"...","cta":"..."}}
四个键均为字符串；某段无需补充且原为空可给空字符串。"""

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for h in prev_hist[-12:]:
        if not isinstance(h, dict):
            continue
        # 缺省 type 的旧数据仍视为 refine，避免多轮上下文被整段丢弃
        if h.get("type") is not None and h.get("type") != "refine":
            continue
        u = (h.get("user_feedback") or "").strip()
        if not u:
            continue
        messages.append({"role": "user", "content": u[:8000]})
        ar = (h.get("assistant_reply") or "").strip() or _FALLBACK_ASSISTANT_REPLY
        messages.append({"role": "assistant", "content": ar[:12000]})

    final_user = f"""## 话题/标题
{title}

## 当前四段（请在本轮用户说明的基础上修改）
【钩子】{hook}
【故事/案例】{story}
【观点/干货】{opinion}
【结尾/CTA】{cta}

## 用户本轮说明
{feedback}

请只输出 JSON 对象，键为 hook, story, opinion, cta。"""

    messages.append({"role": "user", "content": final_user})

    raw = chat_feedback(
        messages=messages,
        model=None,
        temperature=0.68,
    )
    if not raw:
        raise ValueError("模型暂时不可用，请稍后重试")
    sections = _parse_json_sections(raw)

    # 合并正文
    parts = [sections["hook"], sections["story"], sections["opinion"], sections["cta"]]
    body = "\n\n".join(p for p in parts if p)

    wf.update(
        {
            "hook": sections["hook"],
            "story": sections["story"],
            "opinion": sections["opinion"],
            "cta": sections["cta"],
            "body": body,
        }
    )
    assistant_digest = _format_sections_digest(sections)
    hist = list(wf.get("refine_history") or [])
    hist.append(
        {
            "at": _utc_now_iso(),
            "type": "refine",
            "user_feedback": feedback[:2000],
            "assistant_reply": assistant_digest[:12000],
        }
    )
    wf["refine_history"] = hist[-MAX_FEEDBACK_LOG:]
    draft.workflow = wf
    flag_modified(draft, "workflow")
    db.commit()

    return {
        "ok": True,
        "draft_id": draft_id,
        "hook": sections["hook"],
        "story": sections["story"],
        "opinion": sections["opinion"],
        "cta": sections["cta"],
        "assistant_reply": assistant_digest,
    }


def summarize_iteration_learning(
    db: Session,
    *,
    draft_id: str,
    ip_id: str,
    user_note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    在用户满意后，根据本稿迭代记录生成可复用的学习要点，写入 IP.strategy_config.style_learnings。
    """
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == draft_id).first()
    if not draft or draft.ip_id != ip_id:
        raise ValueError("草稿不存在")

    wf = dict(draft.workflow or {})
    hist = wf.get("refine_history") or []
    fb_log = wf.get("refine_feedback_log") or []
    title = str(wf.get("title") or wf.get("topic") or "")

    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    ip_name = ip.name if ip else "IP"

    lines: List[str] = []
    for h in hist[-15:]:
        if isinstance(h, dict) and h.get("user_feedback"):
            lines.append(f"- 反馈：{str(h['user_feedback'])[:400]}")
    for f in fb_log[-10:]:
        if isinstance(f, dict):
            lines.append(
                f"- 分类：{f.get('rewrite_reason','')} 说明：{str(f.get('user_comment') or '')[:300]}"
            )

    extra = (user_note or "").strip()
    prompt = f"""你是写作教练。根据下面「同一篇稿子在迭代中收到的反馈」，总结出 **3-6 条** 可写入「后续自动生成提示」的要点。
每条独立一行，以「- 」开头，每条不超过 90 字，用中文。要具体可执行（避免空话），面向该 IP 的长期文案风格。

IP 名称：{ip_name}
稿件主题：{title[:200]}
用户补充说明：{extra or "无"}

迭代记录：
{chr(10).join(lines) if lines else "（无结构化记录，仅根据主题归纳通用建议）"}

只输出要点列表，不要编号以外的多余解释。"""

    raw = chat_feedback(
        messages=[{"role": "user", "content": prompt}],
        model=None,
        temperature=0.35,
    )
    if not raw:
        raise ValueError("模型暂时不可用，无法总结学习要点")
    bullets: List[str] = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if s.startswith("- "):
            bullets.append(s[2:].strip()[:400])
        elif s.startswith("•"):
            bullets.append(s[1:].strip()[:400])
    if not bullets:
        # 整段作为一条
        one = (raw or "").strip()[:400]
        if one:
            bullets = [one]

    added = 0
    for b in bullets[:6]:
        if b:
            append_style_learning(db, ip_id, b)
            added += 1

    return {"ok": True, "added": added, "bullets": bullets[:6]}

