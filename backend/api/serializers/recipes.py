from rest_framework import serializers
from recipes.models import Ingredient, Recipe, IngredientInRecipe
from drf_extra_fields.fields import Base64ImageField


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeListSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField()
    author = serializers.StringRelatedField()

    class Meta:
        model = Recipe
        fields = ['id', 'author', 'name', 'text', 'image', 'cooking_time', 'ingredients']

    def get_ingredients(self, obj):
        ingredients = IngredientInRecipe.objects.filter(recipe=obj)
        return IngredientInRecipeSerializer(ingredients, many=True).data


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'author', 'name', 'text', 'image', 'cooking_time', 'ingredients']

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужен хотя бы один ингредиент.')
        seen = set()
        for item in value:
            if item['id'] in seen:
                raise serializers.ValidationError('Ингредиенты не должны повторяться.')
            seen.add(item['id'])
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)

        IngredientInRecipe.objects.bulk_create([
            IngredientInRecipe(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=item['id']),
                amount=item['amount']
            ) for item in ingredients_data
        ])

        return recipe

class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
