from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

import app.db.base  # noqa: F401 — registers all SQLModel table metadata so mapper can resolve string relationships


class FakeResult:
    def __init__(self, value: Any) -> None:
        self.value = value

    def all(self) -> Any:
        return self.value

    def first(self) -> Any:
        return self.value

    def one(self) -> Any:
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    def one_or_none(self) -> Any:
        return self.value


class FakeAsyncSession:
    def __init__(self, *, exec_results: list[Any] | None = None, get_results: list[Any] | None = None) -> None:
        self.exec_results = list(exec_results or [])
        self.get_results = list(get_results or [])
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.commits = 0
        self.refreshes: list[Any] = []
        self.rollbacks = 0

    async def exec(self, _statement: Any) -> FakeResult:
        if not self.exec_results:
            raise AssertionError("Unexpected exec() call")
        value = self.exec_results.pop(0)
        return FakeResult(value)

    async def get(self, _model: Any, _pk: Any) -> Any:
        if not self.get_results:
            return None
        return self.get_results.pop(0)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def add_all(self, objects: list[Any]) -> None:
        self.added.extend(objects)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        self.refreshes.append(obj)

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        self.rollbacks += 1


def run_async(awaitable: Awaitable[Any]) -> Any:
    return asyncio.run(awaitable)
