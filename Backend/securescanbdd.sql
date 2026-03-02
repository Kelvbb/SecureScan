-- ==========================================
-- SECURESCAN DATABASE SCHEMA
-- Version avec USERS
-- ==========================================

-- ==========================================
-- 1. Create Database (optional)
-- ==========================================
-- Uncomment if needed
-- CREATE DATABASE securescan;
-- \c securescan;

-- ==========================================
-- 2. Extensions
-- ==========================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 3. USERS
-- ==========================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);

-- ==========================================
-- 4. SCANS
-- ==========================================

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    repository_url TEXT,
    upload_path TEXT,
    language VARCHAR(100),
    
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_scans_user ON scans(user_id);
CREATE INDEX idx_scans_status ON scans(status);

-- ==========================================
-- 5. SECURITY TOOLS
-- ==========================================

CREATE TABLE security_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    cli_command TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- ==========================================
-- 6. TOOL EXECUTIONS
-- ==========================================

CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES security_tools(id),
    
    status VARCHAR(50) NOT NULL,
    raw_output JSONB,
    
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_tool_exec_scan ON tool_executions(scan_id);

-- ==========================================
-- 7. OWASP CATEGORIES
-- ==========================================

CREATE TABLE owasp_categories (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- Initial OWASP Data
INSERT INTO owasp_categories (id, name) VALUES
('A01', 'Broken Access Control'),
('A02', 'Security Misconfiguration'),
('A03', 'Software Supply Chain Failures'),
('A04', 'Cryptographic Failures'),
('A05', 'Injection'),
('A06', 'Insecure Design'),
('A07', 'Authentication Failures'),
('A08', 'Software/Data Integrity Failures'),
('A09', 'Logging and Alerting Failures'),
('A10', 'Mishandling of Exceptional Conditions');

-- ==========================================
-- 8. VULNERABILITIES
-- ==========================================

CREATE TABLE vulnerabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    tool_execution_id UUID REFERENCES tool_executions(id) ON DELETE SET NULL,
    
    title TEXT NOT NULL,
    description TEXT,
    
    file_path TEXT,
    line_start INT,
    line_end INT,
    
    severity VARCHAR(20) NOT NULL,
    confidence VARCHAR(20),
    
    cve_id VARCHAR(50),
    cwe_id VARCHAR(50),
    
    owasp_category_id VARCHAR(10) REFERENCES owasp_categories(id),
    
    status VARCHAR(50) DEFAULT 'open',
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_vuln_scan ON vulnerabilities(scan_id);
CREATE INDEX idx_vuln_severity ON vulnerabilities(severity);
CREATE INDEX idx_vuln_open ON vulnerabilities(scan_id)
WHERE status = 'open';

-- ==========================================
-- 9. SUGGESTED FIXES
-- ==========================================

CREATE TABLE suggested_fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    vulnerability_id UUID REFERENCES vulnerabilities(id) ON DELETE CASCADE,
    
    fix_type VARCHAR(100),
    description TEXT,
    patch_diff TEXT,
    
    auto_applicable BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT now()
);

-- ==========================================
-- 10. SCAN METRICS
-- ==========================================

CREATE TABLE scan_metrics (
    scan_id UUID PRIMARY KEY REFERENCES scans(id) ON DELETE CASCADE,
    
    total_vulnerabilities INT DEFAULT 0,
    critical_count INT DEFAULT 0,
    high_count INT DEFAULT 0,
    medium_count INT DEFAULT 0,
    low_count INT DEFAULT 0,
    
    score_global NUMERIC(5,2),
    
    created_at TIMESTAMP DEFAULT now()
);

-- ==========================================
-- END OF SCHEMA
-- ==========================================