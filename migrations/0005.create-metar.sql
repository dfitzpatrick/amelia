CREATE TABLE MetarConfig
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL UNIQUE,
    restrict_channel BOOLEAN NOT NULL DEFAULT TRUE,
    delete_interval INT NOT NULL DEFAULT 5,


    CONSTRAINT fk_server_guild_id_metar_config_guild_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);

CREATE UNIQUE INDEX metar_config_id_pkey on MetarConfig (id);
CREATE INDEX metar_config_guildid_key on MetarConfig (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON MetarConfig
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_metar_config_event
    AFTER INSERT OR UPDATE OR DELETE ON MetarConfig
        FOR EACH ROW EXECUTE PROCEDURE notify_event();

CREATE TABLE MetarChannel
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,

    CONSTRAINT fk_metar_channel_server_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);
CREATE UNIQUE INDEX metar_config_channel_id_pkey on MetarChannel (id);
CREATE INDEX metar_config_channel_guildid_key on MetarChannel (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON MetarChannel
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_metar_channels_event
    AFTER INSERT OR UPDATE OR DELETE ON MetarChannel
        FOR EACH ROW EXECUTE PROCEDURE notify_event();