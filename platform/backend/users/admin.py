from django.contrib import admin

from .models import Learner,SubUnit, Unit
admin.site.register(Learner)

# ─── Unit (optionnel, pour voir  les unités) ─
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'level', 'order']
    list_filter = ['level']
    search_fields = ['title']


# ─── SubUnit ─────────────────────────────────────
@admin.register(SubUnit)
class SubUnitAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'unit', 'order']
    list_filter = ['unit__level', 'unit']
    search_fields = ['title', 'unit__title']
    ordering = ['unit__level', 'unit__order', 'order']
    
from .models import AdaptiveInteractionLog

@admin.register(AdaptiveInteractionLog)
class AdaptiveInteractionLogAdmin(admin.ModelAdmin):
    list_display    = ['session_id', 'cefr_level', 'difficulty',
                       'question_number', 'attempt_number',
                       'agent1_label','feedback_action','judge_label', 'has_language_errors']
    list_filter     = ['cefr_level', 'difficulty', 'agent1_label','feedback_action','judge_label']
    readonly_fields = ['question_text', 'expected_answer', 'student_answer',
                       'agent1_reasoning', 'agent1_missing', 'language_errors',
                       'feedback_text', 'judge_label']
    search_fields   = ['session_id']

    @admin.display(boolean=True, description='Lang. Errors?')
    def has_language_errors(self, obj):
        return bool(obj.language_errors and obj.language_errors.get("has_errors"))