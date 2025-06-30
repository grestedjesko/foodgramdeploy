from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from api.serializers.users import CustomUserSerializer
from recipes.models import (
    Ingredient,
    Recipe,
    IngredientInRecipe,
    Favorite,
    ShoppingCart
)


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


class IngredientWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


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
        ingredients = obj.ingredient_amounts.select_related('ingredient').all()
        return IngredientInRecipeSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user or not user.is_authenticated:
            return False
        favorited_ids = self.context.get('favorited_ids')
        if favorited_ids is not None:
            return obj.id in favorited_ids
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user or not user.is_authenticated:
            return False
        shopping_cart_ids = self.context.get('shopping_cart_ids')
        if shopping_cart_ids is not None:
            return obj.id in shopping_cart_ids
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = IngredientWriteSerializer(many=True, write_only=True)
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ['id',
                  'author',
                  'name',
                  'text',
                  'image',
                  'cooking_time',
                  'ingredients']

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Нужен хотя бы один ингредиент.'
            )

        ingredient_ids = [item['id'] for item in value]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        existing_ids = set(
            Ingredient.objects
            .filter(id__in=ingredient_ids)
            .values_list('id', flat=True)
        )
        missing = set(ingredient_ids) - existing_ids
        if missing:
            raise serializers.ValidationError(
                f'Ингредиенты с id={", ".join(map(str, missing))} не существуют.'
            )
        return value

    def validate_image(self, value):
        if not value or (isinstance(value, str) and not value.strip()):
            raise serializers.ValidationError(
                'Поле image обязательно и не может быть пустым.'
            )
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее 1 минуты.'
            )
        return value

    def _set_ingredients(self, recipe, ingredients_data):
        IngredientInRecipe.objects.filter(recipe=recipe).delete()
        bulk = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=item['id']),
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        IngredientInRecipe.objects.bulk_create(bulk)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self._set_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.get('ingredients')
        if ingredients_data is None:
            raise serializers.ValidationError({
                'ingredients': 'Это поле обязательно при обновлении рецепта.'
            })

        for attr, value in validated_data.items():
            if attr != 'ingredients':
                setattr(instance, attr, value)
        instance.save()

        self._set_ingredients(instance, ingredients_data)
        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
