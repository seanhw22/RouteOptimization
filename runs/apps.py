import sys

from django.apps import AppConfig


# Management commands where the stale-experiment sweep MUST NOT run.
# (Triggering DB writes during these commands breaks them or is just wasteful.)
_SKIP_COMMANDS = {
    'makemigrations', 'migrate', 'collectstatic', 'showmigrations',
    'sqlmigrate', 'check', 'shell', 'dumpdata', 'loaddata', 'test',
    'createsuperuser', 'changepassword',
}


class RunsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'runs'

    def ready(self):
        # sys.argv[1] is the manage.py subcommand if invoked via manage.py.
        # In gunicorn / wsgi, sys.argv differs and won't match these names.
        if len(sys.argv) > 1 and sys.argv[1] in _SKIP_COMMANDS:
            return
        try:
            from .services import mark_stale_experiments
            n = mark_stale_experiments()
            if n:
                print(f'[runs] Marked {n} stale running experiment(s) as interrupted.')
        except Exception as e:
            print(f'[runs] Stale-experiment sweep skipped: {e}')
