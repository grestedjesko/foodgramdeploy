from django.contrib import admin
from .models import Recipe, Ingredient, IngredientInRecipe
from users.models import CustomUser
from django.db.models import Count


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time', 'favorites_count')
    inlines = [IngredientInRecipeInline]
    search_fields = ['name', 'author__username']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(favorites_total=Count('favorited_by'))

    def favorites_count(self, obj):
        return obj.favorites_total

    favorites_count.short_description = 'В избранном'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ['name']


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('email',)
    search_fields = ('email', 'first_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация',
         {'fields': ('username', 'first_name', 'last_name', 'avatar')}),
        ('Права доступа',
         {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email',
                       'username',
                       'first_name',
                       'last_name',
                       'avatar',
                       'password1',
                       'password2',
                       'is_staff',
                       'is_active')}
         ),
    )
