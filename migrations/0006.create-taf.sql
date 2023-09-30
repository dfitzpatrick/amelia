CREATE TABLE TafConfig
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    restrict_channel BOOLEAN NOT NULL DEFAULT TRUE,
    delete_interval INT NOT NULL DEFAULT 5,


    CONSTRAINT fk_server_guild_id_taf_config_guild_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);

CREATE UNIQUE INDEX taf_config_id_pkey on TafConfig (id);
CREATE INDEX taf_config_guildid_key on TafConfig (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON TafConfig
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_taf_config_event
    AFTER INSERT OR UPDATE OR DELETE ON TafConfig
        FOR EACH ROW EXECUTE PROCEDURE notify_event();

CREATE TABLE TafChannel
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,

    CONSTRAINT fk_taf_channel_server_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);
CREATE UNIQUE INDEX taf_config_channel_id_pkey on TafChannel (id);
CREATE INDEX taf_config_channel_guildid_key on TafChannel (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON TafChannel
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_taf_channels_event
    AFTER INSERT OR UPDATE OR DELETE ON TafChannel
        FOR EACH ROW EXECUTE PROCEDURE notify_event();