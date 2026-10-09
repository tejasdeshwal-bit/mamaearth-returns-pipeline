-- Part 1, Task 3: business reports. Run against the raw (uncleaned) data.

-- a) Order totals: count, total revenue, average order value (NULL discount counts as 0%)
--| Output:
--| total_orders | total_revenue | avg_order_value
--| 180 | 99860.2 | 554.78
--| (1 rows)
SELECT COUNT(*)                                                     AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS avg_order_value
FROM orders o
JOIN products p ON p.product_id = o.product_id;

-- b) COUNT(*) vs COUNT(column): COUNT(rating) skips NULLs, so the gap shows the missing ratings
--| Output:
--| count_star | count_rating | missing_ratings
--| 180 | 165 | 15
--| (1 rows)
SELECT COUNT(*)                AS count_star,
       COUNT(rating)           AS count_rating,
       COUNT(*) - COUNT(rating) AS missing_ratings
FROM orders;

-- c1) Customers with zero orders: LEFT JOIN keeps customers even with no match
--| Output:
--| customer_id | name
--| C045 | Vihaan
--| (1 rows)
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0;

-- c2) Independent cross-check with NOT IN (must return the same customer)
--| Output:
--| customer_id | name
--| C045 | Vihaan
--| (1 rows)
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- d) Return rate by city, keeping only cities above 20%
--| Output:
--| city | total_orders | returned_orders | return_rate_pct
--| Jaipur | 19 | 8 | 42.1
--| Lucknow | 49 | 15 | 30.6
--| Bangalore | 33 | 8 | 24.2
--| (3 rows)
SELECT c.city,
       COUNT(*)                                     AS total_orders,
       SUM(o.returned)                              AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;

-- e1) Top 5 customers by spend. Tie-break on customer_id ASC so equal spenders
--     always rank in the same order (makes LIMIT/OFFSET deterministic).
--| Output:
--| customer_id | name | total_spend
--| C043 | Reyansh | 12920.0
--| C026 | Isha | 8371.6
--| C008 | Meera | 4564.6
--| C011 | Arjun | 4111.0
--| C042 | Sanya | 3785.0
--| (5 rows)
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products  p ON p.product_id  = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 5;

-- e2) Ranks 3-5 only: skip the first 2 rows (OFFSET 2), then take 3
--| Output:
--| customer_id | name | total_spend
--| C008 | Meera | 4564.6
--| C011 | Arjun | 4111.0
--| C042 | Sanya | 3785.0
--| (3 rows)
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products  p ON p.product_id  = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;

-- f) Revenue by category using a three-table JOIN
--| Output:
--| category | order_count | category_revenue
--| Haircare | 54 | 44956.1
--| Skincare | 60 | 27346.0
--| Babycare | 30 | 16805.0
--| PersonalCare | 36 | 10753.1
--| (4 rows)
SELECT p.category,
       COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS category_revenue
FROM orders o
JOIN products  p ON p.product_id  = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY p.category
ORDER BY category_revenue DESC;

-- g) LIKE: customers whose name starts with 'A'
--| Output:
--| customer_id | name
--| C001 | Aarav
--| C003 | Aditi
--| C004 | Ananya
--| C011 | Arjun
--| C021 | Aryan
--| C030 | Anika
--| C031 | Aditya
--| C036 | Aisha
--| C041 | Ayaan
--| C044 | Aria
--| (10 rows)
SELECT customer_id, name
FROM customers
WHERE name LIKE 'A%'
ORDER BY customer_id;

-- h) DISTINCT acquisition sources
--| Output:
--| acquisition_source
--| Ad
--| Organic
--| Referral
--| Social
--| (4 rows)
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- i) ALTER TABLE adds a column, then one UPDATE with CASE fills every row (no WHERE)
--| Output: (statement executed, no result set)
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

--| Output: (statement executed, no result set)
UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

--| Output:
--| loyalty_tier | customers
--| Gold | 28
--| Silver | 17
--| (2 rows)
SELECT loyalty_tier, COUNT(*) AS customers
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
