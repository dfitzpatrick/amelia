CREATE TABLE StationConfig
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    restrict_channel BOOLEAN NOT NULL DEFAULT TRUE,
    delete_interval INT NOT NULL DEFAULT 5,


    CONSTRAINT fk_server_guild_id_station_config_guild_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);

CREATE UNIQUE INDEX station_config_id_pkey on StationConfig (id);
CREATE INDEX station_config_guildid_key on StationConfig (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON StationConfig
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_station_config_event
    AFTER INSERT OR UPDATE OR DELETE ON StationConfig
        FOR EACH ROW EXECUTE PROCEDURE notify_event();

CREATE TABLE StationChannel
(
    id SERIAL NOT NULL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,

    CONSTRAINT fk_station_channel_server_id
        FOREIGN KEY (guild_id)
            REFERENCES Server(guild_id)
            ON DELETE CASCADE
);
CREATE UNIQUE INDEX station_channel_id_pkey on StationChannel (id);
CREATE INDEX station_channel_guildid_key on StationChannel (guild_id);

CREATE TRIGGER set_timestamp
        BEFORE UPDATE ON StationChannel
        FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER notify_station_channels_event
    AFTER INSERT OR UPDATE OR DELETE ON StationChannel
        FOR EACH ROW EXECUTE PROCEDURE notify_event();