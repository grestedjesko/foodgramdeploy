from rest_framework import serializers
from recipes.models import Recipe
from api.serializers.recipes import RecipeShortSerializer


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields
