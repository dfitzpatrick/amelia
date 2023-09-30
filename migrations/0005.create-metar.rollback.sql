DROP TRIGGER IF EXISTS notify_metar_channels_event ON MetarChannel CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON MetarChannel CASCADE;
DROP INDEX IF EXISTS metar_config_guildid_key CASCADE;
DROP INDEX IF EXISTS metar_config_id_pkey CASCADE;
DROP TABLE IF EXISTS MetarChannel CASCADE;

DROP TRIGGER IF EXISTS notify_metar_config_event ON MetarConfig CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON MetarConfig CASCADE;
DROP INDEX IF EXISTS metar_config_guildid_key CASCADE;
DROP INDEX IF EXISTS metar_config_id_pkey CASCADE;
DROP TABLE IF EXISTS  MetarConfig CASCADE;
