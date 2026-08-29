"""Link safety checks to a verification record (Module 2, Phase 3)

Adds the two columns the combined prescription pipeline needs:

* `source`                  — whether the checked list was the user's own
                              curated list or one read off a document by OCR.
* `verification_record_id`  — the forensics record produced from the same
                              upload, so one report can show the tamper verdict
                              and the medication findings together.

Existing rows predate the pipeline and are all user-curated lists, so `source`
backfills to 'list' and `verification_record_id` stays NULL.

Revision ID: b3d71c4e9a20
Revises: ac2fe91fc0f3
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3d71c4e9a20'
down_revision: Union[str, Sequence[str], None] = 'ac2fe91fc0f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PostgreSQL needs the enum type to exist before a column can reference it;
# SQLite has no enum type and renders this as VARCHAR + a CHECK constraint.
SOURCE_ENUM = sa.Enum('list', 'prescription', name='safety_check_source')


def upgrade() -> None:
    """Upgrade schema."""
    SOURCE_ENUM.create(op.get_bind(), checkfirst=True)

    # batch_alter_table so this also applies on SQLite, which cannot ALTER a
    # column in place and has to rebuild the table instead.
    with op.batch_alter_table('safety_checks', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'source', SOURCE_ENUM, nullable=False, server_default='list',
        ))
        batch_op.add_column(sa.Column(
            'verification_record_id', sa.UUID(as_uuid=True), nullable=True,
        ))
        batch_op.create_foreign_key(
            'fk_safety_checks_verification_record_id',
            'verification_records',
            ['verification_record_id'], ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index(
            'ix_safety_checks_verification_record',
            ['verification_record_id'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('safety_checks', schema=None) as batch_op:
        batch_op.drop_index('ix_safety_checks_verification_record')
        batch_op.drop_constraint(
            'fk_safety_checks_verification_record_id', type_='foreignkey',
        )
        batch_op.drop_column('verification_record_id')
        batch_op.drop_column('source')

    SOURCE_ENUM.drop(op.get_bind(), checkfirst=True)
