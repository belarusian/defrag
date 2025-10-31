# User Guide

## User Engagement Scoring

Our system calculates user engagement scores based on three key metrics:

### Scoring Algorithm

The engagement score is computed using weighted factors:
- Visit frequency (30% weight)
- Click activity (50% weight)
- Time spent on platform (20% weight)

Each metric is normalized to a 0-1 range:
- Visits: normalized by dividing by 100
- Clicks: normalized by dividing by 50
- Time spent: normalized by dividing by 3600 seconds (1 hour)

The final score is a weighted sum of these normalized values, rounded to 2 decimal places.

This scoring helps identify highly engaged users for targeted campaigns.

## Payment Processing

Our payment system supports multiple currencies and payment methods.

### Supported Features

- Multi-currency support (USD, EUR, GBP, JPY)
- Transaction validation
- Unique transaction ID generation

### Payment Flow

When processing a payment:
1. Validate the amount (must be positive)
2. Check currency is supported
3. Generate unique transaction identifier
4. Return transaction ID for tracking

Invalid amounts or unsupported currencies will raise errors.
