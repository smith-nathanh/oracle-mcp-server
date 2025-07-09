-- Oracle Database Sample Queries for MCP Server Testing
-- These queries demonstrate various Oracle database exploration patterns
-- that work well with GitHub Copilot Agent mode

-- =============================================================================
-- SCHEMA EXPLORATION QUERIES
-- =============================================================================

-- List all tables accessible to current user
SELECT 
    owner,
    table_name,
    num_rows,
    last_analyzed,
    tablespace_name
FROM all_tables 
WHERE owner NOT IN ('SYS', 'SYSTEM', 'CTXSYS', 'MDSYS', 'OLAPSYS', 'ORDSYS', 'OUTLN', 'WMSYS')
ORDER BY owner, table_name;

-- Get table column information
SELECT 
    column_name,
    data_type,
    data_length,
    data_precision,
    data_scale,
    nullable,
    data_default
FROM all_tab_columns 
WHERE table_name = 'EMPLOYEES'  -- Replace with your table name
ORDER BY column_id;

-- Find tables with specific column names (useful for data discovery)
SELECT DISTINCT 
    owner,
    table_name
FROM all_tab_columns 
WHERE column_name LIKE '%EMAIL%'
   OR column_name LIKE '%PHONE%'
   OR column_name LIKE '%ADDRESS%'
ORDER BY owner, table_name;

-- =============================================================================
-- DATA EXPLORATION QUERIES (HR SCHEMA EXAMPLES)
-- =============================================================================

-- Basic employee data exploration
SELECT 
    employee_id,
    first_name,
    last_name,
    email,
    hire_date,
    job_id,
    salary,
    department_id
FROM employees 
WHERE ROWNUM <= 10;

-- Department summary with employee counts
SELECT 
    d.department_name,
    COUNT(e.employee_id) as employee_count,
    ROUND(AVG(e.salary), 2) as avg_salary,
    MIN(e.salary) as min_salary,
    MAX(e.salary) as max_salary
FROM departments d
LEFT JOIN employees e ON d.department_id = e.department_id
GROUP BY d.department_id, d.department_name
ORDER BY employee_count DESC;

-- Employee hierarchy (if manager_id exists)
SELECT 
    LEVEL,
    LPAD(' ', 2 * (LEVEL - 1)) || first_name || ' ' || last_name AS employee_hierarchy,
    job_id,
    salary
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR employee_id = manager_id
ORDER SIBLINGS BY last_name;

-- =============================================================================
-- DATA QUALITY CHECKS
-- =============================================================================

-- Find duplicate records (adjust columns as needed)
SELECT 
    first_name,
    last_name,
    email,
    COUNT(*) as duplicate_count
FROM employees
GROUP BY first_name, last_name, email
HAVING COUNT(*) > 1;

-- Check for NULL values in critical columns
SELECT 
    'employees' as table_name,
    'email' as column_name,
    COUNT(*) as null_count
FROM employees 
WHERE email IS NULL
UNION ALL
SELECT 
    'employees',
    'hire_date',
    COUNT(*)
FROM employees 
WHERE hire_date IS NULL
UNION ALL
SELECT 
    'employees',
    'department_id',
    COUNT(*)
FROM employees 
WHERE department_id IS NULL;

-- =============================================================================
-- PERFORMANCE ANALYSIS QUERIES
-- =============================================================================

-- Table sizes and row counts
SELECT 
    owner,
    table_name,
    num_rows,
    ROUND(num_rows * avg_row_len / 1024 / 1024, 2) as size_mb,
    last_analyzed
FROM all_tables 
WHERE owner = USER  -- Current schema
  AND num_rows > 0
ORDER BY num_rows DESC;

-- Index information for a table
SELECT 
    index_name,
    index_type,
    uniqueness,
    status,
    num_rows,
    last_analyzed
FROM all_indexes 
WHERE table_name = 'EMPLOYEES'  -- Replace with your table
ORDER BY index_name;

-- =============================================================================
-- DATE AND TIME ANALYSIS
-- =============================================================================

