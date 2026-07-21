import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from MenuOrders.models import Menu, MenuAlias


class Command(BaseCommand):
    help = "Backfill MenuAlias rows from the hand-curated aliases in menu_kb.json"

    def add_arguments(self, parser):
        parser.add_argument('--input', default=os.path.join(settings.BASE_DIR, 'menu_kb.json'))

    def handle(self, *args, **options):
        with open(options['input'], 'r', encoding='utf-8') as f:
            entries = json.load(f)

        created = 0
        skipped_items = 0
        for entry in entries:
            menu_id = entry.get('id')
            aliases = entry.get('aliases') or []
            if not aliases:
                continue

            try:
                menu = Menu.objects.get(id=menu_id)
            except Menu.DoesNotExist:
                skipped_items += 1
                self.stdout.write(self.style.WARNING(f"Skipping unknown menu id {menu_id}"))
                continue

            for alias in aliases:
                alias = alias.strip()
                if not alias:
                    continue
                _, was_created = MenuAlias.objects.get_or_create(menu=menu, alias=alias)
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} alias(es); skipped {skipped_items} unknown item id(s)."
        ))
