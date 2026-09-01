"""Request-local account scope for account-owned ORM records."""
from __future__ import annotations

import contextvars
import uuid

from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria
from sqlalchemy.dialects.postgresql import UUID

_current_account_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "app_current_account_id", default=None
)


class AccountOwned:
    """Mixin for data that may only be read or written in an account scope."""

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True
    )


def set_current_account(account_id: uuid.UUID) -> contextvars.Token:
    return _current_account_id.set(account_id)


def reset_current_account(token: contextvars.Token) -> None:
    _current_account_id.reset(token)


def current_account_id() -> uuid.UUID | None:
    return _current_account_id.get()


@event.listens_for(Session, "do_orm_execute")
def _apply_account_scope(execute_state) -> None:
    account_id = current_account_id()
    if account_id is None or execute_state.execution_options.get("include_all_accounts"):
        return
    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                AccountOwned,
                lambda entity: entity.account_id == account_id,
                include_aliases=True,
            )
        )


@event.listens_for(Session, "before_flush")
def _assign_new_records_to_current_account(session: Session, _flush_context, _instances) -> None:
    account_id = current_account_id()
    if account_id is None:
        return
    for instance in session.new:
        if isinstance(instance, AccountOwned) and instance.account_id is None:
            instance.account_id = account_id