-- Date range analysis
SELECT 
    'hire_date' as date_column,
    MIN(hire_date) as earliest_date,
    MAX(hire_date) as latest_date,
    ROUND(MAX(hire_date) - MIN(hire_date)) as date_range_days
FROM employees;

-- Monthly hiring trends
SELECT 
    TO_CHAR(hire_date, 'YYYY-MM') as hire_month,
    COUNT(*) as hires_count
FROM employees
WHERE hire_date >= ADD_MONTHS(SYSDATE, -24)  -- Last 24 months
GROUP BY TO_CHAR(hire_date, 'YYYY-MM')
ORDER BY hire_month;

-- =============================================================================
-- BUSINESS INTELLIGENCE QUERIES
-- =============================================================================

-- Salary distribution by department
SELECT 
    d.department_name,
    CASE 
        WHEN e.salary < 5000 THEN 'Low (< 5K)'
        WHEN e.salary BETWEEN 5000 AND 10000 THEN 'Medium (5K-10K)'
        WHEN e.salary > 10000 THEN 'High (> 10K)'
    END as salary_range,
    COUNT(*) as employee_count
FROM employees e
JOIN departments d ON e.department_id = d.department_id
GROUP BY d.department_name,
    CASE 
        WHEN e.salary < 5000 THEN 'Low (< 5K)'
        WHEN e.salary BETWEEN 5000 AND 10000 THEN 'Medium (5K-10K)'
        WHEN e.salary > 10000 THEN 'High (> 10K)'
    END
ORDER BY d.department_name, salary_range;

-- Top performers by department (top 20% by salary)
SELECT 
    department_name,
    first_name || ' ' || last_name as employee_name,
    salary,
    RANK() OVER (PARTITION BY d.department_id ORDER BY e.salary DESC) as salary_rank
FROM employees e
JOIN departments d ON e.department_id = d.department_id
WHERE e.salary >= (
    SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY salary)
    FROM employees e2 
    WHERE e2.department_id = e.department_id
)
ORDER BY department_name, salary DESC;

-- =============================================================================
-- GITHUB COPILOT AGENT MODE TEST QUERIES
-- =============================================================================

-- Simple aggregation that agents can build upon
SELECT 
    COUNT(*) as total_employees,
    COUNT(DISTINCT department_id) as total_departments,
    ROUND(AVG(salary), 2) as average_salary
FROM employees;

-- Data for CSV export (limited rows for testing)
SELECT 
    e.employee_id,
    e.first_name,
    e.last_name,
    e.email,
    e.salary,
    d.department_name,
    j.job_title
FROM employees e
LEFT JOIN departments d ON e.department_id = d.department_id
LEFT JOIN jobs j ON e.job_id = j.job_id
WHERE ROWNUM <= 50
ORDER BY e.employee_id;

-- =============================================================================
-- UTILITY QUERIES FOR MCP SERVER TESTING
-- =============================================================================

-- Test EXPLAIN PLAN functionality
EXPLAIN PLAN FOR
SELECT e.first_name, e.last_name, d.department_name
FROM employees e
JOIN departments d ON e.department_id = d.department_id
WHERE e.salary > 10000;

-- Simple queries for testing various data types
SELECT 
    SYSDATE as current_timestamp,
    USER as current_user,
    'Test String' as text_column,
    12345 as number_column,
    NULL as null_column
FROM dual;

-- =============================================================================
-- NOTES FOR GITHUB COPILOT USAGE
-- =============================================================================

/*
These queries are designed to work with the Oracle MCP Server's safety controls:
- All queries are SELECT statements (no modifications)
- ROWNUM limits are used to prevent runaway queries
- Queries focus on common data exploration patterns
- Examples include aggregations, joins, and analytical functions

To use with GitHub Copilot Agent mode:
1. Ask the agent to "execute sample query for employee analysis"
2. Request "show me the table structure for employees"
3. Ask for "data quality check on the employees table"
4. Request "export top 50 employees with department info as CSV"

Example Copilot prompts:
- "Show me the database schema overview"
- "Analyze employee salary distribution by department"
- "Find any data quality issues in the employees table"
- "Generate a report on hiring trends over the last 2 years"
*/