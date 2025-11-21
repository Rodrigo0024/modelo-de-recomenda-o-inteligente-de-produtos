from django.contrib import admin
from .models import Product, UserInteraction, Recommendation

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'interaction_type', 'rating', 'timestamp']
    list_filter = ['interaction_type', 'timestamp']
    search_fields = ['user__username', 'product__name']
    ordering = ['-timestamp']

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'model_version', 'confidence_score', 'created_at']
    list_filter = ['model_version', 'created_at']
    ordering = ['-created_at']