"""
Currency utilities for BilboT
"""

def get_currency_symbol(currency_code):
    """
    Get the currency symbol for a given currency code.
    
    Args:
        currency_code (str): Currency code (e.g., USD, EUR)
        
    Returns:
        str: Currency symbol
    """
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'INR': '₹',
        'RUB': '₽',
        'KRW': '₩',
        'BTC': '₿',
        'CAD': 'C$',
        'AUD': 'A$',
        'NZD': 'NZ$',
        'HKD': 'HK$',
        'SGD': 'S$',
        'CNY': '¥',
        'CHF': 'CHF',
        'SEK': 'kr',
        'ZAR': 'R',
        'THB': '฿',
    }
    
    return currency_symbols.get(currency_code.upper(), '$')
