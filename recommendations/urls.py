from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'recommendations' 

urlpatterns = [
    # Páginas principais
    path('', views.product_explorer, name='product_explorer'),
    path('home/', views.home, name='home'),
    path('index/', views.index, name='index'),
    
    # Sistema de navegação
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<str:category_name>/', views.category_products, name='category_products'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('rate/<int:product_id>/', views.rate_product, name='rate_product'),
    
    # APIs de interação
    path('api/record-interaction/', views.record_interaction_api, name='record_interaction_api'),
    path('api/get-recommendations/', views.get_recommendations_ajax, name='get_recommendations_ajax'),
    path('api/recommendations/', views.get_recommendations, name='get_recommendations'),
    path('api/product/<int:product_id>/stats/', views.product_stats_api, name='product_stats_api'),
    
    # Recomendações
    path('my-recommendations/', views.user_recommendations, name='user_recommendations'),
    
    # Sistema original
    path('train/', views.train_recommender, name='train_recommender'),
    path('model-status/', views.model_status, name='model_status'),
    
    # Debug
    path('debug/interactions/', views.debug_interactions, name='debug_interactions'),
    path('debug/test-interaction/<int:product_id>/', views.test_interaction, name='test_interaction'),

    # IA Generativa - URLs EXISTENTES
    path('ai-status/', views.ai_status, name='ai_status'),
    path('generate-description/', views.generate_description_page, name='generate_description_page'),
    path('test-ai/', views.test_ai, name='test_ai'),
    
    # 🔥 URLs QUE ESTÃO FALTANDO - ADICIONE ESTAS:
    
    # APIs de IA Generativa
    path('api/generate-description/', views.generate_description_api, name='generate_description_api'),
    path('api/test-ai-connection/', views.test_ai_connection, name='test_ai_connection'),
    path('api/generate-features/', views.generate_product_features, name='generate_product_features'),
    path('api/ai-product-wizard/', views.ai_product_wizard, name='ai_product_wizard'),
    
    # APIs auxiliares
    path('api/product/<int:product_id>/data/', views.get_product_data, name='get_product_data'),
    
    # Páginas de IA adicionais
    path('ai-product-wizard/', views.ai_product_wizard, name='ai_product_wizard_page'),
    path('bulk-generate-descriptions/', views.bulk_generate_descriptions, name='bulk_generate_descriptions'),
    
    # Redirects para IA
    path('ai/', RedirectView.as_view(url='/ai-status/')),
    path('generate/', RedirectView.as_view(url='/generate-description/')),
    
    # Redirects existentes (mantenha estes)
    path('recommendations/', RedirectView.as_view(url='/my-recommendations/')),
    path('api/product/<int:product_id>/update-description/', views.update_product_description, name='update_product_description'),
    
]