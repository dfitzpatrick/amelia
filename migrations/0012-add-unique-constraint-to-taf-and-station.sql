ALTER TABLE tafconfig
ADD CONSTRAINT unique_tafconfig_guildid UNIQUE (guild_id);


ALTER TABLE stationconfig
ADD CONSTRAINT unique_stationconfig_guildid UNIQUE (guild_id);


ALTER TABLE metarchannel
ADD CONSTRAINT unique_metarchannel_channelid UNIQUE (channel_id);

ALTER TABLE tafchannel
ADD CONSTRAINT unique_tafchannel_channel_id UNIQUE (channel_id);

ALTER TABLE stationchannel
ADD CONSTRAINT unique_stationchannel_channel_id UNIQUE (channel_id);