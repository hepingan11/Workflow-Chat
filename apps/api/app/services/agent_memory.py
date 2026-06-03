import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - keeps Markdown memory usable before DB deps are installed.
    psycopg = None
    dict_row = None

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


def ensure_memory_store(config: MemoryStorageSettings | None = None) -> bool:
    config = config or read_memory_settings()
    if not config.database_url:
        return False
    if psycopg is None:
        raise RuntimeError("psycopg is required when DATABASE_URL is configured")
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
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
                    tags jsonb not null default '[]'::jsonb,
                    importance integer not null default 3,
                    markdown_path text,
                    metadata jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null,
                    updated_at timestamptz not null
                )
                """
            )
            cursor.execute(
                """
                create index if not exists idx_agent_memories_role_kind
                on agent_memories(role_key, kind)
                """
            )
            cursor.execute(
                """
                create index if not exists idx_agent_memories_search
                on agent_memories using gin (
                    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(content, ''))
                )
                """
            )
            cursor.execute(
                """
                create table if not exists agent_task_memories (
                    id text primary key,
                    role_key text not null,
                    task_id text not null,
                    task_title text not null,
                    user_input text not null default '',
                    execution_summary text not null default '',
                    status text not null default '',
                    raw_payload jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null,
                    completed_at timestamptz
                )
                """
            )
            cursor.execute(
                """
                create index if not exists idx_agent_task_memories_role_task
                on agent_task_memories(role_key, task_id)
                """
            )
        connection.commit()
    return True


def retrieve_role_memory(role_key: str, query: str, limit: int = 8) -> MemorySearchResult:
    config = read_memory_settings()
    markdown_context = read_role_memory_markdown(role_key)
    memories: list[AgentMemoryRecord] = []
    if config.database_url:
        ensure_memory_store(config)
        if psycopg is None:
            return MemorySearchResult(memories=memories, markdown_context=markdown_context)
        with psycopg.connect(config.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select *
                    from agent_memories
                    where role_key = %s
                    order by
                        ts_rank(
                            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(content, '')),
                            plainto_tsquery('simple', %s)
                        ) desc,
                        importance desc,
                        updated_at desc
                    limit %s
                    """,
                    (role_key, query or role_key, limit),
                )
                memories = [row_to_memory_record(row) for row in cursor.fetchall()]
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
    if config.database_url:
        ensure_memory_store(config)
        insert_memory_record(record, config)
    return record


def record_completed_run_memory(run: PlaybookRun) -> TaskReflectionResult | None:
    if run.status not in {"completed", "cancelled", "failed"}:
        return None

    task = build_task_record(run)
    memories = reflect_run_into_memories(run)
    append_task_markdown(task, memories)

    config = read_memory_settings()
    if config.database_url:
        ensure_memory_store(config)
        insert_task_record(task, config)
        for memory in memories:
            insert_memory_record(memory, config)

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
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into agent_memories (
                    id, role_key, kind, title, summary, content, source_type, source_id,
                    tags, importance, markdown_path, metadata, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s)
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
        connection.commit()


def insert_task_record(record: AgentTaskMemoryRecord, config: MemoryStorageSettings | None = None) -> None:
    config = config or read_memory_settings()
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into agent_task_memories (
                    id, role_key, task_id, task_title, user_input, execution_summary,
                    status, raw_payload, created_at, completed_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
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
        connection.commit()


def row_to_memory_record(row: dict) -> AgentMemoryRecord:
    data = dict(row)
    data["created_at"] = data["created_at"].isoformat()
    data["updated_at"] = data["updated_at"].isoformat()
    return AgentMemoryRecord(**data)


def safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "unknown"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
