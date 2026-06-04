import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import find_project_root
from app.schemas.skills import AgentSkillRecord, SkillCreateRequest, SkillSearchResult
from app.services.prompt_config import get_config_dir


def get_skill_registry_path() -> Path:
    path = get_config_dir() / "agent-skills.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_skill_registry() -> list[AgentSkillRecord]:
    path = get_skill_registry_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AgentSkillRecord(**item) for item in data.get("skills", [])]


def write_skill_registry(skills: list[AgentSkillRecord]) -> None:
    get_skill_registry_path().write_text(
        json.dumps({"skills": [item.model_dump() for item in skills]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def retrieve_role_skills(role_key: str, query: str = "", limit: int = 12, skill_ids: list[str] | None = None) -> SkillSearchResult:
    markdown_context = read_role_skills_markdown(role_key)
    normalized_query = query.strip().lower()
    skills = [skill for skill in read_skill_registry() if skill.role_key == role_key]
    if skill_ids:
        selected = set(skill_ids)
        skills = [skill for skill in skills if skill.id in selected]
        return SkillSearchResult(skills=skills[:limit], markdown_context=markdown_context)
    if normalized_query:
        skills.sort(key=lambda item: skill_match_score(item, normalized_query), reverse=True)
        skills = [item for item in skills if skill_match_score(item, normalized_query) > 0]
    else:
        skills.sort(key=lambda item: (item.importance, item.updated_at), reverse=True)
    return SkillSearchResult(skills=skills[:limit], markdown_context=markdown_context)


def create_role_skill(role_key: str, payload: SkillCreateRequest) -> AgentSkillRecord:
    now = now_iso()
    skill = AgentSkillRecord(
        id=f"skill_{uuid4().hex[:12]}",
        role_key=role_key,
        source_type=payload.source_type,
        kind=payload.kind,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        tags=payload.tags,
        importance=payload.importance,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    skill.markdown_path = append_skill_markdown(skill)
    skills = read_skill_registry()
    skills.append(skill)
    write_skill_registry(skills)
    return skill


def skill_match_score(skill: AgentSkillRecord, query: str) -> int:
    haystack = " ".join([skill.title, skill.summary, skill.content, " ".join(skill.tags)]).lower()
    return sum(1 for token in query.split() if token in haystack)


def append_skill_markdown(skill: AgentSkillRecord) -> str:
    path = get_role_skills_dir(skill.role_key) / f"{skill.kind}.md"
    lines = [
        f"## {skill.title}",
        "",
        f"- Skill ID：`{skill.id}`",
        f"- 来源：`{skill.source_type}`",
        f"- 类型：`{skill.kind}`",
        f"- 重要度：`{skill.importance}`",
        f"- 标签：{', '.join(skill.tags) or '无'}",
        f"- 更新时间：`{skill.updated_at}`",
        "",
        "### 摘要",
        skill.summary or "无",
        "",
        "### 内容",
        skill.content,
        "",
    ]
    append_markdown(path, "\n".join(lines))
    return str(path.relative_to(find_project_root()))


def read_role_skills_markdown(role_key: str) -> str:
    role_dir = get_role_skills_dir(role_key)
    chunks: list[str] = []
    for path in sorted(role_dir.glob("*.md")):
        chunks.append(f"# {path.name}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def get_role_skills_dir(role_key: str) -> Path:
    role_dir = get_config_dir() / "skills" / safe_path_part(role_key)
    role_dir.mkdir(parents=True, exist_ok=True)
    return role_dir


def append_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    path.write_text(f"{existing}{separator}{content}\n", encoding="utf-8")


def safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "unknown"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
