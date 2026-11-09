"""Shared building blocks for tenant (church) owned tables.

Every tenant-owned table carries a NOT NULL ``church_id``. References between two
tenant-owned rows use *composite* foreign keys ``(<col>, church_id)`` so the
database itself refuses a row that points at another church's data (a plain FK
only checks the id, and Postgres FK checks bypass row-level security).

Foreign keys to ``users`` stay plain: users are a global identity, and whether a
user belongs to the church is checked through ``memberships`` in application code.
"""
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr


class ChurchScoped:
    """Mixin adding the mandatory ``church_id`` tenant column."""

    @declared_attr
    def church_id(cls):  # noqa: N805 - SQLAlchemy declared_attr convention
        # No ondelete: deleting a church with data must fail loudly. Account
        # closure (Phase 8) deletes tenant data explicitly and in order.
        return Column(UUID(as_uuid=True), ForeignKey("churches.id"), nullable=False)


def id_church_unique(table: str) -> UniqueConstraint:
    """``UNIQUE (id, church_id)``: the target a same-church composite FK needs."""
    return UniqueConstraint("id", "church_id", name=f"uq_{table}_id_church_id")


def same_church_fk(table: str, column: str, target: str, ondelete: str | None = None) -> ForeignKeyConstraint:
    """Composite FK ``(column, church_id) -> target(id, church_id)``.

    Replaces the plain ``column -> target.id`` FK. ``column`` may be NULL (the
    constraint is then not checked, standard MATCH SIMPLE behaviour).
    """
    return ForeignKeyConstraint(
        [column, "church_id"],
        [f"{target}.id", f"{target}.church_id"],
        ondelete=ondelete,
        name=f"fk_{table}_{column}_same_church",
    )
