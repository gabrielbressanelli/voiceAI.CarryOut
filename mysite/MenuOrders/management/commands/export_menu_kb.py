import json
from django.core.management.base import BaseCommand
from MenuOrders.models import Menu
from MenuOrders.pricing import effective_option_delta


class Command(BaseCommand):
    help = 'Export menu DB as a Bland AI knowledge base file'

    def add_arguments(self, parser):
        parser.add_argument('--format', choices=['txt', 'json'], default='txt')
        parser.add_argument('--output', default='menu_kb.txt')

    def handle(self, *args, **options):
        items = (
            Menu.objects
            .all()
            .prefetch_related('modifier_group__group__options')
            .order_by('food_type', 'item')
        )

        if options['format'] == 'json':
            self._export_json(items, options['output'])
        else:
            self._export_txt(items, options['output'])

        self.stdout.write(self.style.SUCCESS(f"Exported to {options['output']}"))

    def _export_txt(self, items, path):
        lines = []
        for item in items:
            lines.append(f"MENU ITEM: {item.item}")
            lines.append(f"Category: {item.get_food_type_display()}")
            lines.append(f"Price: ${item.price}")
            if item.description:
                lines.append(f"Description: {item.description}")

            mmgs = list(
                item.modifier_group
                .select_related('group')
                .prefetch_related('group__options')
                .order_by('sort_order')
            )
            if mmgs:
                lines.append("Options:")
                for mmg in mmgs:
                    req = mmg.effective_required()
                    opts = []
                    for o in mmg.group.options.filter(active=True).order_by('sort_order'):
                        label = o.name
                        delta = effective_option_delta(item, o)
                        if delta:
                            sign = "+" if delta >= 0 else "-"
                            label += f" ({sign}${abs(delta)})"
                        opts.append(label)
                    req_label = "required" if req else "optional"
                    lines.append(f"  - {mmg.group.name} ({req_label}): {', '.join(opts)}")

            lines.append("")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _export_json(self, items, path):
        out = []
        for item in items:
            mmgs = list(
                item.modifier_group
                .select_related('group')
                .prefetch_related('group__options')
                .order_by('sort_order')
            )
            out.append({
                "id": item.id,
                "item": item.item,
                "category": item.get_food_type_display(),
                "price": str(item.price),
                "description": item.description,
                "modifier_groups": [
                    {
                        "name": mmg.group.name,
                        "required": mmg.effective_required(),
                        "min_choices": mmg.effective_min(),
                        "max_choices": mmg.effective_max(),
                        "options": [
                            {"id": o.id, "name": o.name, "price_delta": str(effective_option_delta(item, o))}
                            for o in mmg.group.options.filter(active=True).order_by('sort_order')
                        ]
                    }
                    for mmg in mmgs
                ]
            })

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)