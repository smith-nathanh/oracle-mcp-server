-- Create testuser and grant permissions
-- This runs as SYSTEM user in the TESTDB pluggable database

ALTER SESSION SET CONTAINER = TESTDB;

-- Create the testuser if it doesn't exist
CREATE USER testuser IDENTIFIED BY "TestUser123!"
  DEFAULT TABLESPACE USERS
  QUOTA UNLIMITED ON USERS;

-- Grant necessary privileges
GRANT CONNECT, RESOURCE TO testuser;
GRANT CREATE SESSION TO testuser;
GRANT CREATE TABLE TO testuser;
GRANT CREATE VIEW TO testuser;
GRANT CREATE PROCEDURE TO testuser;
GRANT CREATE SEQUENCE TO testuser;
GRANT CREATE TRIGGER TO testuser;

-- Grant additional system privileges needed
GRANT SELECT ANY DICTIONARY TO testuser;
GRANT SELECT ON ALL_TABLES TO testuser;
GRANT SELECT ON ALL_TAB_COLUMNS TO testuser;
GRANT SELECT ON ALL_VIEWS TO testuser;
GRANT SELECT ON ALL_PROCEDURES TO testuser;

COMMIT;
