from django.urls import path

from stock.views import stocks_list, stock_detail, stock_buy, account, stock_sell

urlpatterns = [
    path('list/', stocks_list, name='list'),
    path('detail/<int:pk>/', stock_detail, name='detail'),
    path('buy/<int:pk>/', stock_buy, name='buy'),
    path('sell/<int:pk>/', stock_sell, name='sell'),
    path('account/', account, name='account'),
]
