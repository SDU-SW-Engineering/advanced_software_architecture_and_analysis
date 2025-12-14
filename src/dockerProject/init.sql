create schema pasta_db;

CREATE TABLE pasta_db.batches (
    id SERIAL PRIMARY KEY,               -- Auto-increment unique identifier for each batch
    blade_type CHAR(1) NOT NULL CHECK (blade_type IN ('A', 'B')), -- Type of blade (A or B)
    isFresh BOOLEAN NOT NULL,            -- Indicates if the batch is fresh (TRUE) or dry (FALSE)
    productionDate TIMESTAMP NOT NULL,   -- Date of production
    inStock INT NOT NULL CHECK (inStock >= 0)  -- Amount in stock
);

-- 5 rows for A-TRUE
INSERT INTO pasta_db.batches (blade_type, isFresh, productionDate, inStock) VALUES
('A', TRUE, NOW(), 10),
('A', TRUE, NOW(), 10),
('A', TRUE, NOW(), 10),
('A', TRUE, NOW(), 10),
('A', TRUE, NOW(), 10),

-- 5 rows for A-FALSE
('A', FALSE, NOW(), 10),
('A', FALSE, NOW(), 10),
('A', FALSE, NOW(), 10),
('A', FALSE, NOW(), 10),
('A', FALSE, NOW(), 10),

-- 5 rows for B-TRUE
('B', TRUE, NOW(), 10),
('B', TRUE, NOW(), 10),
('B', TRUE, NOW(), 10),
('B', TRUE, NOW(), 10),
('B', TRUE, NOW(), 10),

-- 5 rows for B-FALSE
('B', FALSE, NOW(), 10),
('B', FALSE, NOW(), 10),
('B', FALSE, NOW(), 10),
('B', FALSE, NOW(), 10),
('B', FALSE, NOW(), 10);