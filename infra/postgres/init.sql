CREATE TABLE IF NOT EXISTS products (
  id BIGSERIAL PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Users / auth
CREATE TABLE IF NOT EXISTS users (
  email TEXT PRIMARY KEY,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL CHECK (role IN ('customer', 'florist')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  total_cents INTEGER NOT NULL CHECK (total_cents >= 0)
);

CREATE TABLE IF NOT EXISTS order_items (
  order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL CHECK (quantity >= 1),
  unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
  PRIMARY KEY (order_id, product_id)
);

INSERT INTO products (sku, name, description, price_cents)
VALUES
  ('PINK-001', 'Notebook', 'Minimal stationery for focused work.', 1299),
  ('PINK-002', 'Bouquet', 'A soft palette for any occasion.', 3499),
  ('PINK-003', 'Skincare', 'Gentle daily essentials.', 2599)
ON CONFLICT (sku) DO NOTHING;
