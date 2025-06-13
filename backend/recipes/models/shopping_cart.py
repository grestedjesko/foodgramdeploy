from django.db import models
from django.conf import settings
from recipes.models import Recipe


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='shopping_cart',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='in_shopping_carts',
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Покупка'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в корзину'
