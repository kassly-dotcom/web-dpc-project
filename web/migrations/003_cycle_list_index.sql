-- О1.5. Індекс для списку циклів користувача з курсорною пагінацією:
-- WHERE user_id = ? ORDER BY created_at DESC, id DESC.
CREATE INDEX ix_cycle_user_created
    ON cycle (user_id, created_at DESC, id DESC);
