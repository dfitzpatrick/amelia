CREATE TABLE AutoPins
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    parent_id BIGINT NOT NULL UNIQUE,


    CONSTRAINT fk_server_guild_id_auto_pin_guild_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);


CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON AutoPins
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_autopins_event
    AFTER INSERT OR UPDATE OR DELETE ON AutoPins
        FOR EACH ROW EXECUTE PROCEDURE notify_event();