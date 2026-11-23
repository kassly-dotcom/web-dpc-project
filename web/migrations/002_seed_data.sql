INSERT INTO users (name, role)
VALUES
    ('Student 1', 'student'),
    ('Student 2', 'student'),
    ('Commandant', 'commandant');

INSERT INTO floor (limit_w, used_w, timezone)
VALUES (10000, 0, 'Europe/Kyiv');

INSERT INTO machine (floor_id, kind, power_w)
VALUES
    (1, 'washer', 2000),
    (1, 'washer', 2000),
    (1, 'washer', 2000),
    (1, 'washer', 2000),
    (1, 'washer', 2000),
    (1, 'washer', 2000),
    (1, 'dryer', 2000),
    (1, 'dryer', 2000),
    (1, 'dryer', 2000),
    (1, 'dryer', 2000);
    