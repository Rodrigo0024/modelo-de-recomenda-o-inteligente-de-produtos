
from django.urls import path
from django.views.generic import RedirectView  # Add this import
from . import views


urlpatterns = [
    # Páginas principais
    path('', views.product_explorer, name='product_explorer'),
    path('home/', views.home, name='home'),
    path('index/', views.index, name='index'),
    
    
    # Sistema de navegação
    path('explore/', views.product_explorer, name='product_explorer'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<str:category_name>/', views.category_products, name='category_products'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('rate/<int:product_id>/', views.rate_product, name='rate_product'),
    
 # ✅ ESTAS 3 URLs DEVEM EXISTIR:
    path('api/record-interaction/', views.record_interaction, name='record_interaction'),
    path('api/get-recommendations/', views.get_recommendations_ajax, name='get_recommendations_ajax'),
    path('api/recommendations/', views.get_recommendations, name='get_recommendations'),
    
    # ✅ E ESTA TAMBÉM:
    path('my-recommendations/', views.user_recommendations, name='user_recommendations'),
    
    # Sistema original
    path('train/', views.train_recommender, name='train_recommender'),
    path('model-status/', views.model_status, name='model_status'),
    path('my-recommendations/', views.user_recommendations, name='user_recommendations'),
     # Add the redirect for /recommendations/
    path('recommendations/', RedirectView.as_view(url='/my-recommendations/')),
    path('debug/interactions/', views.debug_interactions, name='debug_interactions'),
    path('debug/test-interaction/<int:product_id>/', views.test_interaction, name='test_interaction'),


    path('api/record-interaction/', views.record_interaction_api, name='record_interaction_api'),
    path('api/get-recommendations/', views.get_recommendations_ajax, name='get_recommendations_ajax'),
    path('api/product/<int:product_id>/stats/', views.product_stats_api, name='product_stats_api'),
]