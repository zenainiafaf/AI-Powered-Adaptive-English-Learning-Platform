import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from users.models import Learner
from .engine import get_recommendations
from .models import VocabularyItem, GrammarRule, ReadingContent, TaskContent, RecommendationLog


@csrf_exempt
def get_recommendations_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET uniquement'}, status=405)

    learner_id = request.GET.get('learner_id')
    if not learner_id:
        return JsonResponse({'error': 'learner_id requis'}, status=400)

    try:
        learner = Learner.objects.get(pk=learner_id)
    except Learner.DoesNotExist:
        return JsonResponse({'error': 'Apprenant introuvable'}, status=404)


    from django.utils import timezone
    from datetime import timedelta
    # ── Ce que l'étudiant a déjà vu ──────────────────────────
    cutoff_7  = timezone.now() - timedelta(days=7)
    cutoff_1  = timezone.now() - timedelta(days=1)

    already_seen = {}
    for ct in ['vocabulary', 'grammar', 'reading']:
        already_seen[ct] = set(
            RecommendationLog.objects.filter(
                learner=learner, content_type=ct,
                recommended_at__gte=cutoff_7
            ).values_list('content_id', flat=True)
        )
    # Task : seulement 24 items A1, reset chaque jour
    already_seen['task'] = set(
        RecommendationLog.objects.filter(
            learner=learner, content_type='task',
            recommended_at__gte=cutoff_1
        ).values_list('content_id', flat=True)
    )
    # ── Appel GNN avec top_k large ────────────────────────────
    raw = get_recommendations(learner, top_k=50)

    # ── Exclure le déjà vu et garder top 10 ──────────────────
    DISPLAY_LIMIT = {
        'vocabulary': 10,
        'grammar':    10,
        'reading':    10,
        'task':       10,
    }

    def filter_seen(items, ct):
        seen   = already_seen.get(ct, set())
        limit  = DISPLAY_LIMIT.get(ct, 10)
        return [r for r in items if r['model_idx'] not in seen][:limit]

    raw['vocabulary'] = filter_seen(raw.get('vocabulary', []), 'vocabulary')
    raw['grammar']    = filter_seen(raw.get('grammar',    []), 'grammar')
    raw['reading']    = filter_seen(raw.get('reading',    []), 'reading')
    raw['task']       = filter_seen(raw.get('task',       []), 'task')

    # ── Enrichir avec le contenu ──────────────────────────────
    response = {
        'learner_id': learner.learner_id,
        'cefr_level': learner.cefr_level,
        'recommendations': {}
    }

    # Vocabulary
    # Vocabulary — 2 sections : même niveau + autres
    vocab_idxs  = [r['model_idx'] for r in raw.get('vocabulary', [])]
    vocab_items = {v.model_idx: v for v in VocabularyItem.objects.filter(model_idx__in=vocab_idxs)}

    personalized = []
    others       = []

    for r in raw.get('vocabulary', []):
        if r['model_idx'] not in vocab_items:
            continue
        v = vocab_items[r['model_idx']]
        item = {
            'model_idx': r['model_idx'],
            'score':     r['score'],
            'headword':  v.headword,
            'cefr':      v.cefr,
            'pos':       v.pos,
            'definition': v.definition,   
            'synonym':    v.synonym,      
            'example':    v.example, 
        }
        if v.cefr == learner.cefr_level:
            personalized.append(item)
        else:
            others.append(item)

    response['recommendations']['vocabulary'] = {
        'personalized': personalized,
        'others':       others,
    }

    # Grammar
    gram_idxs  = [r['model_idx'] for r in raw.get('grammar', [])]
    gram_items = {g.model_idx: g for g in GrammarRule.objects.filter(model_idx__in=gram_idxs)}
    response['recommendations']['grammar'] = [
        {
            'model_idx': r['model_idx'], 'score': r['score'],
            'super_category': gram_items[r['model_idx']].super_category if r['model_idx'] in gram_items else None,
            'guideword':      gram_items[r['model_idx']].guideword       if r['model_idx'] in gram_items else None,
            'cefr':           gram_items[r['model_idx']].cefr            if r['model_idx'] in gram_items else None,
            'example':        gram_items[r['model_idx']].example         if r['model_idx'] in gram_items else None,
            'can_do':         gram_items[r['model_idx']].can_do          if r['model_idx'] in gram_items else None,
        }
        for r in raw.get('grammar', [])
    ]

    # Reading
    read_idxs  = [r['model_idx'] for r in raw.get('reading', [])]
    read_items = {rd.model_idx: rd for rd in ReadingContent.objects.filter(model_idx__in=read_idxs)}
    response['recommendations']['reading'] = [
        {
            'model_idx': r['model_idx'], 'score': r['score'],
            'title':      read_items[r['model_idx']].title      if r['model_idx'] in read_items else None,
            'cefr':       read_items[r['model_idx']].cefr       if r['model_idx'] in read_items else None,
            'word_count': read_items[r['model_idx']].word_count if r['model_idx'] in read_items else None,
        }
        for r in raw.get('reading', [])
    ]

    # Tasks
    task_idxs  = [r['model_idx'] for r in raw.get('task', [])]
    task_items = {t.model_idx: t for t in TaskContent.objects.filter(model_idx__in=task_idxs)}
    response['recommendations']['tasks'] = [
        {
            'model_idx': r['model_idx'], 'score': r['score'],
            'title':        task_items[r['model_idx']].title        if r['model_idx'] in task_items else None,
            'topic':        task_items[r['model_idx']].topic        if r['model_idx'] in task_items else None,
            'cefr':         task_items[r['model_idx']].cefr         if r['model_idx'] in task_items else None,
            'written_task': task_items[r['model_idx']].written_task if r['model_idx'] in task_items else None,
        }
        for r in raw.get('task', [])
    ]
    return JsonResponse(response)


@csrf_exempt
def mark_clicked_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST uniquement'}, status=405)
    try:
        body       = json.loads(request.body)
        learner_id = body.get('learner_id')
        ct         = body.get('content_type')
        cid        = body.get('content_id')

        learner = Learner.objects.get(pk=learner_id)

        # Créer ou mettre à jour
        obj, created = RecommendationLog.objects.get_or_create(
            learner=learner,
            content_type=ct,
            content_id=cid,
            defaults={'score': 0.0, 'was_clicked': True}
        )
        if not created:
            obj.was_clicked = True
            obj.save()

        return JsonResponse({'success': True, 'created': created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def get_reading_detail_api(request, model_idx):
    try:
        item = ReadingContent.objects.get(model_idx=model_idx)
        return JsonResponse({
            'title': item.title, 'cefr': item.cefr,
            'text': item.text, 'word_count': item.word_count,
        })
    except ReadingContent.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)