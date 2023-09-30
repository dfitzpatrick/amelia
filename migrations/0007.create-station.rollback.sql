DROP TRIGGER IF EXISTS notify_station_channels_event ON StationChannel CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON StationChannel CASCADE;
DROP INDEX IF EXISTS station_channel_guildid_key CASCADE;
DROP INDEX IF EXISTS station_channel_id_pkey CASCADE;
DROP TABLE IF EXISTS StationChannel CASCADE;

DROP TRIGGER IF EXISTS notify_station_config_event ON StationConfig CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON StationConfig CASCADE;
DROP INDEX IF EXISTS station_config_guildid_key CASCADE;
DROP INDEX IF EXISTS station_config_id_pkey CASCADE;
DROP TABLE IF EXISTS StationConfig CASCADE;
