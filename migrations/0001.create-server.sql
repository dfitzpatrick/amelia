CREATE TABLE Server
(
    id SERIAL NOT NULL PRIMARY KEY,
	guild_id BIGINT NOT NULL UNIQUE,
	joined TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delimiter VARCHAR(1) DEFAULT '!'
);

CREATE UNIQUE INDEX server_id_pkey on Server (id);
CREATE UNIQUE INDEX server_guildid_key on  Server (guild_id);



CREATE TRIGGER notify_server_event
    AFTER INSERT OR UPDATE OR DELETE ON Server
        FOR EACH ROW EXECUTE PROCEDURE notify_event();