from django.contrib import admin

from .models import Character, Comic, Tag


@admin.register(Comic)
class ComicAdmin(admin.ModelAdmin):
    list_display = ('title', 'panel_count')
    list_filter = ('characters', 'tags')
    search_fields = ('title', 'creator_credit')
    autocomplete_fields = ('characters', 'tags')


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
