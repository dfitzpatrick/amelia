ALTER TABLE autorole
DROP CONSTRAINT if exists fk_server_guild_id_auto_role_guild_id;

ALTER TABLE autorole
ADD CONSTRAINT fk_guilds_guild_id_auto_role_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE metarconfig
DROP CONSTRAINT if exists fk_server_guild_id_metar_config_guild_id;

ALTER TABLE metarconfig
ADD CONSTRAINT fk_guilds_guild_id_metarconfig_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE metarchannel
DROP CONSTRAINT if exists fk_metar_channel_server_id;

ALTER TABLE metarchannel
ADD CONSTRAINT fk_guilds_guild_id_metarchannel_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE tafconfig
DROP CONSTRAINT if exists fk_server_guild_id_taf_config_guild_id;

ALTER TABLE tafconfig
ADD CONSTRAINT fk_guilds_guild_id_tafconfig_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE tafchannel
DROP CONSTRAINT if exists fk_taf_channel_server_id;

ALTER TABLE tafchannel
ADD CONSTRAINT fk_guilds_guild_id_tafchannel_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;



ALTER TABLE stationconfig
DROP CONSTRAINT if exists fk_server_guild_id_station_config_guild_id;

ALTER TABLE stationconfig
ADD CONSTRAINT fk_guilds_guild_id_stationconfig_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE stationchannel
DROP CONSTRAINT if exists fk_station_channel_server_id;

ALTER TABLE stationchannel
ADD CONSTRAINT fk_guilds_guild_id_stationfchannel_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;


ALTER TABLE autopins
DROP CONSTRAINT if exists fk_server_guild_id_auto_pin_guild_id;

ALTER TABLE autopins
ADD CONSTRAINT fk_guilds_guild_id_autopins_guild_id
    FOREIGN KEY (guild_id)
    REFERENCES Guilds(guild_id)
    ON DELETE CASCADE;