-- Starter watchlist — edit freely, this is just for local dev/testing
insert into watchlist (symbol, type, name) values
  ('AAPL', 'stock', 'Apple Inc.'),
  ('MSFT', 'stock', 'Microsoft Corporation'),
  ('NVDA', 'stock', 'NVIDIA Corporation'),
  ('SPY', 'index', 'S&P 500 ETF'),
  ('QQQ', 'index', 'Nasdaq-100 ETF')
on conflict (symbol) do nothing;
