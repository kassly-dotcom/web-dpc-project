-- PRIMARY KEY
INSERT INTO users (id, name, role)
VALUES (1, 'Test Student', 'student');

-- FOREIGN KEY
INSERT INTO machine (floor_id, kind, power_w)
VALUES (999, 'washer', 2000);

-- NOT NULL
INSERT INTO users (name, role)
VALUES (NULL, 'student');

-- CHECK: power
INSERT INTO machine (floor_id, kind, power_w)
VALUES (1, 'washer', -2000);

-- CHECK: floor power limit
UPDATE floor
SET used_w = 12000
WHERE id = 1;

-- CHECK: role
INSERT INTO users (name, role)
VALUES ('Test', 'admin');

-- UNIQUE: active cycle
BEGIN;

INSERT INTO cycle (
    user_id, machine_id, program,
    duration_min, price_kopecks, expires_at
)
VALUES (1, 1, 'standard', 60, 5000,
        now() + interval '10 minutes');

INSERT INTO cycle (
    user_id, machine_id, program,
    duration_min, price_kopecks, expires_at
)
VALUES (2, 1, 'standard', 60, 5000,
        now() + interval '10 minutes');

ROLLBACK;