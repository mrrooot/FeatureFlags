"""Cached, DB-free evaluation config snapshots.

Flag evaluation only needs configuration data (flags, variations, flag state,
targeting documents, targeting rules, running experiments and segment
definitions). None of that changes between writes, yet the un-cached evaluator
re-reads it from the database on every single ``evaluate()`` call.

This module builds an immutable, picklable snapshot of everything needed to
evaluate *any* flag in a ``(project, environment)`` pair and caches it in
Django's cache framework. On a cache hit, evaluation touches the database zero
times (aside from the optional tracking write when ``track=True``).

Invalidation uses a single monotonic "generation" counter stored in the cache.
Any write to a config model bumps the generation (see ``apps.py`` signals),
which makes every previously cached snapshot unreachable at once. A TTL on each
snapshot bounds staleness even if a bump is ever missed (e.g. bulk updates that
don't emit signals, or a per-process cache that another worker can't reach).
"""

from dataclasses import dataclass, field

from django.core.cache import caches
from django.db.models import Prefetch

from django_feature_flags import settings as package_settings
from django_feature_flags.models import (
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    FlagState,
    Project,
)
from django_feature_flags.targeting.documents import normalized_targeting

FORMAT_VERSION = 1
GENERATION_KEY = "dff:cfg:gen"


@dataclass(frozen=True)
class VariationData:
    key: str
    value: object
    id: int
    is_default: bool


@dataclass(frozen=True)
class ExperimentData:
    key: str
    flag_key: str
    allocations: tuple  # tuple[(weight: int, variation_key: str)]


@dataclass(frozen=True)
class FlagConfig:
    id: int
    key: str
    value_type: str
    variations: dict  # variation_key -> VariationData
    flag_default_variation_key: str  # the is_default variation (used to seed targeting docs)
    state_exists: bool
    enabled: bool
    state_default_variation_key: str
    rollout: dict
    has_targeting: bool
    emergency_override: dict
    normalized_document: dict
    legacy_rules: tuple  # tuple[{"conditions": [...], "variation_key": str}]
    experiment: object  # ExperimentData | None


@dataclass(frozen=True)
class EnvironmentConfig:
    project_key: str
    project_exists: bool
    environment_exists: bool
    environment_id: object  # int | None
    environment_key: str
    flags: dict  # flag_key -> FlagConfig
    flag_keys: frozenset
    segments: dict  # segment_key -> list[{"conditions": [...], "exclude": bool}]

    def flag(self, flag_key):
        return self.flags.get(flag_key)


def _absent(project_key, environment_key, project_exists):
    return EnvironmentConfig(
        project_key=project_key,
        project_exists=project_exists,
        environment_exists=False,
        environment_id=None,
        environment_key=environment_key,
        flags={},
        flag_keys=frozenset(),
        segments={},
    )


