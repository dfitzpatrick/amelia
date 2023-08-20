ALTER TABLE IF EXISTS Server
    RENAME COLUMN created_at TO joined;

ALTER TABLE IF EXISTS Server
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS auto_delete_commands;


DROP TRIGGER IF EXISTS set_timestamp ON Server CASCADE;

