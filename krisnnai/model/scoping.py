"""Tenant-scoped sessions: every SELECT is filtered by tenant_id, every INSERT is stamped with it.

Rule 8 (tenant isolation): application code gets a session only through `tenant_session`, so a
forgotten WHERE clause cannot leak another tenant's rows, and a row for the wrong tenant cannot be
written.
"""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from krisnnai.model.base import Scoped


class TenantMismatchError(Exception):
    pass


def tenant_session(bind: Engine, tenant_id: int) -> Session:
    session = Session(bind)
    session.info["tenant_id"] = tenant_id

    @event.listens_for(session, "do_orm_execute")
    def _filter(state: ORMExecuteState) -> None:
        if state.is_select and not state.is_column_load and not state.is_relationship_load:
            state.statement = state.statement.options(
                with_loader_criteria(Scoped, lambda cls: cls.tenant_id == tenant_id, include_aliases=True)
            )

    @event.listens_for(session, "before_flush")
    def _stamp(sess: Session, _ctx, _instances) -> None:
        for obj in sess.new:
            if isinstance(obj, Scoped):
                if obj.tenant_id is None:
                    obj.tenant_id = tenant_id
                elif obj.tenant_id != tenant_id:
                    raise TenantMismatchError(
                        f"{type(obj).__name__} has tenant_id {obj.tenant_id}, session is {tenant_id}"
                    )

    return session
