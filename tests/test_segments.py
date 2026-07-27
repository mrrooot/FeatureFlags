"""Segment matching behaviors.

Each behavior is checked twice: against an in-memory segment map (the path the
cached evaluator uses) and against the live ORM (project.segments), asserting
the two agree.
"""
import pytest

from django_feature_flags.models import Project, Segment, SegmentRule
from django_feature_flags.targeting.operators import segment_clause_matches

# In-memory segment map mirrored by the ORM rows created in the fixture.
SEGMENTS_MAP = {
    "beta": [{"conditions": [{"attribute": "plan", "operator": "equals", "value": "pro"}], "exclude": False}],
    "excl": [
        {"conditions": [{"attribute": "plan", "operator": "equals", "value": "pro"}], "exclude": False},
        {"conditions": [{"attribute": "banned", "operator": "equals", "value": True}], "exclude": True},
    ],
    "empty": [],  # no rules -> everyone matches
}


@pytest.fixture
def project_with_segments():
    project = Project.objects.create(key="p", name="P")
    beta = Segment.objects.create(project=project, key="beta", name="Beta")
    SegmentRule.objects.create(segment=beta, conditions=[{"attribute": "plan", "operator": "equals", "value": "pro"}])
    excl = Segment.objects.create(project=project, key="excl", name="Excl")
    SegmentRule.objects.create(segment=excl, conditions=[{"attribute": "plan", "operator": "equals", "value": "pro"}])
    SegmentRule.objects.create(segment=excl, conditions=[{"attribute": "banned", "operator": "equals", "value": True}], exclude=True)
    Segment.objects.create(project=project, key="empty", name="Empty")  # no rules
    return project


def clause(keys, negate=False):
    return {"context_kind": "user", "attribute": "segment", "operator": "segment_match", "values": keys, "negate": negate}


CASES = [
    ("include_hit", {"plan": "pro"}, clause(["beta"]), True),
    ("include_miss", {"plan": "free"}, clause(["beta"]), False),
    ("exclude_removes_member", {"plan": "pro", "banned": True}, clause(["excl"]), False),
    ("exclude_keeps_member", {"plan": "pro", "banned": False}, clause(["excl"]), True),
    ("multi_segment_any", {"plan": "free"}, clause(["beta", "excl"]), False),
    ("multi_segment_one_hits", {"plan": "pro"}, clause(["beta", "ghost"]), True),
    ("negate_inverts", {"plan": "free"}, clause(["beta"], negate=True), True),
    ("segment_not_found", {"plan": "pro"}, clause(["ghost"]), False),
    ("empty_segment_matches_all", {"plan": "whatever"}, clause(["empty"]), True),
]


@pytest.mark.django_db
@pytest.mark.parametrize("label,attrs,segment_clause,want", CASES, ids=[c[0] for c in CASES])
def test_segment_clause_matches(project_with_segments, label, attrs, segment_clause, want):
    context = {"user": {"key": "u", **attrs}}

    map_result = segment_clause_matches(context, segment_clause, segments=SEGMENTS_MAP)
    orm_result = segment_clause_matches(context, segment_clause, project=project_with_segments)

    assert map_result is want, f"{label}: map path returned {map_result}"
    assert orm_result is want, f"{label}: orm path returned {orm_result}"
