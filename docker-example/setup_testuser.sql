-- Create testuser in the testdb database
CREATE USER testuser IDENTIFIED BY "TestUser123!";
GRANT CONNECT, RESOURCE, DBA TO testuser;
ALTER USER testuser DEFAULT TABLESPACE USERS;
ALTER USER testuser QUOTA UNLIMITED ON USERS;

-- Create sample tables as testuser
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

-- Insert sample data
INSERT INTO testuser.departments (id, name, location, budget) VALUES (1, 'Engineering', 'San Francisco', 5000000);
INSERT INTO testuser.departments (id, name, location, budget) VALUES (2, 'Marketing', 'New York', 2000000);
INSERT INTO testuser.departments (id, name, location, budget) VALUES (3, 'Sales', 'Chicago', 3000000);

INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES (1, 'John', 'Doe', 'john.doe@company.com', 75000, 1);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES (2, 'Jane', 'Smith', 'jane.smith@company.com', 85000, 1);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES (3, 'Bob', 'Johnson', 'bob.johnson@company.com', 65000, 2);
INSERT INTO testuser.employees (id, first_name, last_name, email, salary, department_id) VALUES (4, 'Alice', 'Brown', 'alice.brown@company.com', 70000, 3);

-- Create a view for testing
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

COMMIT;

SELECT 'Setup completed successfully!' as status FROM dual;
