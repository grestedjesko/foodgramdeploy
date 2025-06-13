from rest_framework import serializers
from recipes.models import (Ingredient,
                            Recipe,
                            IngredientInRecipe,
                            Favorite,
                            ShoppingCart)
from drf_extra_fields.fields import Base64ImageField
from api.serializers.users import CustomUserSerializer  # путь поправь, если другой

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
    author = CustomUserSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'author', 'name', 'text', 'image', 'cooking_time',
            'ingredients', 'is_favorited', 'is_in_shopping_cart'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return ""

    def get_ingredients(self, obj):
        ingredients = IngredientInRecipe.objects.filter(recipe=obj)
        return IngredientInRecipeSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated and
            Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated and
            ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

class RecipeCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ['id', 'author', 'name', 'text', 'image', 'cooking_time', 'ingredients']

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужен хотя бы один ингредиент.')

        seen = set()
        for item in value:
            ingredient_id = item.get('id')
            amount = item.get('amount')

            if ingredient_id in seen:
                raise serializers.ValidationError('Ингредиенты не должны повторяться.')
            seen.add(ingredient_id)

            if not isinstance(amount, int) or amount < 1:
                raise serializers.ValidationError(
                    f'Количество ингредиента (id={ingredient_id}) должно быть больше нуля.'
                )

            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    f'Ингредиент с id={ingredient_id} не существует.'
                )

        return value

    def validate_image(self, value):
        if not value or (isinstance(value, str) and not value.strip()):
            raise serializers.ValidationError('Поле image обязательно и не может быть пустым.')
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее 1 минуты.'
            )
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)

        ingredient_objs = []
        for item in ingredients_data:
            try:
                ingredient = Ingredient.objects.get(id=item['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f'Ингредиент с id={item["id"]} не существует.'
                )
            ingredient_objs.append(IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient,
                amount=item['amount']
            ))

        IngredientInRecipe.objects.bulk_create(ingredient_objs)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.get('ingredients')
        if ingredients_data is None:
            raise serializers.ValidationError({
                'ingredients': 'Это поле обязательно при обновлении рецепта.'
            })

        # Обновим основные поля
        for attr, value in validated_data.items():
            if attr != 'ingredients':  # не перезаписываем их напрямую
                setattr(instance, attr, value)
        instance.save()

        # Очистим старые ингредиенты
        instance.ingredients.clear()
        IngredientInRecipe.objects.filter(recipe=instance).delete()

        IngredientInRecipe.objects.bulk_create([
            IngredientInRecipe(
                recipe=instance,
                ingredient=Ingredient.objects.get(id=item['id']),
                amount=item['amount']
            ) for item in ingredients_data
        ])

        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
