from django.urls import path
from . import views

urlpatterns = [
    path('api/recommendations/', views.get_recommendations_api, name='recommendations'),
    path('api/recommendations/reading/<int:model_idx>/', views.get_reading_detail_api, name='reading_detail'),
    path('api/recommendations/clicked/',                      views.mark_clicked_api,        name='rec_clicked'),
]