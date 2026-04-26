from django.contrib import admin

from .models import Customer, Dataset, Depot, Item, Node, Order, Vehicle


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('dataset_id', 'name', 'user', 'created_at', 'expires_at')
    list_filter = ('user',)
    search_fields = ('name',)


admin.site.register(Node)
admin.site.register(Depot)
admin.site.register(Customer)
admin.site.register(Vehicle)
admin.site.register(Item)
admin.site.register(Order)
