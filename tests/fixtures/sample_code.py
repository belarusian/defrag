"""
Sample code for testing semantic analysis.

This module contains functions that should match to documentation.
"""


def calculate_user_score(user_data):
    """
    Calculate user engagement score based on activity.

    Args:
        user_data: Dictionary with user metrics

    Returns:
        Float score between 0.0 and 1.0
    """
    if not user_data:
        return 0.0

    visits = user_data.get('visits', 0)
    clicks = user_data.get('clicks', 0)
    time_spent = user_data.get('time_spent', 0)

    # Weight factors
    visit_weight = 0.3
    click_weight = 0.5
    time_weight = 0.2

    # Normalize and calculate weighted score
    normalized_visits = min(visits / 100.0, 1.0)
    normalized_clicks = min(clicks / 50.0, 1.0)
    normalized_time = min(time_spent / 3600.0, 1.0)

    score = (
        normalized_visits * visit_weight +
        normalized_clicks * click_weight +
        normalized_time * time_weight
    )

    return round(score, 2)


def process_payment(amount, currency, payment_method):
    """
    Process a payment transaction.

    This function handles payment processing through various providers.
    It validates the input, applies currency conversion if needed,
    and returns a transaction ID.

    Args:
        amount: Payment amount (positive float)
        currency: ISO currency code (e.g., 'USD', 'EUR')
        payment_method: Payment method identifier

    Returns:
        Transaction ID string

    Raises:
        ValueError: If amount is invalid or currency not supported
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")

    supported_currencies = ['USD', 'EUR', 'GBP', 'JPY']
    if currency not in supported_currencies:
        raise ValueError(f"Unsupported currency: {currency}")

    # Simulate payment processing
    transaction_id = f"TXN-{currency}-{int(amount * 100)}"

    return transaction_id


class CacheManager:
    """Manages in-memory cache with TTL support."""

    def __init__(self, default_ttl=3600):
        """
        Initialize cache manager.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.timestamps = {}

    def get(self, key):
        """Get value from cache if not expired."""
        if key not in self.cache:
            return None

        # Check expiration
        import time
        if time.time() - self.timestamps[key] > self.default_ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None

        return self.cache[key]

    def set(self, key, value):
        """Set value in cache with current timestamp."""
        import time
        self.cache[key] = value
        self.timestamps[key] = time.time()

    def clear(self):
        """Clear all cached values."""
        self.cache.clear()
        self.timestamps.clear()
