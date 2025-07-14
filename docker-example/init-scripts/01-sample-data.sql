-- Sample data setup for Oracle MCP Server testing
-- This script runs as SYSTEM and creates objects in the testuser schema
-- The gvenzl/oracle-xe image automatically creates the testuser and TESTDB database

-- Switch to the TESTDB pluggable database
ALTER SESSION SET CONTAINER = TESTDB;

-- Create tables in the testuser schema
CREATE TABLE testuser.employees (
    id NUMBER(10) PRIMARY KEY,
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE,
    hire_date DATE DEFAULT SYSDATE,
    salary NUMBER(10,2),
    department_id NUMBER(10)
);

CREATE TABLE testuser.departments (
    id NUMBER(10) PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    location VARCHAR2(100),
    budget NUMBER(15,2)
);

-- Create sequences in testuser schema
CREATE SEQUENCE testuser.employees_seq START WITH 5 INCREMENT BY 1;
CREATE SEQUENCE testuser.departments_seq START WITH 4 INCREMENT BY 1;

-- Grant testuser access to their own sequences
GRANT SELECT, ALTER ON testuser.employees_seq TO testuser;
GRANT SELECT, ALTER ON testuser.departments_seq TO testuser;

-- Insert sample data
INSERT INTO testuser.departments (id, name, location, budget) VALUES 
    (1, 'Engineering', 'San Francisco', 5000000);
INSERT INTO testuser.departments (id, name, location, budget) VALUES 
    (2, 'Marketing', 'New York', 2000000);
INSERT INTO testuser.departments (id, name, location, budget) VALUES 
    (3, 'Sales', 'Chicago', 3000000);

INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES 
    (1, 'John', 'Doe', 'john.doe@company.com', 75000, 1);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES 
    (2, 'Jane', 'Smith', 'jane.smith@company.com', 85000, 1);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES 
    (3, 'Bob', 'Johnson', 'bob.johnson@company.com', 65000, 2);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES 
    (4, 'Alice', 'Brown', 'alice.brown@company.com', 70000, 3);

-- Create a view for testing in testuser schema
CREATE VIEW testuser.employee_details AS
SELECT 
    e.id,
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    e.hire_date,
    e.salary,
    d.name AS department_name,
    d.location
FROM testuser.employees e
JOIN testuser.departments d ON e.department_id = d.id;

-- Grant testuser access to their own objects
GRANT ALL ON testuser.employees TO testuser;
GRANT ALL ON testuser.departments TO testuser;
GRANT ALL ON testuser.employee_details TO testuser;

COMMIT;
