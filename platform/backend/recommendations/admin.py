from django.contrib import admin
from .models import VocabularyItem, GrammarRule, ReadingContent, TaskContent, RecommendationLog

@admin.register(VocabularyItem)
class VocabularyAdmin(admin.ModelAdmin):
    list_display  = ['headword', 'cefr', 'pos', 'vocab_id', 'model_idx']
    list_filter   = ['cefr']
    search_fields = ['headword', 'vocab_id']


@admin.register(GrammarRule)
class GrammarAdmin(admin.ModelAdmin):
    list_display  = ['super_category', 'sub_category', 'cefr', 'guideword', 'model_idx']
    list_filter   = ['cefr', 'super_category']
    search_fields = ['guideword', 'can_do']


@admin.register(ReadingContent)
class ReadingAdmin(admin.ModelAdmin):
    list_display  = ['title', 'cefr', 'grade_level', 'word_count', 'model_idx']
    list_filter   = ['cefr']
    search_fields = ['title', 'slug']


@admin.register(TaskContent)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ['title', 'cefr', 'level', 'unit', 'topic', 'model_idx']
    list_filter   = ['cefr', 'level']
    search_fields = ['title', 'topic']


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display  = ['learner', 'content_type', 'content_id', 'score', 'was_clicked', 'recommended_at']
    list_filter   = ['content_type', 'was_clicked']
    search_fields = ['learner__name']


