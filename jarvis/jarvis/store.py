"""Persistent records. PostgreSQL is the operational store. MemoryStore is the test double."""

from __future__ import annotations

import threading
import uuid
from typing import Any
from urllib.parse import quote

from jarvis.automations import AUTOMATIONS
from jarvis.clock import iso, now

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id text PRIMARY KEY,
        name text NOT NULL,
        tool text NOT NULL,
        arguments jsonb NOT NULL,
        cron text,
        timezone text NOT NULL,
        enabled boolean NOT NULL,
        approval_state text NOT NULL,
        cancelled boolean NOT NULL,
        n8n_workflow_id text,
        source text NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS executions (
        id text PRIMARY KEY,
        task_id text,
        tool text NOT NULL,
        ok boolean NOT NULL,
        execution_status text NOT NULL,
        result jsonb NOT NULL,
        started_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memories (
        id text PRIMARY KEY,
        collection text NOT NULL CHECK (collection IN ('personal', 'business', 'confidential')),
        project text,
        title text NOT NULL,
        body text NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS approvals (
        id text PRIMARY KEY,
        action text NOT NULL,
        payload jsonb NOT NULL,
        status text NOT NULL,
        created_at timestamptz NOT NULL,
        decided_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id text PRIMARY KEY,
        channel text,
        body text NOT NULL,
        status text NOT NULL,
        detail text NOT NULL,
        created_at timestamptz NOT NULL
    )
    """,
)


def _id() -> str:
    return str(uuid.uuid4())


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.tasks: dict[str, dict[str, Any]] = {}
        self.executions: list[dict[str, Any]] = []
        self.memories: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.notifications: list[dict[str, Any]] = []
        self.backend = "memory"

    def migrate(self) -> None:
        return None

    def seed_automations(self) -> None:
        with self._lock:
            existing = {item["name"] for item in self.tasks.values() if item["source"] == "initial_automation"}
            for spec in AUTOMATIONS:
                if spec["name"] in existing:
                    continue
                task_id = _id()
                moment = iso()
                self.tasks[task_id] = {
                    "id": task_id,
                    "name": spec["name"],
                    "tool": spec["tool"],
                    "arguments": dict(spec["arguments"]),
                    "cron": spec["cron"],
                    "timezone": "America/Los_Angeles",
                    "enabled": False,
                    "approval_state": "unapproved",
                    "cancelled": False,
                    "n8n_workflow_id": None,
                    "source": "initial_automation",
                    "created_at": moment,
                    "updated_at": moment,
                }

    def add_task(self, **fields: Any) -> dict[str, Any]:
        task_id = _id()
        moment = iso()
        row = {
            "id": task_id,
            "enabled": False,
            "approval_state": "unapproved",
            "cancelled": False,
            "n8n_workflow_id": None,
            "source": "user",
            "timezone": "America/Los_Angeles",
            "arguments": {},
            "cron": None,
            "created_at": moment,
            "updated_at": moment,
        }
        row.update(fields)
        row["id"] = task_id
        row["created_at"] = moment
        row["updated_at"] = moment
        with self._lock:
            self.tasks[task_id] = row
        return dict(row)

    def list_tasks(self, include_cancelled: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(item) for item in self.tasks.values()]
        if not include_cancelled:
            rows = [item for item in rows if not item["cancelled"]]
        return sorted(rows, key=lambda item: item["name"])

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.tasks.get(task_id)
            return dict(row) if row else None

    def update_task(self, task_id: str, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            row = self.tasks.get(task_id)
            if row is None:
                return None
            row.update(fields)
            row["updated_at"] = iso()
            return dict(row)

    def add_execution(self, **fields: Any) -> dict[str, Any]:
        row = {"id": _id(), "task_id": None, "started_at": iso()}
        row.update(fields)
        with self._lock:
            self.executions.append(row)
        return dict(row)

    def list_executions(
        self, limit: int = 50, task_id: str | None = None, failed_only: bool = False
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self.executions)
        if task_id:
            rows = [item for item in rows if item.get("task_id") == task_id]
        if failed_only:
            rows = [item for item in rows if not item.get("ok")]
        rows.sort(key=lambda item: item["started_at"], reverse=True)
        return [dict(item) for item in rows[:limit]]

    def add_memory(self, **fields: Any) -> dict[str, Any]:
        moment = iso()
        row = {
            "id": _id(),
            "project": None,
            "created_at": moment,
            "updated_at": moment,
        }
        row.update(fields)
        with self._lock:
            self.memories[row["id"]] = row
        return dict(row)

    def update_memory(self, memory_id: str, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            row = self.memories.get(memory_id)
            if row is None:
                return None
            row.update(fields)
            row["updated_at"] = iso()
            return dict(row)

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.memories.get(memory_id)
            return dict(row) if row else None

    def search_memories(self, query: str, collections: list[str]) -> list[dict[str, Any]]:
        needle = query.lower()
        with self._lock:
            rows = [
                dict(item)
                for item in self.memories.values()
                if item["collection"] in collections
                and (needle in item["title"].lower() or needle in item["body"].lower() or needle in (item.get("project") or "").lower())
            ]
        return rows

    def list_projects(self) -> list[str]:
        with self._lock:
            names = {(item.get("project") or "").strip() for item in self.memories.values()}
        return sorted(name for name in names if name)

    def add_approval(self, **fields: Any) -> dict[str, Any]:
        row = {"id": _id(), "status": "pending", "created_at": iso(), "decided_at": None}
        row.update(fields)
        with self._lock:
            self.approvals[row["id"]] = row
        return dict(row)

    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(item) for item in self.approvals.values()]
        if status:
            rows = [item for item in rows if item["status"] == status]
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.approvals.get(approval_id)
            return dict(row) if row else None

    def decide_approval(self, approval_id: str, status: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.approvals.get(approval_id)
            if row is None:
                return None
            row["status"] = status
            row["decided_at"] = iso()
            return dict(row)

    def add_notification(self, **fields: Any) -> dict[str, Any]:
        row = {"id": _id(), "channel": None, "created_at": iso()}
        row.update(fields)
        with self._lock:
            self.notifications.append(row)
        return dict(row)

    def list_notifications(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self.notifications)
        return [dict(item) for item in rows[-limit:]][::-1]

    def verified_notification(self) -> bool:
        with self._lock:
            return any(item["status"] == "delivered" for item in self.notifications)


class PostgresStore(MemoryStore):
    def __init__(self, dsn: str):
        super().__init__()
        self.backend = "postgres"
        self._dsn = dsn

    def _connect(self):
        import psycopg

        return psycopg.connect(self._dsn, connect_timeout=4)

    def migrate(self) -> None:
        with self._connect() as conn:
            for statement in SCHEMA:
                conn.execute(statement)
            conn.commit()

    def seed_automations(self) -> None:
        with self._connect() as conn:
            existing = {
                row[0]
                for row in conn.execute("SELECT name FROM tasks WHERE source = 'initial_automation'")
            }
            for spec in AUTOMATIONS:
                if spec["name"] in existing:
                    continue
                moment = now()
                conn.execute(
                    """
                    INSERT INTO tasks (
                        id, name, tool, arguments, cron, timezone, enabled,
                        approval_state, cancelled, n8n_workflow_id, source, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        _id(),
                        spec["name"],
                        spec["tool"],
                        _json(spec["arguments"]),
                        spec["cron"],
                        "America/Los_Angeles",
                        False,
                        "unapproved",
                        False,
                        None,
                        "initial_automation",
                        moment,
                        moment,
                    ),
                )
            conn.commit()

    def add_task(self, **fields: Any) -> dict[str, Any]:
        row = super().add_task(**fields)
        self._insert_task(row)
        with self._lock:
            self.tasks.pop(row["id"], None)
        return row

    def _insert_task(self, row: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, name, tool, arguments, cron, timezone, enabled,
                    approval_state, cancelled, n8n_workflow_id, source, created_at, updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    row["id"],
                    row["name"],
                    row["tool"],
                    _json(row["arguments"]),
                    row["cron"],
                    row["timezone"],
                    row["enabled"],
                    row["approval_state"],
                    row["cancelled"],
                    row["n8n_workflow_id"],
                    row["source"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def list_tasks(self, include_cancelled: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks"
        if not include_cancelled:
            query += " WHERE cancelled = false"
        query += " ORDER BY name"
        with self._connect() as conn:
            return [_task_row(row) for row in conn.execute(query)]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
        return _task_row(row) if row else None

    def update_task(self, task_id: str, **fields: Any) -> dict[str, Any] | None:
        current = self.get_task(task_id)
        if current is None:
            return None
        current.update(fields)
        current["updated_at"] = iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks SET name=%s, tool=%s, arguments=%s, cron=%s, timezone=%s,
                    enabled=%s, approval_state=%s, cancelled=%s, n8n_workflow_id=%s,
                    source=%s, updated_at=%s
                WHERE id=%s
                """,
                (
                    current["name"],
                    current["tool"],
                    _json(current["arguments"]),
                    current["cron"],
                    current["timezone"],
                    current["enabled"],
                    current["approval_state"],
                    current["cancelled"],
                    current["n8n_workflow_id"],
                    current["source"],
                    current["updated_at"],
                    task_id,
                ),
            )
            conn.commit()
        return current

    def add_execution(self, **fields: Any) -> dict[str, Any]:
        row = {
            "id": _id(),
            "task_id": fields.get("task_id"),
            "tool": fields["tool"],
            "ok": fields["ok"],
            "execution_status": fields["execution_status"],
            "result": fields["result"],
            "started_at": iso(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO executions (id, task_id, tool, ok, execution_status, result, started_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    row["id"],
                    row["task_id"],
                    row["tool"],
                    row["ok"],
                    row["execution_status"],
                    _json(row["result"]),
                    row["started_at"],
                ),
            )
            conn.commit()
        return row

    def list_executions(
        self, limit: int = 50, task_id: str | None = None, failed_only: bool = False
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if task_id:
            clauses.append("task_id = %s")
            params.append(task_id)
        if failed_only:
            clauses.append("ok = false")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM executions{where} ORDER BY started_at DESC LIMIT %s",
                params,
            ).fetchall()
        return [_execution_row(row) for row in rows]

    def add_memory(self, **fields: Any) -> dict[str, Any]:
        moment = iso()
        row = {
            "id": _id(),
            "collection": fields["collection"],
            "project": fields.get("project"),
            "title": fields["title"],
            "body": fields["body"],
            "created_at": moment,
            "updated_at": moment,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, collection, project, title, body, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    row["id"],
                    row["collection"],
                    row["project"],
                    row["title"],
                    row["body"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()
        return row

    def update_memory(self, memory_id: str, **fields: Any) -> dict[str, Any] | None:
        current = self.get_memory(memory_id)
        if current is None:
            return None
        current.update(fields)
        current["updated_at"] = iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memories SET collection=%s, project=%s, title=%s, body=%s, updated_at=%s
                WHERE id=%s
                """,
                (
                    current["collection"],
                    current["project"],
                    current["title"],
                    current["body"],
                    current["updated_at"],
                    memory_id,
                ),
            )
            conn.commit()
        return current

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = %s", (memory_id,)).fetchone()
        return _memory_row(row) if row else None

    def search_memories(self, query: str, collections: list[str]) -> list[dict[str, Any]]:
        if not collections:
            return []
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE collection = ANY(%s)
                  AND (
                    title ILIKE %s ESCAPE '\\'
                    OR body ILIKE %s ESCAPE '\\'
                    OR COALESCE(project, '') ILIKE %s ESCAPE '\\'
                  )
                ORDER BY updated_at DESC
                """,
                (collections, like, like, like),
            ).fetchall()
        return [_memory_row(row) for row in rows]

    def list_projects(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT project FROM memories WHERE project IS NOT NULL AND project <> '' ORDER BY project"
            ).fetchall()
        return [row[0] for row in rows]

    def add_approval(self, **fields: Any) -> dict[str, Any]:
        row = {
            "id": _id(),
            "action": fields["action"],
            "payload": fields.get("payload") or {},
            "status": fields.get("status") or "pending",
            "created_at": iso(),
            "decided_at": None,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals (id, action, payload, status, created_at, decided_at)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (row["id"], row["action"], _json(row["payload"]), row["status"], row["created_at"], None),
            )
            conn.commit()
        return row

    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM approvals WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC").fetchall()
        return [_approval_row(row) for row in rows]

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE id = %s", (approval_id,)).fetchone()
        return _approval_row(row) if row else None

    def decide_approval(self, approval_id: str, status: str) -> dict[str, Any] | None:
        current = self.get_approval(approval_id)
        if current is None:
            return None
        decided = iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE approvals SET status=%s, decided_at=%s WHERE id=%s",
                (status, decided, approval_id),
            )
            conn.commit()
        current["status"] = status
        current["decided_at"] = decided
        return current

    def add_notification(self, **fields: Any) -> dict[str, Any]:
        row = {
            "id": _id(),
            "channel": fields.get("channel"),
            "body": fields["body"],
            "status": fields["status"],
            "detail": fields.get("detail") or "",
            "created_at": iso(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notifications (id, channel, body, status, detail, created_at)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (row["id"], row["channel"], row["body"], row["status"], row["detail"], row["created_at"]),
            )
            conn.commit()
        return row

    def list_notifications(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "channel": row[1],
                "body": row[2],
                "status": row[3],
                "detail": row[4],
                "created_at": row[5].isoformat(timespec="seconds"),
            }
            for row in rows
        ]

    def verified_notification(self) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM notifications WHERE status = 'delivered' LIMIT 1"
            ).fetchone()
        return row is not None


def postgres_dsn(user: str, password: str, host: str, port: str, database: str) -> str:
    return f"postgresql://{quote(user)}:{quote(password)}@{host}:{port}/{database}"


def _json(value: Any):
    from psycopg.types.json import Json

    return Json(value)


def _task_row(row: Any) -> dict[str, Any]:
    return {
        "id": row[0],
        "name": row[1],
        "tool": row[2],
        "arguments": row[3],
        "cron": row[4],
        "timezone": row[5],
        "enabled": row[6],
        "approval_state": row[7],
        "cancelled": row[8],
        "n8n_workflow_id": row[9],
        "source": row[10],
        "created_at": row[11].isoformat(timespec="seconds"),
        "updated_at": row[12].isoformat(timespec="seconds"),
    }


def _execution_row(row: Any) -> dict[str, Any]:
    return {
        "id": row[0],
        "task_id": row[1],
        "tool": row[2],
        "ok": row[3],
        "execution_status": row[4],
        "result": row[5],
        "started_at": row[6].isoformat(timespec="seconds"),
    }


def _memory_row(row: Any) -> dict[str, Any]:
    return {
        "id": row[0],
        "collection": row[1],
        "project": row[2],
        "title": row[3],
        "body": row[4],
        "created_at": row[5].isoformat(timespec="seconds"),
        "updated_at": row[6].isoformat(timespec="seconds"),
    }


def _approval_row(row: Any) -> dict[str, Any]:
    return {
        "id": row[0],
        "action": row[1],
        "payload": row[2],
        "status": row[3],
        "created_at": row[4].isoformat(timespec="seconds"),
        "decided_at": row[5].isoformat(timespec="seconds") if row[5] else None,
    }
