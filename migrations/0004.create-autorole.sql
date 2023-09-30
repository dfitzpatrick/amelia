CREATE TABLE AutoRole
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,


    CONSTRAINT fk_server_guild_id_auto_role_guild_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);

CREATE UNIQUE INDEX auto_role_id_pkey on AutoRole (id);
CREATE INDEX auto_role_guildid_key on AutoRole (guild_id);



CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON AutoRole
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_auto_role_event
    AFTER INSERT OR UPDATE OR DELETE ON AutoRole
        FOR EACH ROW EXECUTE PROCEDURE notify_event();