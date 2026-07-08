from django.db import models

from users.models import Learner


class VocabularyItem(models.Model):
    CEFR_CHOICES = [
        ('A1', 'A1'), ('A2', 'A2'),
        ('B1', 'B1'), ('B2', 'B2'),
        ('C1', 'C1'), ('C2', 'C2'),
    ]
    vocab_id   = models.CharField(max_length=100, unique=True)
    headword   = models.CharField(max_length=200)
    pos        = models.CharField(max_length=50, blank=True)
    cefr       = models.CharField(max_length=2, choices=CEFR_CHOICES)
    label      = models.CharField(max_length=300, blank=True)
    model_idx  = models.IntegerField(unique=True)
    definition = models.TextField(blank=True)
    synonym = models.TextField(blank=True)
    example    = models.TextField(blank=True)  

    class Meta:
        db_table = 'rec_vocabulary'
        ordering = ['cefr', 'headword']

    def __str__(self):
        return f"[{self.cefr}] {self.headword}"


class GrammarRule(models.Model):
    CEFR_CHOICES = [
        ('A1', 'A1'), ('A2', 'A2'),
        ('B1', 'B1'), ('B2', 'B2'),
        ('C1', 'C1'), ('C2', 'C2'),
    ]
    grammar_id      = models.CharField(max_length=100, unique=True)
    super_category  = models.CharField(max_length=200)
    sub_category    = models.CharField(max_length=200, blank=True)
    cefr            = models.CharField(max_length=2, choices=CEFR_CHOICES)
    guideword       = models.CharField(max_length=300, blank=True)
    can_do          = models.TextField(blank=True)
    example         = models.TextField(blank=True)
    model_idx       = models.IntegerField(unique=True)

    class Meta:
        db_table = 'rec_grammar'
        ordering = ['cefr', 'super_category']

    def __str__(self):
        return f"[{self.cefr}] {self.super_category} — {self.guideword[:60]}"


class ReadingContent(models.Model):
    CEFR_CHOICES = [
        ('A1', 'A1'), ('A2', 'A2'),
        ('B1', 'B1'), ('B2', 'B2'),
        ('C1', 'C1'), ('C2', 'C2'),
    ]
    reading_id   = models.CharField(max_length=200, unique=True)
    slug         = models.CharField(max_length=200, blank=True)
    title        = models.CharField(max_length=500)
    cefr         = models.CharField(max_length=2, choices=CEFR_CHOICES)
    grade_level  = models.FloatField(null=True, blank=True)
    version      = models.IntegerField(default=0)
    text         = models.TextField()
    text_length  = models.IntegerField(default=0)
    word_count   = models.IntegerField(default=0)
    model_idx    = models.IntegerField(unique=True)

    class Meta:
        db_table = 'rec_reading'
        ordering = ['cefr', 'title']

    def __str__(self):
        return f"[{self.cefr}] {self.title[:80]}"


class TaskContent(models.Model):
    CEFR_CHOICES = [
        ('A1', 'A1'), ('A2', 'A2'),
        ('B1', 'B1'), ('B2', 'B2'),
        ('C1', 'C1'), ('C2', 'C2'),
    ]
    level_number  = models.IntegerField()
    level         = models.CharField(max_length=50)
    unit          = models.IntegerField()
    title         = models.CharField(max_length=300)
    topic         = models.CharField(max_length=300)
    cefr          = models.CharField(max_length=2, choices=CEFR_CHOICES)
    written_task  = models.TextField()
    model_idx     = models.IntegerField(unique=True)

    class Meta:
        db_table = 'rec_task'
        ordering = ['cefr', 'level_number', 'unit']

    def __str__(self):
        return f"[{self.cefr}] {self.title}"


class RecommendationLog(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('vocabulary', 'Vocabulary'),
        ('grammar',    'Grammar'),
        ('reading',    'Reading'),
        ('task',       'Task'),
    ]
    learner        = models.ForeignKey(
        Learner,
        on_delete=models.CASCADE,
        related_name='recommendation_logs'
    )
    content_type   = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id     = models.IntegerField()
    score          = models.FloatField()
    recommended_at = models.DateTimeField(auto_now_add=True)
    was_clicked    = models.BooleanField(default=False)

    class Meta:
        db_table = 'rec_log'
        ordering = ['-recommended_at']
        indexes  = [models.Index(fields=['learner', 'content_type'])]

    def __str__(self):
        return f"{self.learner.name} | {self.content_type} #{self.content_id} | {self.score:.3f}"
