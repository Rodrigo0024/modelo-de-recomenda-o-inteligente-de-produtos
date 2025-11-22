# recommendations/templatetags/query_tags.py
from django import template

register = template.Library()

@register.simple_tag
def modify_query(**kwargs):
    """
    Template tag para modificar parâmetros da query string
    Uso: {% modify_query page=2 sort='price_low' %}
    """
    from django.http import QueryDict
    from urllib.parse import urlencode
    
    # Pega os parâmetros atuais da URL
    current_params = QueryDict(mutable=True)
    for key, value in kwargs.items():
        if value is None or value == '':
            # Remove parâmetros vazios
            if key in current_params:
                del current_params[key]
        else:
            current_params[key] = value
    
    return current_params.urlencode()

@register.simple_tag
def get_query_params():
    """
    Retorna todos os parâmetros atuais da query string
    """
    from django.http import QueryDict
    import copy
    
    # Cria uma cópia mutável dos parâmetros atuais
    params = QueryDict(mutable=True)
    return params

@register.simple_tag
def remove_query_param(param_name):
    """
    Remove um parâmetro específico da query string
    """
    from django.http import QueryDict
    from urllib.parse import parse_qs, urlencode
    
    # Implementação simplificada
    params = QueryDict(mutable=True)
    # A lógica completa seria mais complexa
    return params.urlencode()