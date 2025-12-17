from rest_framework import serializers
from .models import Region, Prefecture, StructureLocale, Signalement


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'nom']


class PrefectureSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)  # 🔗 pour afficher le nom de la région

    class Meta:
        model = Prefecture
        fields = ['id', 'nom', 'region']


class StructureLocaleSerializer(serializers.ModelSerializer):
    prefecture = PrefectureSerializer(read_only=True)  # 🔗 pour afficher le nom de la préfecture

    class Meta:
        model = StructureLocale
        fields = ['id', 'nom', 'prefecture']


class SignalementSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    prefecture = PrefectureSerializer(read_only=True)
    structure_locale = StructureLocaleSerializer(read_only=True)

    class Meta:
        model = Signalement
        fields = '__all__'
