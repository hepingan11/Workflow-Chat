import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import find_project_root
from app.schemas.skills import AgentSkillRecord, SkillCreateRequest, SkillPackageFile, SkillSearchResult, SkillUpdateRequest
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
    if payload.package_files:
        skill.metadata = {**skill.metadata, **persist_skill_package(role_key, skill.id, payload.package_files)}
    skill.markdown_path = append_skill_markdown(skill)
    skills = read_skill_registry()
    skills.append(skill)
    write_skill_registry(skills)
    return skill


def update_role_skill(role_key: str, skill_id: str, payload: SkillUpdateRequest) -> AgentSkillRecord | None:
    skills = read_skill_registry()
    updated_skill: AgentSkillRecord | None = None
    for index, skill in enumerate(skills):
        if skill.role_key != role_key or skill.id != skill_id:
            continue
        patch = payload.model_dump(exclude_unset=True)
        package_files = patch.pop("package_files", None)
        next_data = skill.model_dump()
        next_data.update(patch)
        if package_files is not None:
            package_file_models = [SkillPackageFile(**item) if isinstance(item, dict) else item for item in package_files]
            metadata = next_data.get("metadata") if isinstance(next_data.get("metadata"), dict) else {}
            next_data["metadata"] = {**metadata, **persist_skill_package(role_key, skill_id, package_file_models)}
        next_data["updated_at"] = now_iso()
        updated_skill = AgentSkillRecord(**next_data)
        skills[index] = updated_skill
        break
    if updated_skill is None:
        return None
    write_skill_registry(skills)
    rewrite_role_skill_markdown(role_key, skills)
    return updated_skill


def delete_role_skill(role_key: str, skill_id: str) -> bool:
    skills = read_skill_registry()
    next_skills = [skill for skill in skills if not (skill.role_key == role_key and skill.id == skill_id)]
    if len(next_skills) == len(skills):
        return False
    delete_skill_package_dir(role_key, skill_id)
    write_skill_registry(next_skills)
    rewrite_role_skill_markdown(role_key, next_skills)
    return True


def skill_match_score(skill: AgentSkillRecord, query: str) -> int:
    metadata = skill.metadata if isinstance(skill.metadata, dict) else {}
    package_paths = " ".join(str(item) for item in metadata.get("package_file_paths", []))
    haystack = " ".join([skill.title, skill.summary, skill.content, " ".join(skill.tags), package_paths]).lower()
    return sum(1 for token in query.split() if token in haystack)


def append_skill_markdown(skill: AgentSkillRecord) -> str:
    path = get_role_skills_dir(skill.role_key) / f"{skill.kind}.md"
    metadata = skill.metadata if isinstance(skill.metadata, dict) else {}
    package_root = str(metadata.get("package_root") or "")
    package_file_paths = [str(item) for item in metadata.get("package_file_paths", []) if item]
    script_paths = [str(item) for item in metadata.get("script_paths", []) if item]
    entry_path = str(metadata.get("entry_path") or "")
    lines = [
        f"## {skill.title}",
        "",
        f"- Skill ID: `{skill.id}`",
        f"- 来源: `{skill.source_type}`",
        f"- 类型: `{skill.kind}`",
        f"- 重要度: `{skill.importance}`",
        f"- 标签: {', '.join(skill.tags) or '无'}",
        f"- 更新时间: `{skill.updated_at}`",
    ]
    if package_root:
        lines.extend(
            [
                f"- Skill 包目录: `{package_root}`",
                f"- 入口文件: `{entry_path or '未指定'}`",
            ]
        )
    if package_file_paths:
        lines.extend(["", "### 文件清单", *[f"- `{item}`" for item in package_file_paths]])
    if script_paths:
        lines.extend(["", "### 可执行脚本", *[f"- `{item}`" for item in script_paths]])
    lines.extend(
        [
            "",
            "### 摘要",
            skill.summary or "无",
            "",
            "### 内容",
            skill.content,
            "",
        ]
    )
    append_markdown(path, "\n".join(lines))
    return str(path.relative_to(find_project_root()))


def rewrite_role_skill_markdown(role_key: str, skills: list[AgentSkillRecord] | None = None) -> None:
    role_dir = get_role_skills_dir(role_key)
    for path in role_dir.glob("*.md"):
        path.unlink()
    role_skills = [skill for skill in (skills or read_skill_registry()) if skill.role_key == role_key]
    changed = False
    for skill in sorted(role_skills, key=lambda item: (item.kind, item.updated_at)):
        next_path = append_skill_markdown(skill)
        if skill.markdown_path != next_path:
            skill.markdown_path = next_path
            changed = True
    if skills is not None and changed:
        write_skill_registry(skills)


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


def get_role_skill_packages_dir(role_key: str) -> Path:
    packages_dir = get_config_dir() / "skill-packages" / safe_path_part(role_key)
    packages_dir.mkdir(parents=True, exist_ok=True)
    return packages_dir


def persist_skill_package(role_key: str, skill_id: str, files: list[SkillPackageFile]) -> dict:
    safe_files = [(sanitize_relative_path(file.path), file) for file in files]
    safe_files = [(path, file) for path, file in safe_files if path]
    if not safe_files:
        return {}
    rewrite_skill_package_dir(role_key, skill_id, [file for _, file in safe_files])
    package_root = get_role_skill_packages_dir(role_key) / safe_path_part(skill_id)
    paths = [path for path, _ in safe_files]
    script_paths = [path for path in paths if is_script_path(path)]
    return {
        "package_root": str(package_root.relative_to(find_project_root())),
        "package_file_paths": paths,
        "script_paths": script_paths,
        "entry_path": choose_skill_entry_path(paths),
        "package_file_count": len(paths),
    }


def rewrite_skill_package_dir(role_key: str, skill_id: str, files: list[SkillPackageFile]) -> None:
    package_dir = get_role_skill_packages_dir(role_key) / safe_path_part(skill_id)
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        safe_path = sanitize_relative_path(file.path)
        if not safe_path:
            continue
        target = package_dir / safe_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file.content, encoding="utf-8")


def delete_skill_package_dir(role_key: str, skill_id: str) -> None:
    package_dir = get_role_skill_packages_dir(role_key) / safe_path_part(skill_id)
    if package_dir.exists():
        shutil.rmtree(package_dir)


def sanitize_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip().lstrip("/")
    parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]
    return "/".join(parts)


def is_script_path(value: str) -> bool:
    return Path(value).suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".ps1", ".bat", ".cmd"}


def choose_skill_entry_path(paths: list[str]) -> str:
    lowered = {path.lower(): path for path in paths}
    for candidate in ("skill.md", "readme.md", "editing.md"):
        if candidate in lowered:
            return lowered[candidate]
    for path in paths:
        if path.lower().endswith(".md"):
            return path
    return paths[0] if paths else ""


def append_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    path.write_text(f"{existing}{separator}{content}\n", encoding="utf-8")


def safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "unknown"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
