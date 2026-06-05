from django.core.management.base import BaseCommand, CommandError

from django_feature_flags import settings as package_settings
from django_feature_flags.models import Environment, Project, SDKKey


class Command(BaseCommand):
    help = "Manage django-featureflags projects, environments, SDK keys, and maintenance tasks."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")
        bootstrap = subparsers.add_parser("bootstrap")
        bootstrap.add_argument("--project", default="default")
        bootstrap.add_argument("--name", default="Default")

    def handle(self, *args, **options):
        action = options.get("action")
        if action == "bootstrap":
            return self.handle_bootstrap(options)

        raise CommandError("Action is required. Use: bootstrap")

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
