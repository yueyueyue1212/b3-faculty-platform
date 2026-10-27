"""Optional LLM integration. All business logic works without an API key."""
import json
import logging

import httpx

from ..config import (
    LLM_ALLOW_PERSONAL_DATA,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_RETRIES,
    LLM_TIMEOUT,
)

logger = logging.getLogger("b3.llm")

SYSTEM_PROMPT = (
    "你是高校师资管理平台的画像辅助助手。你只能依据用户给出的事实数据进行归纳，"
    "禁止编造论文、项目、奖项、任职、联系方式或任何未提供的信息。"
    "如果数据不足，必须明确指出“数据不足”，不得给出确定性评价。"
    "输出使用简洁中文，分为【画像摘要】和【发展建议】两部分。"
)


class LLMUnavailable(Exception):
    pass


def llm_configured() -> bool:
    return bool(LLM_API_KEY)


def llm_public_status() -> dict:
    return {
        "configured": llm_configured(),
        "model": LLM_MODEL if llm_configured() else None,
        "base_url": LLM_BASE_URL if llm_configured() else None,
        "allow_personal_data": LLM_ALLOW_PERSONAL_DATA,
        "mode": "llm" if llm_configured() else "local",
        "note": "未配置 API Key，系统使用本地规则生成摘要" if not llm_configured()
        else "已配置 LLM，仅发送脱敏后的事实统计与关键词",
    }


def chat_completion(messages: list[dict], temperature: float = 0.2) -> str:
    if not llm_configured():
        raise LLMUnavailable("未配置 LLM_API_KEY")
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    last_error = None
    for attempt in range(LLM_RETRIES + 1):
        try:
            with httpx.Client(timeout=LLM_TIMEOUT) as client:
                resp = client.post(
                    url,
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # network, auth, malformed response
            last_error = exc
            logger.warning("LLM call failed (attempt %s): %s", attempt + 1, exc)
    raise LLMUnavailable(f"LLM 服务调用失败：{last_error}")


def build_profile_facts(stats: dict) -> str:
    """Serialize only aggregated facts. No name/phone/email/ID is sent."""
    facts = {
        "研究方向": stats.get("research_direction") or "未提供",
        "研究关键词": stats.get("research_keywords") or "未提供",
        "职称": stats.get("title"),
        "学历": stats.get("degree") or "未提供",
        "成果总数": stats.get("output_count"),
        "成果年度分布": stats.get("output_by_year"),
        "成果类型分布": stats.get("output_by_type"),
        "项目总数": stats.get("project_count"),
        "主持项目数": stats.get("principal_project_count"),
        "项目经费合计": stats.get("project_funding_total"),
        "课程门次": stats.get("course_count"),
        "教学工作量(学时)": stats.get("teaching_hours_total"),
        "平均教学评价": stats.get("avg_evaluation_score"),
        "获奖数": stats.get("award_count"),
        "学术任职数": stats.get("academic_post_count"),
        "社会服务数": stats.get("social_service_count"),
        "数据完整度": stats.get("completeness"),
        "缺失字段": stats.get("missing_fields"),
    }
    return json.dumps(facts, ensure_ascii=False, indent=2)


def generate_profile_summary(stats: dict) -> dict:
    if not llm_configured():
        return {
            "text": stats.get("local_summary", ""),
            "mode": "local",
            "warning": "未配置 LLM_API_KEY，当前为本地规则生成，仅基于数据库统计事实。",
        }
    facts = build_profile_facts(stats)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请基于以下事实生成教师画像摘要与发展建议：\n{facts}"},
    ]
    try:
        text = chat_completion(messages)
        return {"text": text, "mode": "llm", "warning": "内容由大模型基于统计事实生成，请人工核对。"}
    except LLMUnavailable as exc:
        return {
            "text": stats.get("local_summary", ""),
            "mode": "local",
            "warning": f"{exc}；已自动回退到本地规则摘要。",
        }
