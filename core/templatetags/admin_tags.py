from django import template

register = template.Library()

@register.filter
def get_type_badge_class(type_declaration):
    """Retourne la classe CSS pour le badge selon le type de déclaration"""
    if type_declaration == 'perdu':
        return 'badge-warning'
    else:
        return 'badge-info'

@register.filter
def get_status_badge_class(statut):
    """Retourne la classe CSS pour le badge selon le statut"""
    status_classes = {
        'cree': 'badge-secondary',
        'valide': 'badge-success',
        'publie': 'badge-primary',
        'restitue': 'badge-info',
        'rejete': 'badge-danger',
        'en_validation': 'badge-warning',
    }
    return status_classes.get(statut, 'badge-secondary')

@register.filter
def get_priority_class(priorite):
    """Retourne la classe CSS pour la priorité"""
    if priorite == 3:
        return 'priority-high'
    elif priorite == 2:
        return 'priority-medium'
    else:
        return 'priority-low'