def build_environment_config(project_key, environment_key):
    """Build a snapshot from the database (the cache-miss path)."""
    project = Project.objects.filter(key=project_key).first()
    if project is None:
        return _absent(project_key, environment_key, project_exists=False)

    environment = Environment.objects.filter(project=project, key=environment_key).first()
    if environment is None:
        return _absent(project_key, environment_key, project_exists=True)

    segments = {}
    for segment in project.segments.prefetch_related("rules").all():
        segments[segment.key] = [
            {"conditions": rule.conditions, "exclude": rule.exclude} for rule in segment.rules.all()
        ]

    states_by_flag = {
        state.flag_id: state
        for state in FlagState.objects.filter(environment=environment).select_related("default_variation")
    }

    running_experiments = Experiment.objects.filter(status=Experiment.RUNNING).prefetch_related(
        Prefetch("allocations", queryset=ExperimentAllocation.objects.select_related("variation").order_by("id"))
    )
    flag_queryset = (
        FeatureFlag.objects.filter(project=project, archived=False)
        .prefetch_related(
            "variations",
            "targeting_rules__variation",
            Prefetch("experiments", queryset=running_experiments),
        )
    )

    flags = {}
    for flag in flag_queryset:
        flag.project = project  # avoid re-fetching the (already-known) project downstream

        variations = {}
        flag_default_variation_key = ""
        for variation in flag.variations.all():
            variations[variation.key] = VariationData(
                key=variation.key,
                value=variation.value,
                id=variation.id,
                is_default=variation.is_default,
            )
            if variation.is_default and not flag_default_variation_key:
                flag_default_variation_key = variation.key

        state = states_by_flag.get(flag.id)
        if state is None or state.default_variation is None:
            flags[flag.key] = FlagConfig(
                id=flag.id,
                key=flag.key,
                value_type=flag.value_type,
                variations=variations,
                flag_default_variation_key=flag_default_variation_key,
                state_exists=False,
                enabled=False,
                state_default_variation_key="",
                rollout={},
                has_targeting=False,
                emergency_override={},
                normalized_document={},
                legacy_rules=(),
                experiment=None,
            )
            continue

        state.environment = environment  # normalized_targeting reads state.environment.key for the rollout salt
        normalized_document = normalized_targeting(state)

        legacy_rules = tuple(
            {"conditions": rule.conditions, "variation_key": rule.variation.key}
            for rule in sorted(flag.targeting_rules.all(), key=lambda rule: (rule.priority, rule.id))
        )

        experiment = None
        active = sorted(flag.experiments.all(), key=lambda item: item.id)
        if active:
            chosen = active[0]
            experiment = ExperimentData(
                key=chosen.key,
                flag_key=flag.key,
                allocations=tuple(
                    (allocation.weight, allocation.variation.key) for allocation in chosen.allocations.all()
                ),
            )

        flags[flag.key] = FlagConfig(
            id=flag.id,
            key=flag.key,
            value_type=flag.value_type,
            variations=variations,
            flag_default_variation_key=flag_default_variation_key,
            state_exists=True,
            enabled=state.enabled,
            state_default_variation_key=state.default_variation.key,
            rollout=state.rollout or {},
            has_targeting=bool(state.targeting),
            emergency_override=state.emergency_override or {},
            normalized_document=normalized_document,
            legacy_rules=legacy_rules,
            experiment=experiment,
        )

    return EnvironmentConfig(
        project_key=project_key,
        project_exists=True,
        environment_exists=True,
        environment_id=environment.id,
        environment_key=environment.key,
        flags=flags,
        flag_keys=frozenset(flags),
        segments=segments,
    )


def _cache():
    return caches[package_settings.cache_alias()]


def _generation(cache):
    generation = cache.get(GENERATION_KEY)
    if generation is None:
        # `add` is atomic and only sets when absent, so concurrent evaluators
        # can't clobber a bump that lands in between. Persist it (timeout=None)
        # so the counter outlives the shorter-lived snapshots it stamps.
        cache.add(GENERATION_KEY, 1, timeout=None)
        generation = cache.get(GENERATION_KEY) or 1
    return generation


def _config_key(project_key, environment_key, generation):
    return f"dff:cfg:{FORMAT_VERSION}:{generation}:{project_key}:{environment_key}"


def bump_generation():
    """Invalidate every cached snapshot by advancing the generation counter."""
    if not package_settings.cache_enabled():
        return
    cache = _cache()
    try:
        cache.incr(GENERATION_KEY)
    except ValueError:
        # Counter absent (never set or evicted); establish a fresh one.
        cache.add(GENERATION_KEY, 1, timeout=None)


def get_environment_config(project_key, environment_key, use_cache=True):
    """Return the snapshot for a ``(project, environment)`` pair.

    Builds fresh (no caching) when caching is disabled or ``use_cache`` is
    False — the latter is used by the dashboard preview, which evaluates
    against unsaved targeting overrides that must reflect live data.
    """
    if not use_cache or not package_settings.cache_enabled():
        return build_environment_config(project_key, environment_key)

    cache = _cache()
    generation = _generation(cache)
    key = _config_key(project_key, environment_key, generation)
    config = cache.get(key)
    if config is None:
        config = build_environment_config(project_key, environment_key)
        cache.set(key, config, timeout=package_settings.cache_ttl())
    return config
