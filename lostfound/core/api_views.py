# core/api_views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Region, Prefecture, StructureLocale

@api_view(['GET'])
def api_regions(request):
    """Renvoie la liste des régions"""
    data = [{"id": r.id, "nom": r.nom} for r in Region.objects.all()]
    return Response(data)

@api_view(['GET'])
def api_prefectures(request, region_id):
    """Renvoie les préfectures d'une région"""
    data = [{"id": p.id, "nom": p.nom} for p in Prefecture.objects.filter(region_id=region_id)]
    return Response(data)

@api_view(['GET'])
def api_structures(request, prefecture_id):
    """Renvoie les structures locales d'une préfecture"""
    data = [{"id": s.id, "nom": s.nom, "type_structure": s.type_structure} for s in StructureLocale.objects.filter(prefecture_id=prefecture_id)]
    return Response(data)
