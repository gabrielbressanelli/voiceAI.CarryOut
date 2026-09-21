import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings

from MenuOrders.models import Menu, MenuAlias, MenuModifierGroup, ModifierGroup, ModifierOption, ModifierOptionAlias
from MenuOrders.modifier_matching import match_modifier_option
from cart.views import _resolve_modifier_option

from .matching import _find_option_in_query, search_menu
from .order_summary import compute_total_from_summary
from .views import menu_item_detail, menu_search


@override_settings(VOICE_ORDER_API_TOKEN="test-token")
class ModifierAliasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.menu = Menu.objects.create(item="Build Your Own Pasta", price="15.00", food_type="pasta")
        cls.shape = ModifierGroup.objects.create(name="Pasta BYO", required=True, min_choices=1)
        cls.sauce = ModifierGroup.objects.create(name="Sauce BYO", required=True, min_choices=1)
        for group in (cls.shape, cls.sauce):
            MenuModifierGroup.objects.create(menu=cls.menu, group=group)
        cls.penne = ModifierOption.objects.create(group=cls.shape, name="Penne")
        cls.palomino = ModifierOption.objects.create(group=cls.sauce, name="Palomino", price_delta="2.00")
        cls.marinara = ModifierOption.objects.create(group=cls.sauce, name="Marinara")
        ModifierOptionAlias.objects.create(option=cls.palomino, alias="pink sauce")
        ModifierOptionAlias.objects.create(option=cls.marinara, alias="red sauce")
        cls.hidden = ModifierOption.objects.create(group=cls.sauce, name="Pesto", active=False)
        ModifierOptionAlias.objects.create(option=cls.hidden, alias="green sauce")

    def search(self, query):
        request = RequestFactory().get("/api/agent/menu/search", {"q": query}, HTTP_AUTHORIZATION="Bearer test-token")
        response = menu_search(request)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)

    def assert_no_scripted_questions(self, payload):
        if isinstance(payload, dict):
            self.assertFalse({"question", "clarification_question", "note"} & payload.keys())
            for value in payload.values():
                self.assert_no_scripted_questions(value)
        elif isinstance(payload, list):
            for value in payload:
                self.assert_no_scripted_questions(value)

    def test_sauce_alias_preselects_canonical_option(self):
        payload = self.search("penne with PINK SAUCE")
        self.assertEqual(payload["match_status"], "matched")
        self.assertEqual(payload["resolution"], "build_your_own")
        selected = {p["option_id"]: p["option_name"] for p in payload["preselected_modifiers"]}
        self.assertEqual(selected, {self.penne.id: "Penne", self.palomino.id: "Palomino"})
        self.assertEqual(payload["item"]["required_modifiers"], [])
        self.assert_no_scripted_questions(payload)

    def test_shape_alias_resolves_build_your_own(self):
        ModifierOptionAlias.objects.create(option=self.penne, alias="penny")
        payload = self.search("penny red sauce")
        self.assertEqual(payload["resolution"], "build_your_own")
        self.assertEqual({p["option_id"] for p in payload["preselected_modifiers"]}, {self.penne.id, self.marinara.id})

    def test_detail_keeps_group_rules_prices_and_aliases(self):
        request = RequestFactory().get("/", HTTP_AUTHORIZATION="Bearer test-token")
        payload = json.loads(menu_item_detail(request, self.menu.id).content)
        sauce = next(g for g in payload["item"]["required_modifiers"] if g["id"] == self.sauce.id)
        self.assertEqual((sauce["name"], sauce["min_choices"], sauce["max_choices"]), ("Sauce BYO", 1, 1))
        self.assertEqual(sauce["options"][0], {
            "id": self.palomino.id, "name": "Palomino", "price_adjustment": "2.00", "aliases": ["pink sauce"],
        })
        self.assertNotIn(self.hidden.id, [o["id"] for o in sauce["options"]])
        shape = next(g for g in payload["item"]["required_modifiers"] if g["id"] == self.shape.id)
        self.assertNotIn("aliases", shape["options"][0])
        self.assert_no_scripted_questions(payload)

    def test_shape_only_keeps_standalone_and_custom_candidates(self):
        dishes = [Menu.objects.create(item=name, price="20.00", food_type="pasta") for name in ("Penne Primavera", "Penne Puttanesca")]
        payload = self.search("penne")
        self.assertEqual(payload["match_status"], "ambiguous")
        self.assertEqual({m["item_id"] for m in payload["matches"]}, {self.menu.id, *(dish.id for dish in dishes)})
        byo = next(m for m in payload["matches"] if m["item_id"] == self.menu.id)
        self.assertEqual([g["name"] for g in byo["required_modifiers"]], ["Sauce BYO"])
        self.assertEqual(byo["preselected_modifiers"][0]["option_id"], self.penne.id)
        self.assert_no_scripted_questions(payload)

    def test_ordinary_ambiguity_and_batch_responses_have_no_questions(self):
        for name in ("Chicken Parm", "Eggplant Parm"):
            dish = Menu.objects.create(item=name, price="20.00", food_type="parms")
            MenuAlias.objects.create(menu=dish, alias="parm")
        payload = self.search("parm, penne pink sauce")
        self.assertEqual([r["match_status"] for r in payload["results"]], ["ambiguous", "matched"])
        self.assert_no_scripted_questions(payload)

    def test_exact_menu_dish_still_wins(self):
        dish = Menu.objects.create(item="Penne Palomino", price="22.00", food_type="pasta")
        self.assertEqual(search_menu(dish.item)["item"], dish)

    def test_alias_reprices_summary(self):
        total, warnings = compute_total_from_summary("2x Build Your Own Pasta; Penne; pink sauce")
        self.assertEqual(total, Decimal("34.00"))
        self.assertEqual(warnings, [])

    def test_cart_import_alias_is_scoped_to_item_and_active_options(self):
        self.assertEqual(_resolve_modifier_option(self.menu, "PINK SAUCE"), self.palomino)
        self.assertIsNone(_resolve_modifier_option(self.menu, "green sauce"))
        other = Menu.objects.create(item="Salad", price="10.00", food_type="salad")
        self.assertIsNone(_resolve_modifier_option(other, "pink sauce"))

    def test_alias_collisions_stay_unresolved_and_canonical_name_wins(self):
        ModifierOptionAlias.objects.create(option=self.marinara, alias="pink sauce")
        options = self.sauce.options.prefetch_related("aliases")
        self.assertIsNone(match_modifier_option(options, "pink sauce"))
        self.assertIsNone(_find_option_in_query("penne pink sauce", options))
        ModifierOptionAlias.objects.create(option=self.palomino, alias="Marinara")
        self.assertEqual(match_modifier_option(self.sauce.options.all(), "Marinara"), self.marinara)

    def test_phrase_boundaries_and_longest_alias(self):
        ModifierOptionAlias.objects.create(option=self.palomino, alias="red")
        options = self.sauce.options.prefetch_related("aliases")
        self.assertEqual(_find_option_in_query("penne red sauce", options), self.marinara)
        self.assertIsNone(_find_option_in_query("penne shredded cheese", options))
        self.assertIsNone(_find_option_in_query("penne green sauce", options))

    def test_existing_fuzzy_names_and_alias_typos(self):
        self.assertEqual(_find_option_in_query("penne palomno", self.sauce.options.all()), self.palomino)
        ModifierOptionAlias.objects.create(option=self.palomino, alias="rosata")
        self.assertEqual(_find_option_in_query("penne rosatta", self.sauce.options.all()), self.palomino)

    def test_knowledge_base_exports_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            for format in ("json", "txt"):
                path = Path(directory) / f"kb.{format}"
                call_command("export_menu_kb", format=format, output=str(path), verbosity=0)
                content = path.read_text()
                self.assertIn("pink sauce", content)
                self.assertNotIn("green sauce", content)
                if format == "json":
                    option = json.loads(content)[0]["modifier_groups"][1]["options"][0]
                    self.assertEqual(option["aliases"], ["pink sauce"])
