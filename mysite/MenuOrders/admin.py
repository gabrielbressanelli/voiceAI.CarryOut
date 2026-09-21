from django.contrib import admin
from .models import Menu, Cart, ModifierGroup, ModifierOption, ModifierOptionAlias, MenuModifierGroup, MenuAlias, DietaryTag


class MenuAliasInline(admin.TabularInline):
    model = MenuAlias
    extra = 1


class MenuAdmin(admin.ModelAdmin):
    list_display = ('item', 'price',)
    ordering = ('item',)
    inlines = [MenuAliasInline]
    filter_horizontal = ["dietary_tags"]



admin.site.register(Menu, MenuAdmin)
admin.site.register(Cart)
admin.site.register(ModifierGroup)
class ModifierOptionAliasInline(admin.TabularInline):
    model = ModifierOptionAlias
    extra = 1


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "active")
    list_filter = ("group", "active")
    search_fields = ("name", "aliases__alias")
    inlines = [ModifierOptionAliasInline]


admin.site.register(MenuModifierGroup)
admin.site.register(DietaryTag)

