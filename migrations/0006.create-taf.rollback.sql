DROP TRIGGER IF EXISTS notify_taf_channels_event ON TafChannel CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON TafChannel CASCADE;
DROP INDEX IF EXISTS taf_config_guildid_key CASCADE;
DROP INDEX IF EXISTS taf_config_id_pkey CASCADE;
DROP TABLE IF EXISTS TafChannel CASCADE;

DROP TRIGGER IF EXISTS notify_taf_config_event ON TafConfig CASCADE;
DROP TRIGGER IF EXISTS set_timestamp ON TafConfig CASCADE;
DROP INDEX IF EXISTS taf_config_guildid_key CASCADE;
DROP INDEX IF EXISTS taf_config_id_pkey CASCADE;
DROP TABLE IF EXISTS  TafConfig CASCADE;
