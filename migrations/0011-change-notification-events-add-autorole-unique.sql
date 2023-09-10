CREATE OR REPLACE FUNCTION notify_event() RETURNS TRIGGER AS $$
    DECLARE
        record RECORD;
        payload JSON;
    BEGIN
        IF (TG_OP = 'DELETE') THEN
            record = OLD;
        ELSE
            record = NEW;
        END IF;
        payload = json_build_object('table', TG_TABLE_NAME,
            'action', TG_OP,
            'id', record.id);

        PERFORM pg_notify('events', payload::text);
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;



alter table autorole add unique (role_id);