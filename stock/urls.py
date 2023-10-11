from django.urls import path

from stock.views import stocks_list

urlpatterns = [
    path('list/', stocks_list)
]
