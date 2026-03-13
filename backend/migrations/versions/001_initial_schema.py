"""Initial schema - all core tables for Crawtopia

Revision ID: 001_initial
Revises:
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="openclaw"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active", index=True),
        sa.Column("capabilities", JSONB, server_default="[]"),
        sa.Column("preferred_roles", JSONB, server_default="[]"),
        sa.Column("auth_token_hash", sa.String(255), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True)),
    )

    # Roles
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("division", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.String(2000)),
        sa.Column("max_slots", sa.Integer, nullable=False, server_default="1"),
        sa.Column("requires_election", sa.Boolean, server_default="false"),
        sa.Column("requires_appointment", sa.Boolean, server_default="false"),
        sa.Column("required_capabilities", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Role Assignments
    op.create_table(
        "role_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("assignment_type", sa.String(50), nullable=False, server_default="application"),
        sa.Column("assigned_by", UUID(as_uuid=True), sa.ForeignKey("agents.id")),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )

    # Elections
    op.create_table(
        "elections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("election_type", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="scheduled", index=True),
        sa.Column("cycle_number", sa.Integer, nullable=False, server_default="0"),
        sa.Column("nomination_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voting_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voting_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("certified_at", sa.DateTime(timezone=True)),
        sa.Column("results", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Candidates
    op.create_table(
        "candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("election_id", UUID(as_uuid=True), sa.ForeignKey("elections.id"), nullable=False, index=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("platform", sa.String(5000)),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("election_id", "agent_id", name="uq_candidate_election_agent"),
    )

    # Ballots
    op.create_table(
        "ballots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("election_id", UUID(as_uuid=True), sa.ForeignKey("elections.id"), nullable=False, index=True),
        sa.Column("voter_agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("rankings", JSONB, nullable=False),
        sa.Column("cast_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("election_id", "voter_agent_id", name="uq_ballot_election_voter"),
    )

    # Constitution Articles
    op.create_table(
        "constitution_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("article_number", sa.Integer, unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("amended_at", sa.DateTime(timezone=True)),
        sa.Column("amended_by", UUID(as_uuid=True), sa.ForeignKey("agents.id")),
    )

    # Laws
    op.create_table(
        "laws",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("proposed_by", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="proposed", index=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("debate_ends_at", sa.DateTime(timezone=True)),
        sa.Column("votes_for", sa.Integer, server_default="0"),
        sa.Column("votes_against", sa.Integer, server_default="0"),
        sa.Column("presidential_action", sa.String(50)),
        sa.Column("enacted_at", sa.DateTime(timezone=True)),
    )

    # Law Votes
    op.create_table(
        "law_votes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("law_id", UUID(as_uuid=True), sa.ForeignKey("laws.id"), nullable=False, index=True),
        sa.Column("senator_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("vote", sa.String(20), nullable=False),
        sa.Column("cast_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("law_id", "senator_id", name="uq_law_vote_senator"),
    )

    # Code Proposals
    op.create_table(
        "code_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("branch_name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("files_changed", JSONB, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open", index=True),
        sa.Column("requires_governance", sa.Boolean, server_default="false"),
        sa.Column("governance_approved", sa.Boolean),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("merged_at", sa.DateTime(timezone=True)),
    )

    # Code Reviews
    op.create_table(
        "code_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("proposal_id", UUID(as_uuid=True), sa.ForeignKey("code_proposals.id"), nullable=False, index=True),
        sa.Column("reviewer_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("verdict", sa.String(50), nullable=False),
        sa.Column("comments", sa.Text),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("from_agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("to_agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), index=True),
        sa.Column("channel", sa.String(100), index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False, server_default="chat"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), index=True),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("agents.id"), index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open", index=True),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # City Events
    op.create_table(
        "city_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("data", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
    )


def downgrade() -> None:
    op.drop_table("city_events")
    op.drop_table("tasks")
    op.drop_table("messages")
    op.drop_table("code_reviews")
    op.drop_table("code_proposals")
    op.drop_table("law_votes")
    op.drop_table("laws")
    op.drop_table("constitution_articles")
    op.drop_table("ballots")
    op.drop_table("candidates")
    op.drop_table("elections")
    op.drop_table("role_assignments")
    op.drop_table("roles")
    op.drop_table("agents")
