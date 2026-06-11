import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import find_project_root, settings
from app.schemas.memory import (
    AgentMemoryRecord,
    AgentTaskMemoryRecord,
    MemoryCreateRequest,
    MemorySearchResult,
    TaskReflectionResult,
)
from app.schemas.playbooks import PlaybookRun
from app.schemas.settings import MemoryStorageSettings
from app.services.memory_settings import read_memory_settings
from app.services.prompt_config import get_config_dir


MEMORY_COMPRESSION_INTERVAL = 10


# ---------------------------------------------------------------------------
# SQLite structured index
#
# Markdown remains the human-readable source of truth; SQLite is an always-on
# structured index that provides ranked top-N retrieval. No external service is
# required — the database is a single file under the local config directory.
# ---------------------------------------------------------------------------


def get_memory_db_path(config: MemoryStorageSettings | None = None) -> Path:
    config = config or read_memory_settings()
    raw = (config.sqlite_path or settings.memory_db_path).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = find_project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect_memory_db(config: MemoryStorageSettings | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(get_memory_db_path(config)), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma journal_mode=WAL")
    connection.execute("pragma busy_timeout=5000")
    return connection


def ensure_memory_store(config: MemoryStorageSettings | None = None) -> bool:
    config = config or read_memory_settings()
    with closing(connect_memory_db(config)) as connection:
        with connection:
            connection.executescript(
                """
                create table if not exists agent_memories (
                    id text primary key,
                    role_key text not null,
                    kind text not null,
                    title text not null,
                    summary text not null default '',
                    content text not null,
                    source_type text not null default 'manual',
                    source_id text,
                    tags text not null default '[]',
                    importance integer not null default 3,
                    markdown_path text,
                    metadata text not null default '{}',
                    created_at text not null,
                    updated_at text not null
                );

                create index if not exists idx_agent_memories_role_kind
                    on agent_memories(role_key, kind);

                create table if not exists agent_task_memories (
                    id text primary key,
                    role_key text not null,
                    task_id text not null,
                    task_title text not null,
                    user_input text not null default '',
                    execution_summary text not null default '',
                    status text not null default '',
                    raw_payload text not null default '{}',
                    created_at text not null,
                    completed_at text
                );

                create index if not exists idx_agent_task_memories_role_task
                    on agent_task_memories(role_key, task_id);
                """
            )
    return True


def search_role_memories(
    role_key: str,
    query: str,
    limit: int,
    config: MemoryStorageSettings | None = None,
) -> list[AgentMemoryRecord]:
    config = config or read_memory_settings()
    tokens = [token for token in re.split(r"\s+", (query or "").strip()) if token]
    with closing(connect_memory_db(config)) as connection:
        if not tokens:
            rows = connection.execute(
                """
                select * from agent_memories
                where role_key = ?
                order by importance desc, updated_at desc
                limit ?
                """,
                (role_key, limit),
            ).fetchall()
            return [row_to_memory_record(row) for row in rows]

        score_terms: list[str] = []
        params: list[object] = []
        for token in tokens:
            like = f"%{token}%"
            # Weighted relevance: title matches outrank summary, which outrank body.
            score_terms.append("((title like ?) * 3 + (summary like ?) * 2 + (content like ?))")
            params.extend([like, like, like])
        score_expr = " + ".join(score_terms)
        sql = f"""
            select *, ({score_expr}) as score
            from agent_memories
            where role_key = ?
            order by score desc, importance desc, updated_at desc
            limit ?
        """
        params.extend([role_key, limit])
        rows = connection.execute(sql, params).fetchall()

    matched = [row for row in rows if (row["score"] or 0) > 0]
    selected = matched or rows[:limit]
    return [row_to_memory_record(row) for row in selected]


def retrieve_role_memory(role_key: str, query: str, limit: int = 8) -> MemorySearchResult:
    config = read_memory_settings()
    markdown_context = read_role_memory_markdown(role_key)
    ensure_memory_store(config)
    memories = search_role_memories(role_key, query, limit, config)
    return MemorySearchResult(memories=memories, markdown_context=markdown_context)


def create_role_memory(role_key: str, payload: MemoryCreateRequest) -> AgentMemoryRecord:
    now = now_iso()
    record = AgentMemoryRecord(
        id=f"mem_{uuid4().hex[:12]}",
        role_key=role_key,
        kind=payload.kind,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        source_type=payload.source_type,
        source_id=payload.source_id,
        tags=payload.tags,
        importance=payload.importance,
        metadata=payload.metadata,
        markdown_path=None,
        created_at=now,
        updated_at=now,
    )
    record.markdown_path = append_memory_markdown(record)
    config = read_memory_settings()
    ensure_memory_store(config)
    insert_memory_record(record, config)
    return record


def record_completed_run_memory(run: PlaybookRun) -> TaskReflectionResult | None:
    if run.status != "completed":
        return None

    task = build_task_record(run)
    memories = reflect_run_into_memories(run)
    append_task_markdown(task, memories)

    config = read_memory_settings()
    ensure_memory_store(config)
    insert_task_record(task, config)
    for memory in memories:
        insert_memory_record(memory, config)

    if increment_successful_task_count(run.role_key) >= MEMORY_COMPRESSION_INTERVAL:
        compact_role_memory(run.role_key, task, memories, config)
        reset_successful_task_count(run.role_key)

    return TaskReflectionResult(task=task, memories=memories)


def build_task_record(run: PlaybookRun) -> AgentTaskMemoryRecord:
    now = now_iso()
    return AgentTaskMemoryRecord(
        id=f"task_mem_{uuid4().hex[:12]}",
        role_key=run.role_key,
        task_id=run.id,
        task_title=str(run.shared_context.get("playbook_name") or run.playbook_id),
        user_input=str(run.shared_context.get("natural_language") or ""),
        execution_summary=summarize_run(run),
        status=run.status,
        raw_payload=run.model_dump(),
        created_at=run.updated_at or now,
        completed_at=now,
    )


def reflect_run_into_memories(run: PlaybookRun) -> list[AgentMemoryRecord]:
    now = now_iso()
    title = str(run.shared_context.get("playbook_name") or run.playbook_id)
    natural_language = str(run.shared_context.get("natural_language") or "")
    completed_steps = [step for step in run.steps if step.status == "completed"]
    failed_steps = [step for step in run.steps if step.status == "failed"]
    memories = [
        AgentMemoryRecord(
            id=f"mem_{uuid4().hex[:12]}",
            role_key=run.role_key,
            kind="episodic",
            title=f"任务经验：{title}",
            summary=summarize_run(run),
            content=build_episodic_content(run, natural_language),
            source_type="playbook_run",
            source_id=run.id,
            tags=["task", run.status],
            importance=4 if failed_steps else 3,
            markdown_path=None,
            metadata={"playbook_id": run.playbook_id, "completed_steps": len(completed_steps), "failed_steps": len(failed_steps)},
            created_at=now,
            updated_at=now,
        )
    ]
    if failed_steps:
        memories.append(
            AgentMemoryRecord(
                id=f"mem_{uuid4().hex[:12]}",
                role_key=run.role_key,
                kind="pitfall",
                title=f"避坑点：{title}",
                summary="本次任务出现失败节点，后续执行类似任务前需要先检查工具配置、输入字段和外部服务状态。",
                content=build_failed_steps_content(failed_steps),
                source_type="playbook_run",
                source_id=run.id,
                tags=["pitfall", "failed"],
                importance=5,
                markdown_path=None,
                metadata={"playbook_id": run.playbook_id},
                created_at=now,
                updated_at=now,
            )
        )
    for memory in memories:
        memory.markdown_path = append_memory_markdown(memory)
    return memories


def get_memory_compaction_state_path() -> Path:
    return get_config_dir() / "memory-compaction-state.json"


def read_memory_compaction_state() -> dict:
    path = get_memory_compaction_state_path()
    if not path.exists():
        return {"roles": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"roles": {}}


def write_memory_compaction_state(state: dict) -> None:
    get_memory_compaction_state_path().write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def increment_successful_task_count(role_key: str) -> int:
    state = read_memory_compaction_state()
    roles = state.setdefault("roles", {})
    role_state = roles.setdefault(role_key, {"successful_since_compaction": 0, "last_compacted_at": None})
    role_state["successful_since_compaction"] = int(role_state.get("successful_since_compaction") or 0) + 1
    write_memory_compaction_state(state)
    return role_state["successful_since_compaction"]


def reset_successful_task_count(role_key: str) -> None:
    state = read_memory_compaction_state()
    roles = state.setdefault("roles", {})
    role_state = roles.setdefault(role_key, {})
    role_state["successful_since_compaction"] = 0
    role_state["last_compacted_at"] = now_iso()
    write_memory_compaction_state(state)


def compact_role_memory_now(role_key: str) -> dict:
    config = read_memory_settings()
    now = now_iso()
    task = AgentTaskMemoryRecord(
        id=f"task_mem_{uuid4().hex[:12]}",
        role_key=role_key,
        task_id=f"manual_compaction_{uuid4().hex[:8]}",
        task_title="手动压缩/清理长期记忆库",
        user_input="用户手动触发当前员工知识库清理与压缩。",
        execution_summary="已归档原始任务流水，清理失败/未压缩任务记忆，并生成压缩知识库摘要。",
        status="completed",
        raw_payload={"manual": True, "compacted_at": now},
        created_at=now,
        completed_at=now,
    )
    compact_role_memory(role_key, task, [], config)
    reset_successful_task_count(role_key)
    return {
        "ok": True,
        "role_key": role_key,
        "message": "当前员工长期记忆库已清理并压缩。",
        "compacted_at": now,
    }


def compact_role_memory(
    role_key: str,
    latest_task: AgentTaskMemoryRecord,
    latest_memories: list[AgentMemoryRecord],
    config: MemoryStorageSettings,
) -> None:
    role_dir = get_role_memory_dir(role_key)
    compacted_at = now_iso()
    raw_sections = collect_raw_memory_sections(role_dir)
    compacted_content = build_compacted_memory_markdown(role_key, latest_task, latest_memories, raw_sections, compacted_at)
    archive_raw_memory_files(role_dir, compacted_at)
    compacted_path = role_dir / "compacted.md"
    append_markdown(compacted_path, compacted_content)

    compacted_record = AgentMemoryRecord(
        id=f"mem_{uuid4().hex[:12]}",
        role_key=role_key,
        kind="semantic",
        title=f"压缩知识库：{role_key} / {compacted_at}",
        summary=f"已将最近 {MEMORY_COMPRESSION_INTERVAL} 次成功任务沉淀压缩为稳定经验摘要。",
        content=compacted_content,
        source_type="memory_compaction",
        source_id=latest_task.task_id,
        tags=["compacted", "successful_tasks"],
        importance=5,
        markdown_path=str(compacted_path.relative_to(find_project_root())),
        metadata={"interval": MEMORY_COMPRESSION_INTERVAL, "latest_task_id": latest_task.task_id},
        created_at=compacted_at,
        updated_at=compacted_at,
    )

    ensure_memory_store(config)
    delete_uncompressed_task_memories(role_key, config)
    delete_failed_task_memory_records(role_key, config)
    insert_memory_record(compacted_record, config)


def collect_raw_memory_sections(role_dir: Path) -> dict[str, str]:
    sections: dict[str, str] = {}
    for name in ["tasks.md", "episodic.md", "pitfall.md"]:
        path = role_dir / name
        if path.exists():
            sections[name] = path.read_text(encoding="utf-8")
    return sections


def build_compacted_memory_markdown(
    role_key: str,
    latest_task: AgentTaskMemoryRecord,
    latest_memories: list[AgentMemoryRecord],
    raw_sections: dict[str, str],
    compacted_at: str,
) -> str:
    task_headings = extract_markdown_headings(raw_sections.get("tasks.md", ""), limit=20)
    memory_summaries = [
        f"- [{memory.kind}] {memory.title}: {memory.summary or memory.content[:160]}"
        for memory in latest_memories
    ]
    historical_signals = extract_signal_lines("\n\n".join(raw_sections.values()), limit=24)
    lines = [
        f"# {role_key} 压缩知识库",
        "",
        f"- 压缩时间：`{compacted_at}`",
        f"- 压缩策略：每 {MEMORY_COMPRESSION_INTERVAL} 次成功任务保留一次稳定摘要；失败任务不进入知识库。",
        f"- 最近任务：`{latest_task.task_title}` / `{latest_task.task_id}`",
        "",
        "## 稳定经验",
        *(memory_summaries or ["- 暂无可提炼经验。"]),
        "",
        "## 最近成功任务索引",
        *(task_headings or [f"- {latest_task.task_title}"]),
        "",
        "## 可复用信号",
        *(historical_signals or ["- 暂无额外信号。"]),
        "",
        "## 使用原则",
        "- 优先复用这里的稳定经验、偏好、流程和避坑点。",
        "- 不要把单次执行流水当成长期事实，除非它在多次任务中重复出现。",
        "- 如果新任务与旧经验冲突，以最近一次成功任务和人工上传知识为准。",
        "",
    ]
    return "\n".join(lines)


def extract_markdown_headings(markdown: str, limit: int) -> list[str]:
    headings = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            headings.append(f"- {line[3:].strip()}")
    return headings[-limit:]


def extract_signal_lines(text: str, limit: int) -> list[str]:
    signals = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(keyword in stripped for keyword in ["复盘", "建议", "优先", "确保", "工具", "消息", "审批", "输入", "输出"]):
            signals.append(f"- {stripped.lstrip('- ')}")
    deduped = list(dict.fromkeys(signals))
    return deduped[-limit:]


def archive_raw_memory_files(role_dir: Path, compacted_at: str) -> None:
    archive_dir = role_dir / "archive" / safe_path_part(compacted_at)
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ["tasks.md", "episodic.md", "pitfall.md"]:
        path = role_dir / name
        if path.exists():
            path.replace(archive_dir / name)


def delete_uncompressed_task_memories(role_key: str, config: MemoryStorageSettings) -> None:
    with closing(connect_memory_db(config)) as connection:
        with connection:
            connection.execute(
                """
                delete from agent_memories
                where role_key = ?
                  and source_type = 'playbook_run'
                """,
                (role_key,),
            )


def delete_failed_task_memory_records(role_key: str, config: MemoryStorageSettings) -> None:
    with closing(connect_memory_db(config)) as connection:
        with connection:
            connection.execute(
                """
                delete from agent_task_memories
                where role_key = ?
                  and status <> 'completed'
                """,
                (role_key,),
            )


def summarize_run(run: PlaybookRun) -> str:
    completed = sum(1 for step in run.steps if step.status == "completed")
    failed = sum(1 for step in run.steps if step.status == "failed")
    waiting = sum(1 for step in run.steps if step.status == "waiting_approval")
    return f"运行状态：{run.status}；完成节点：{completed}；失败节点：{failed}；等待审批节点：{waiting}。"


def build_episodic_content(run: PlaybookRun, natural_language: str) -> str:
    lines = [
        f"原始任务：{natural_language or '无'}",
        f"运行 ID：{run.id}",
        f"调度时间：{run.scheduled_for}",
        "",
        "节点结果：",
    ]
    for step in run.steps:
        lines.append(f"- {step.name} [{step.type}]：{step.status}")
        if step.error:
            lines.append(f"  错误：{step.error}")
    lines.extend(
        [
            "",
            "自动复盘：",
            "- 下次执行前优先复用本次任务的输入结构和上下文读写方式。",
            "- 如果涉及外部工具，先确认工具授权、API Key、输入字段和返回格式。",
            "- 如果涉及消息推送或审批，确保老板设定和员工角色提示词已更新。",
        ]
    )
    return "\n".join(lines)


def build_failed_steps_content(failed_steps) -> str:
    lines = ["失败节点："]
    for step in failed_steps:
        lines.append(f"- {step.name}：{step.error or '未知错误'}")
    lines.append("")
    lines.append("建议：先检查工具配置、模型接口、通知配置和上游节点输出是否为空。")
    return "\n".join(lines)


def append_task_markdown(task: AgentTaskMemoryRecord, memories: list[AgentMemoryRecord]) -> Path:
    path = get_role_memory_dir(task.role_key) / "tasks.md"
    lines = [
        f"## {task.task_title}",
        "",
        f"- 任务 ID：`{task.task_id}`",
        f"- 状态：`{task.status}`",
        f"- 完成时间：`{task.completed_at}`",
        "",
        "### 用户问题",
        task.user_input or "无",
        "",
        "### 执行摘要",
        task.execution_summary,
        "",
        "### 自动复盘记忆",
    ]
    for memory in memories:
        lines.append(f"- [{memory.kind}] {memory.title}：{memory.summary}")
    lines.append("")
    append_markdown(path, "\n".join(lines))
    return path


def append_memory_markdown(memory: AgentMemoryRecord) -> str:
    path = get_role_memory_dir(memory.role_key) / f"{memory.kind}.md"
    lines = [
        f"## {memory.title}",
        "",
        f"- 记忆 ID：`{memory.id}`",
        f"- 来源：`{memory.source_type}` / `{memory.source_id or 'manual'}`",
        f"- 重要度：`{memory.importance}`",
        f"- 标签：{', '.join(memory.tags) or '无'}",
        f"- 更新时间：`{memory.updated_at}`",
        "",
        "### 摘要",
        memory.summary or "无",
        "",
        "### 内容",
        memory.content,
        "",
    ]
    append_markdown(path, "\n".join(lines))
    return str(path.relative_to(find_project_root()))


def read_role_memory_markdown(role_key: str) -> str:
    role_dir = get_role_memory_dir(role_key)
    chunks: list[str] = []
    for path in sorted(role_dir.glob("*.md")):
        chunks.append(f"# {path.name}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def get_role_memory_dir(role_key: str) -> Path:
    config = read_memory_settings()
    path = Path(config.markdown_dir or settings.memory_markdown_dir)
    if not path.is_absolute():
        path = find_project_root() / path
    role_dir = path / safe_path_part(role_key)
    role_dir.mkdir(parents=True, exist_ok=True)
    return role_dir


def append_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "\n\n---\n\n" if existing.strip() else ""
    path.write_text(f"{existing}{separator}{content}\n", encoding="utf-8")


def insert_memory_record(record: AgentMemoryRecord, config: MemoryStorageSettings | None = None) -> None:
    config = config or read_memory_settings()
    with closing(connect_memory_db(config)) as connection:
        with connection:
            connection.execute(
                """
                insert into agent_memories (
                    id, role_key, kind, title, summary, content, source_type, source_id,
                    tags, importance, markdown_path, metadata, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict (id) do nothing
                """,
                (
                    record.id,
                    record.role_key,
                    record.kind,
                    record.title,
                    record.summary,
                    record.content,
                    record.source_type,
                    record.source_id,
                    json.dumps(record.tags, ensure_ascii=False),
                    record.importance,
                    record.markdown_path,
                    json.dumps(record.metadata, ensure_ascii=False),
                    record.created_at,
                    record.updated_at,
                ),
            )


def insert_task_record(record: AgentTaskMemoryRecord, config: MemoryStorageSettings | None = None) -> None:
    config = config or read_memory_settings()
    with closing(connect_memory_db(config)) as connection:
        with connection:
            connection.execute(
                """
                insert into agent_task_memories (
                    id, role_key, task_id, task_title, user_input, execution_summary,
                    status, raw_payload, created_at, completed_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict (id) do nothing
                """,
                (
                    record.id,
                    record.role_key,
                    record.task_id,
                    record.task_title,
                    record.user_input,
                    record.execution_summary,
                    record.status,
                    json.dumps(record.raw_payload, ensure_ascii=False),
                    record.created_at,
                    record.completed_at,
                ),
            )


def row_to_memory_record(row) -> AgentMemoryRecord:
    data = dict(row)
    data.pop("score", None)
    if isinstance(data.get("tags"), str):
        data["tags"] = json.loads(data["tags"] or "[]")
    if isinstance(data.get("metadata"), str):
        data["metadata"] = json.loads(data["metadata"] or "{}")
    return AgentMemoryRecord(**data)


def safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "unknown"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
