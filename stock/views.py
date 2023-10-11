from django.shortcuts import render

from stock.models import Stock

# Create your views here.


def stocks_list(request):
    stocks = Stock.objects.all()
    context = {
        'stocks': stocks,
    }
    return render(request, 'stocks.html', context)
