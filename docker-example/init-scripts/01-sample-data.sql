-- Sample data setup for Oracle MCP Server testing

-- Create some sample tables for testing
CREATE TABLE employees (
    id NUMBER(10) PRIMARY KEY,
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE,
    hire_date DATE DEFAULT SYSDATE,
    salary NUMBER(10,2),
    department_id NUMBER(10)
);

CREATE TABLE departments (
    id NUMBER(10) PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    location VARCHAR2(100),
    budget NUMBER(15,2)
);

-- Create sequences for auto-incrementing IDs
CREATE SEQUENCE employees_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE departments_seq START WITH 1 INCREMENT BY 1;

-- Create triggers for auto-incrementing IDs
CREATE OR REPLACE TRIGGER employees_trigger
    BEFORE INSERT ON employees
    FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        :NEW.id := employees_seq.NEXTVAL;
    END IF;
END;
/

CREATE OR REPLACE TRIGGER departments_trigger
    BEFORE INSERT ON departments
    FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        :NEW.id := departments_seq.NEXTVAL;
    END IF;
END;
/

-- Insert sample data
INSERT INTO departments (name, location, budget) VALUES 
    ('Engineering', 'San Francisco', 5000000);
INSERT INTO departments (name, location, budget) VALUES 
    ('Marketing', 'New York', 2000000);
INSERT INTO departments (name, location, budget) VALUES 
    ('Sales', 'Chicago', 3000000);

INSERT INTO employees (first_name, last_name, email, salary, department_id) VALUES 
    ('John', 'Doe', 'john.doe@company.com', 75000, 1);
INSERT INTO employees (first_name, last_name, email, salary, department_id) VALUES 
    ('Jane', 'Smith', 'jane.smith@company.com', 85000, 1);
INSERT INTO employees (first_name, last_name, email, salary, department_id) VALUES 
    ('Bob', 'Johnson', 'bob.johnson@company.com', 65000, 2);
INSERT INTO employees (first_name, last_name, email, salary, department_id) VALUES 
    ('Alice', 'Brown', 'alice.brown@company.com', 70000, 3);

-- Create a view for testing
CREATE VIEW employee_details AS
SELECT 
    e.id,
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    e.hire_date,
    e.salary,
    d.name AS department_name,
    d.location
FROM employees e
JOIN departments d ON e.department_id = d.id;

-- Create a simple stored procedure for testing
CREATE OR REPLACE PROCEDURE get_employee_count(p_dept_id IN NUMBER, p_count OUT NUMBER)
IS
BEGIN
    SELECT COUNT(*) INTO p_count
    FROM employees
    WHERE department_id = p_dept_id;
END;
/

COMMIT;
