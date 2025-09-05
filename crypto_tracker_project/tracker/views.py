import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from .models import Cryptocurrency, PriceHistory, SearchHistory
from .forms import CryptocurrencySearchForm


def get_crypto_data(coin_id):
    try:
           url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API Error: {e}")
        return None


def populate_cryptocurrencies():
    popular_cryptos = [
        {'id': 'bitcoin', 'name': 'Bitcoin', 'symbol': 'BTC'},
        {'id': 'ethereum', 'name': 'Ethereum', 'symbol': 'ETH'},
        {'id': 'binancecoin', 'name': 'BNB', 'symbol': 'BNB'},
        {'id': 'ripple', 'name': 'XRP', 'symbol': 'XRP'},
        {'id': 'solana', 'name': 'Solana', 'symbol': 'SOL'},
        {'id': 'cardano', 'name': 'Cardano', 'symbol': 'ADA'},
        {'id': 'dogecoin', 'name': 'Dogecoin', 'symbol': 'DOGE'},
        {'id': 'polygon', 'name': 'Polygon', 'symbol': 'MATIC'},
        {'id': 'litecoin', 'name': 'Litecoin', 'symbol': 'LTC'},
        {'id': 'chainlink', 'name': 'Chainlink', 'symbol': 'LINK'},
    ]

    for crypto in popular_cryptos:
        Cryptocurrency.objects.get_or_create(
            coin_id=crypto['id'],
            defaults={
                'name': crypto['name'],
                'symbol': crypto['symbol']
            }
        )


def index(request):
    if not Cryptocurrency.objects.exists():
        populate_cryptocurrencies()

    form = CryptocurrencySearchForm()
    crypto_data = None
    selected_crypto = None

    if request.method == 'POST':
        form = CryptocurrencySearchForm(request.POST)
        if form.is_valid():
            selected_crypto = form.cleaned_data['cryptocurrency']
            api_data = get_crypto_data(selected_crypto.coin_id)

            if api_data and selected_crypto.coin_id in api_data:
                data = api_data[selected_crypto.coin_id]

                
                price_history = PriceHistory.objects.create(
                    cryptocurrency=selected_crypto,
                    price_usd=Decimal(str(data['usd'])),
                    market_cap=data.get('usd_market_cap'),
                    volume_24h=data.get('usd_24h_vol'),
                    price_change_24h=Decimal(str(data.get('usd_24h_change', 0)))
                )

                
                session_key = request.session.session_key
                if not session_key:
                    request.session.create()
                    session_key = request.session.session_key

                SearchHistory.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    cryptocurrency=selected_crypto,
                    session_key=session_key
                )

                crypto_data = {
                    'name': selected_crypto.name,
                    'symbol': selected_crypto.symbol,
                    'price': data['usd'],
                    'market_cap': data.get('usd_market_cap'),
                    'volume_24h': data.get('usd_24h_vol'),
                    'price_change_24h': data.get('usd_24h_change', 0)
                }
            else:
                messages.error(request, 'Failed to fetch cryptocurrency data. Please try again.')

    
    session_key = request.session.session_key
    if request.user.is_authenticated:
        recent_searches = SearchHistory.objects.filter(user=request.user)[:5]
    else:
        recent_searches = SearchHistory.objects.filter(session_key=session_key)[:5] if session_key else []

    context = {
        'form': form,
        'crypto_data': crypto_data,
        'selected_crypto': selected_crypto,
        'recent_searches': recent_searches
    }

    return render(request, 'tracker/index.html', context)


def price_history(request, crypto_id):
    cryptocurrency = get_object_or_404(Cryptocurrency, id=crypto_id)
    history = PriceHistory.objects.filter(cryptocurrency=cryptocurrency)[:20]

    context = {
        'cryptocurrency': cryptocurrency,
        'history': history
    }

    return render(request, 'tracker/history.html', context)


def api_refresh_price(request, crypto_id):
    if request.method == 'POST':
        cryptocurrency = get_object_or_404(Cryptocurrency, id=crypto_id)
        api_data = get_crypto_data(cryptocurrency.coin_id)

        if api_data and cryptocurrency.coin_id in api_data:
            data = api_data[cryptocurrency.coin_id]

        
            PriceHistory.objects.create(
                cryptocurrency=cryptocurrency,
                price_usd=Decimal(str(data['usd'])),
                market_cap=data.get('usd_market_cap'),
                volume_24h=data.get('usd_24h_vol'),
                price_change_24h=Decimal(str(data.get('usd_24h_change', 0)))
            )

            return JsonResponse({
                'success': True,
                'data': {
                    'price': data['usd'],
                    'market_cap': data.get('usd_market_cap'),
                    'volume_24h': data.get('usd_24h_vol'),
                    'price_change_24h': data.get('usd_24h_change', 0)
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Failed to fetch data'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})
