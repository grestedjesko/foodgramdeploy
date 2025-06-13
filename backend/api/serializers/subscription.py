from rest_framework import serializers
from users.models.subscription import Subscription
from api.serializers.users import UserSerializer
from api.serializers.recipes import RecipeShortSerializer


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя.'
            )
        ]

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError('Нельзя подписаться на самого себя.')
        return data


class AuthorWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeShortSerializer(recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
