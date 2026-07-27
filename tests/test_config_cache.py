import pytest
from django.core.cache import cache

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import (
    Environment,
    Event,
    FeatureFlag,
    FlagState,
    Project,
    Segment,
    SegmentRule,
    Variation,
)


@pytest.fixture(autouse=True)
def clear_config_cache():
    # Reset the generation counter and any snapshots so query counts are
    # deterministic regardless of test ordering (LocMem isn't rolled back).
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def flag_stack():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=off)
    return project, environment, flag, off, on


def _evaluate(flag_key="new_checkout", context=None, default=None, **kwargs):
    return evaluate(
        flag_key,
        context or {"key": "user-1"},
        default=default,
        project_key="ecommerce",
        environment_key="production",
        **kwargs,
    )


@pytest.mark.django_db
def test_cache_hit_issues_no_queries(flag_stack, django_assert_num_queries):
    _evaluate()  # cold: builds and caches the snapshot

    with django_assert_num_queries(0):
        result = _evaluate()

    assert result.reason == "fallthrough"
    assert result.variation_key == "off"


@pytest.mark.django_db
def test_other_flags_in_same_environment_are_free_after_warmup(flag_stack, django_assert_num_queries):
    project, environment, _, _, _ = flag_stack
    second = FeatureFlag.objects.create(project=project, key="dark_mode", name="Dark Mode", value_type="boolean")
    off = Variation.objects.create(flag=second, key="off", value=False, is_default=True)
    Variation.objects.create(flag=second, key="on", value=True)
    FlagState.objects.create(flag=second, environment=environment, enabled=False, default_variation=off)

    _evaluate("new_checkout")  # one build covers every flag in the environment

    with django_assert_num_queries(0):
        result = _evaluate("dark_mode")

    assert result.reason == "off"


@pytest.mark.django_db
def test_saving_state_invalidates_cache(flag_stack):
    _evaluate()  # cache with enabled=True -> fallthrough "off" variation

    state = FlagState.objects.get(flag__key="new_checkout")
    state.enabled = False
    state.targeting = {"off_variation": "on", "fallthrough": {"variation_key": "off"}}
    state.save(update_fields=["enabled", "targeting"])

    result = _evaluate()
    assert result.reason == "off"
    assert result.variation_key == "on"  # reflects the just-saved off_variation


@pytest.mark.django_db
def test_archiving_flag_invalidates_cache(flag_stack):
    assert _evaluate().reason == "fallthrough"

    flag = FeatureFlag.objects.get(key="new_checkout")
    flag.archived = True
    flag.save(update_fields=["archived"])

    result = _evaluate(default="gone")
    assert result.reason == "flag_not_found"
    assert result.value == "gone"


@pytest.mark.django_db
def test_tracking_writes_event_on_cache_hit_with_single_query(flag_stack, django_assert_num_queries):
    _evaluate()  # warm the cache

    before = Event.objects.count()
    with django_assert_num_queries(1):  # only the event INSERT; config comes from cache
        _evaluate(track=True)

    assert Event.objects.count() == before + 1


@pytest.mark.django_db
def test_segment_match_is_evaluated_from_cache_without_queries(flag_stack, django_assert_num_queries):
    project, environment, flag, off, on = flag_stack
    segment = Segment.objects.create(project=project, key="beta_users", name="Beta Users")
    SegmentRule.objects.create(segment=segment, conditions=[{"attribute": "plan", "operator": "equals", "value": "pro"}])
    state = FlagState.objects.get(flag=flag)
    state.targeting = {
        "off_variation": off.key,
        "rules": [
            {
                "id": "segment-rule",
                "clauses": [
                    {
                        "context_kind": "user",
                        "attribute": "segment",
                        "operator": "segment_match",
                        "values": ["beta_users"],
                    }
                ],
                "serve": {"variation_key": on.key},
            }
        ],
        "fallthrough": {"variation_key": off.key},
    }
    state.save(update_fields=["targeting"])

    context = {"key": "user-1", "plan": "pro"}
    _evaluate(context=context)  # warm

    with django_assert_num_queries(0):
        result = _evaluate(context=context)

    assert result.reason == "rule_match"
    assert result.variation_key == "on"


@pytest.mark.django_db
def test_cache_disabled_reads_live_data(flag_stack, settings, django_assert_num_queries):
    settings.DJANGO_FEATURE_FLAGS_CACHE_ENABLED = False

    assert _evaluate().variation_key == "off"

    # QuerySet.update() intentionally skips signals; with caching off the change
    # is still picked up because every evaluation reads the database.
    FlagState.objects.filter(flag__key="new_checkout").update(
        targeting={"off_variation": "on", "fallthrough": {"variation_key": "off"}}, enabled=False
    )

    result = _evaluate()
    assert result.reason == "off"
    assert result.variation_key == "on"


@pytest.mark.django_db
def test_preview_override_bypasses_cache(flag_stack):
    state = FlagState.objects.get(flag__key="new_checkout")
    state.enabled = False
    state.save(update_fields=["enabled"])

    _evaluate()  # cache the disabled snapshot

    override_document = {
        "off_variation": "off",
        "targets": [],
        "rules": [],
        "fallthrough": {"variation_key": "on"},
    }
    result = _evaluate(targeting_override=override_document, enabled_override=True)

    assert result.reason == "fallthrough"
    assert result.variation_key == "on"  # override wins over the cached disabled state
