# Legacy Features

## Old Authentication System

Our previous authentication system used session tokens stored in cookies.

### How it worked

1. User login generated a session token
2. Token stored in browser cookie
3. Server validated token on each request
4. Token expired after 24 hours

This system was replaced with JWT-based authentication in v2.0.

## Deprecated Batch Processor

The batch processor handled nightly data aggregation jobs. It ran at 2 AM daily and processed user activity logs into summary tables.

This functionality has been moved to real-time streaming architecture.
