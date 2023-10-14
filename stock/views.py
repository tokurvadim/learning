from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.urls import resolve
import re

from stock.models import Stock, AccountCurrency, AccountStock
from stock.forms import BuySellForm

# Create your views here.


def stocks_list(request):
    stocks = Stock.objects.all()
    context = {
        'stocks': stocks,
    }
    return render(request, 'stocks.html', context)


@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    ref = re.findall(r"/(account|list)/", request.META.get('HTTP_REFERER'))
    context = {
        'stock': stock,
        'form': BuySellForm(initial={'price': stock.get_random_price()}),
        'referer': ref[0]
    }
    return render(request, 'stock.html', context)


@login_required
def stock_buy(request, pk):
    if request.method != 'POST':
        return redirect('stock:list', pk=pk)

    stock = get_object_or_404(Stock, pk=pk)
    form = BuySellForm(request.POST)
    request.url_path = resolve(request.path).url_name

    if form.is_valid():
        amount = form.cleaned_data['amount']
        price = form.cleaned_data['price']
        buy_cost = amount * price

        acc_stock, created = AccountStock.objects.get_or_create(account=request.user.account, stock=stock, defaults={
            'average_buy_cost': 0,
            'amount': 0,
        })
        current_cost = acc_stock.average_buy_cost * acc_stock.amount

        total_cost = current_cost + buy_cost
        total_amount = acc_stock.amount + amount

        acc_stock.amount = total_amount
        acc_stock.average_buy_cost = total_cost / total_amount

        acc_currency, created = AccountCurrency.objects.get_or_create(account=request.user.account,
                                                                      currency=stock.currency,
                                                                      defaults={
                                                                          'amount': 0,
                                                                      })

        if acc_currency.amount < buy_cost:
            form.add_error(None, f'На счете недостаточно средств в валюте {stock.currency.sign}')
        else:
            acc_currency.amount -= buy_cost
            if acc_currency == 0:
                acc_currency.delete()
            acc_stock.save()
            acc_currency.save()

            stocks = [
                {
                    'ticket': acc_stock.stock.ticket,
                    'amount': acc_stock.amount,
                    'avg': acc_stock.average_buy_cost,
                    'pk': acc_stock.stock.pk
                } for acc_stock in request.user.account.accountstock_set.select_related('stock').all()
            ]
            cache.set(f'stocks_{request.user.username}', stocks)

            curr = [
                {
                    'amount': acc_currency.amount,
                    'sign': acc_currency.currency.sign
                } for acc_currency in request.user.account.accountcurrency_set.select_related('currency').all() if acc_currency.amount != 0
            ]
            print(curr)
            cache.set(f'currencies_{request.user.username}', curr)

            return redirect('stock:list')

    context = {
        'stock': get_object_or_404(Stock, pk=pk),
        'form': form,
        'referer': 'list'
    }
    return render(request, 'stock.html', context)


@login_required
def stock_sell(request, pk):
    if request.method != 'POST':
        return redirect('stock:detail', pk=pk)

    stock = get_object_or_404(Stock, pk=pk)
    form = BuySellForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        price = form.cleaned_data['price']
        sell_cost = amount * price

        acc_stock, created = AccountStock.objects.get_or_create(account=request.user.account, stock=stock, defaults={
            'average_buy_cost': 0,
            'amount': 0,
        })

        acc_currency, created = AccountCurrency.objects.get_or_create(account=request.user.account,
                                                                      currency=stock.currency,
                                                                      defaults={
                                                                          'amount': 0,
                                                                      })

        if acc_stock.amount < amount:
            form.add_error(None, f'У Вас нет столько акций {acc_stock.stock} в Вашем порфтеле')
        else:
            acc_stock.amount -= amount
            if acc_stock.amount == 0:
                acc_stock.delete()

            acc_currency.amount += sell_cost
            acc_stock.save()
            acc_currency.save()

            stocks = [
                {
                    'ticket': acc_stock.stock.ticket,
                    'amount': acc_stock.amount,
                    'avg': acc_stock.average_buy_cost,
                    'pk': acc_stock.stock.pk
                } for acc_stock in request.user.account.accountstock_set.select_related('stock').all() if acc_stock.amount != 0
            ]
            cache.set(f'stocks_{request.user.username}', stocks)

            curr = [
                {
                    'amount': acc_currency.amount,
                    'sign': acc_currency.currency.sign
                } for acc_currency in request.user.account.accountcurrency_set.select_related('currency').all()
            ]
            cache.set(f'currencies_{request.user.username}', curr)

            return redirect('stock:list')
    context = {
        'stock': get_object_or_404(Stock, pk=pk),
        'form': form,
        'referer': 'account'
    }

    return render(request, 'stock.html', context)


@login_required
def account(request):
    acc_currencies = cache.get(f'currencies_{request.user.username}')
    acc_stocks = cache.get(f'stocks_{request.user.username}')
    stocks = Stock.objects.all()

    if acc_currencies is None:
        acc_currencies = [
            {
                'amount': acc_currency.amount,
                'sign': acc_currency.currency.sign
            } for acc_currency in request.user.account.accountcurrency_set.select_related('currency') if acc_currency.amount != 0
        ]
        cache.set(f'currencies_{request.user.username}', acc_currencies, 300)

    if acc_stocks is None:
        acc_stocks = [
            {
                'ticket': acc_stock.stock.ticket,
                'amount': acc_stock.amount,
                'avg': acc_stock.average_buy_cost,
                'pk': acc_stock.stock.pk
            } for acc_stock in request.user.account.accountstock_set.select_related('stock').all() if acc_stock.amount != 0
        ]
        cache.set(f'stocks_{request.user.username}', acc_stocks, 300)

    context = {
        'acc_currencies': acc_currencies,
        'acc_stocks': acc_stocks,
        'stocks': stocks
    }

    return render(request, template_name='account.html', context=context)
