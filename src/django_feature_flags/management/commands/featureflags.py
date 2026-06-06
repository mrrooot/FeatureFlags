import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from django_feature_flags import settings as package_settings
from django_feature_flags.models import (
    Environment,
    Event,
    Experiment,
    ExperimentResultSnapshot,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Variation,
)


class Command(BaseCommand):
    help = "Manage django-featureflags projects, environments, SDK keys, and maintenance tasks."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")

        bootstrap = subparsers.add_parser("bootstrap")
        bootstrap.add_argument("--project", default="default")
        bootstrap.add_argument("--name", default="Default")

        export = subparsers.add_parser("export")
        export.add_argument("--project", required=True)

        import_cmd = subparsers.add_parser("import")
        import_cmd.add_argument("path")

        rotate = subparsers.add_parser("rotate-key")
        rotate.add_argument("--project", required=True)
        rotate.add_argument("--environment", required=True)

        cleanup = subparsers.add_parser("cleanup-events")
        cleanup.add_argument("--days", type=int, default=90)

        subparsers.add_parser("snapshot-results")

    def handle(self, *args, **options):
        action = options.get("action")
        if action == "bootstrap":
            return self.handle_bootstrap(options)
        if action == "export":
            return self.handle_export(options)
        if action == "import":
            return self.handle_import(options)
        if action == "rotate-key":
            return self.handle_rotate_key(options)
        if action == "cleanup-events":
            return self.handle_cleanup_events(options)
        if action == "snapshot-results":
            return self.handle_snapshot_results(options)

        raise CommandError("Action is required.")

    def handle_bootstrap(self, options):
        project, _ = Project.objects.get_or_create(
            key=options["project"],
            defaults={"name": options["name"]},
        )
        created_secrets = []

        for environment_key in package_settings.DEFAULT_ENVIRONMENTS:
            environment, _ = Environment.objects.get_or_create(
                project=project,
                key=environment_key,
                defaults={"name": self.environment_name(environment_key)},
            )
            if not SDKKey.objects.filter(environment=environment, name="Server SDK").exists():
                sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")
                created_secrets.append((environment.key, sdk_key.secret))

        self.stdout.write(self.style.SUCCESS(f"Bootstrapped project '{project.key}'"))
        if created_secrets:
            self.stdout.write("New SDK secrets:")
            for environment_key, raw_secret in created_secrets:
                self.stdout.write(f"{environment_key}: {raw_secret}")
        else:
            self.stdout.write("No new SDK secrets created.")

    @staticmethod
    def environment_name(environment_key):
        return environment_key.replace("-", " ").replace("_", " ").title()

    def handle_export(self, options):
        project = Project.objects.get(key=options["project"])
        payload = {
            "project": {"key": project.key, "name": project.name, "description": project.description},
            "environments": list(project.environments.values("key", "name", "requires_approval", "require_change_reason")),
            "flags": [],
        }
        for flag in project.flags.prefetch_related("variations", "states__environment"):
            payload["flags"].append(
                {
                    "key": flag.key,
                    "name": flag.name,
                    "description": flag.description,
                    "value_type": flag.value_type,
                    "archived": flag.archived,
                    "rules": flag.rules,
                    "variations": list(flag.variations.values("key", "name", "value", "is_default")),
                    "states": [
                        {
                            "environment": state.environment.key,
                            "enabled": state.enabled,
                            "default_variation": state.default_variation.key if state.default_variation else "",
                            "rollout": state.rollout,
                            "emergency_override": state.emergency_override,
                        }
                        for state in flag.states.select_related("environment", "default_variation")
                    ],
                }
            )
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))

    def handle_import(self, options):
        with open(options["path"], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        project_data = payload["project"]
        project, _ = Project.objects.update_or_create(
            key=project_data["key"],
            defaults={"name": project_data["name"], "description": project_data.get("description", "")},
        )
        environments = {}
        for item in payload["environments"]:
            environment, _ = Environment.objects.update_or_create(
                project=project,
                key=item["key"],
                defaults={
                    "name": item["name"],
                    "requires_approval": item.get("requires_approval", False),
                    "require_change_reason": item.get("require_change_reason", False),
                },
            )
            environments[environment.key] = environment
        for flag_data in payload["flags"]:
            flag, _ = FeatureFlag.objects.update_or_create(
                project=project,
                key=flag_data["key"],
                defaults={
                    "name": flag_data["name"],
                    "description": flag_data.get("description", ""),
                    "value_type": flag_data["value_type"],
                    "archived": flag_data.get("archived", False),
                    "rules": flag_data.get("rules", []),
                },
            )
            variations = {}
            for item in flag_data["variations"]:
                variation, _ = Variation.objects.update_or_create(
                    flag=flag,
                    key=item["key"],
                    defaults={"name": item.get("name", ""), "value": item["value"], "is_default": item.get("is_default", False)},
                )
                variations[variation.key] = variation
            for item in flag_data["states"]:
                FlagState.objects.update_or_create(
                    flag=flag,
                    environment=environments[item["environment"]],
                    defaults={
                        "enabled": item["enabled"],
                        "default_variation": variations.get(item.get("default_variation")),
                        "rollout": item.get("rollout", {}),
                        "emergency_override": item.get("emergency_override", {}),
                    },
                )
        self.stdout.write(self.style.SUCCESS("Imported feature flag configuration"))

    def handle_rotate_key(self, options):
        environment = Environment.objects.get(project__key=options["project"], key=options["environment"])
        environment.sdk_keys.filter(active=True).update(active=False)
        sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")
        self.stdout.write(sdk_key.secret)

    def handle_cleanup_events(self, options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        deleted, _ = Event.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(str(deleted))

    def handle_snapshot_results(self, options):
        count = 0
        for experiment in Experiment.objects.all():
            ExperimentResultSnapshot.create_for_experiment(experiment)
            count += 1
        self.stdout.write(str(count))
