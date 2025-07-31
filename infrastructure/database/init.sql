-- Blood Bank Database Initialization Script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create blood bank database if not exists
-- (This is typically handled by docker-compose environment variables)

-- Create schemas
CREATE SCHEMA IF NOT EXISTS blood_bank;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set default search path
ALTER DATABASE blood_bank_db SET search_path TO blood_bank, public;

-- Create custom types for blood types
DO $$ BEGIN
    CREATE TYPE blood_type_enum AS ENUM (
        'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create custom types for gender
DO $$ BEGIN
    CREATE TYPE gender_enum AS ENUM ('MALE', 'FEMALE', 'OTHER');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create custom types for product status
DO $$ BEGIN
    CREATE TYPE product_status_enum AS ENUM (
        'AVAILABLE', 'RESERVED', 'EXPIRED', 'USED', 'QUARANTINE'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create audit trigger function
CREATE OR REPLACE FUNCTION blood_bank.audit_trigger()
RETURNS TRIGGER AS $audit_trigger$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (
            table_name, operation, old_values, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, TG_OP, row_to_json(OLD), current_user, now()
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (
            table_name, operation, old_values, new_values, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), current_user, now()
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (
            table_name, operation, new_values, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, TG_OP, row_to_json(NEW), current_user, now()
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$audit_trigger$ LANGUAGE plpgsql;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by TEXT DEFAULT current_user,
    changed_at TIMESTAMP DEFAULT now()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit.audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit.audit_log(changed_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit.audit_log(operation);

-- Create monitoring tables
CREATE TABLE IF NOT EXISTS monitoring.system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT now(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time 
ON monitoring.system_metrics(metric_name, recorded_at);

-- Create function to clean old audit logs (older than 1 year)
CREATE OR REPLACE FUNCTION audit.cleanup_old_logs()
RETURNS INTEGER AS $cleanup$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit.audit_log 
    WHERE changed_at < now() - INTERVAL '1 year';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO monitoring.system_metrics (metric_name, metric_value, metric_unit)
    VALUES ('audit_cleanup_deleted_records', deleted_count, 'records');
    
    RETURN deleted_count;
END;
$cleanup$ LANGUAGE plpgsql;

-- Create function to get blood inventory summary
CREATE OR REPLACE FUNCTION blood_bank.get_inventory_summary()
RETURNS TABLE (
    blood_type VARCHAR(5),
    available_count BIGINT,
    reserved_count BIGINT,
    expired_count BIGINT,
    total_volume NUMERIC
) AS $inventory_summary$
BEGIN
    RETURN QUERY
    SELECT 
        bp.blood_type::VARCHAR(5),
        COUNT(*) FILTER (WHERE bp.status = 'AVAILABLE') as available_count,
        COUNT(*) FILTER (WHERE bp.status = 'RESERVED') as reserved_count,
        COUNT(*) FILTER (WHERE bp.status = 'EXPIRED') as expired_count,
        SUM(bp.volume) as total_volume
    FROM blood_bank.blood_products bp
    GROUP BY bp.blood_type
    ORDER BY bp.blood_type;
END;
$inventory_summary$ LANGUAGE plpgsql;

-- Create function to get donation statistics
CREATE OR REPLACE FUNCTION blood_bank.get_donation_stats(
    start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    donation_date DATE,
    donation_count BIGINT,
    total_volume NUMERIC,
    unique_donors BIGINT
) AS $donation_stats$
BEGIN
    RETURN QUERY
    SELECT 
        d.donation_date::DATE,
        COUNT(*) as donation_count,
        SUM(d.volume_collected) as total_volume,
        COUNT(DISTINCT d.donor_id) as unique_donors
    FROM blood_bank.donations d
    WHERE d.donation_date::DATE BETWEEN start_date AND end_date
    GROUP BY d.donation_date::DATE
    ORDER BY d.donation_date::DATE;
END;
$donation_stats$ LANGUAGE plpgsql;

-- Create DHIS2 sync status table
CREATE TABLE IF NOT EXISTS blood_bank.dhis2_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    last_sync_date TIMESTAMP,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_synced INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_dhis2_sync_status_type ON blood_bank.dhis2_sync_status(sync_type);
CREATE INDEX IF NOT EXISTS idx_dhis2_sync_status_date ON blood_bank.dhis2_sync_status(last_sync_date);

-- Insert initial DHIS2 sync status records
INSERT INTO blood_bank.dhis2_sync_status (sync_type, status) 
VALUES 
    ('donations', 'idle'),
    ('inventory', 'idle'),
    ('donors', 'idle')
ON CONFLICT DO NOTHING;

-- Create trigger to update updated_at column
CREATE OR REPLACE FUNCTION blood_bank.update_updated_at_column()
RETURNS TRIGGER AS $update_timestamp$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$update_timestamp$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA blood_bank TO PUBLIC;
GRANT USAGE ON SCHEMA audit TO PUBLIC;
GRANT USAGE ON SCHEMA monitoring TO PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA blood_bank TO PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA monitoring TO PUBLIC;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA blood_bank TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA monitoring TO PUBLIC;

-- Create a view for blood bank dashboard
CREATE OR REPLACE VIEW blood_bank.dashboard_summary AS
SELECT 
    (SELECT COUNT(*) FROM blood_bank.donors) as total_donors,
    (SELECT COUNT(*) FROM blood_bank.donations WHERE donation_date >= CURRENT_DATE - INTERVAL '30 days') as donations_last_30_days,
    (SELECT COUNT(*) FROM blood_bank.blood_products WHERE status = 'AVAILABLE') as available_products,
    (SELECT COUNT(*) FROM blood_bank.blood_products WHERE status = 'EXPIRED') as expired_products,
    (SELECT COUNT(*) FROM blood_bank.blood_products WHERE expiry_date <= CURRENT_DATE + INTERVAL '7 days' AND status = 'AVAILABLE') as expiring_soon,
    CURRENT_TIMESTAMP as last_updated;

-- Add comments for documentation
COMMENT ON DATABASE blood_bank_db IS 'Blood Bank Management System Database';
COMMENT ON SCHEMA blood_bank IS 'Main schema for blood bank operations';
COMMENT ON SCHEMA audit IS 'Audit trail for all data changes';
COMMENT ON SCHEMA monitoring IS 'System monitoring and metrics';

COMMENT ON FUNCTION blood_bank.get_inventory_summary() IS 'Returns current inventory summary by blood type';
COMMENT ON FUNCTION blood_bank.get_donation_stats(DATE, DATE) IS 'Returns donation statistics for a date range';
COMMENT ON FUNCTION audit.cleanup_old_logs() IS 'Removes audit logs older than 1 year';

-- Vacuum and analyze for optimal performance
VACUUM ANALYZE;