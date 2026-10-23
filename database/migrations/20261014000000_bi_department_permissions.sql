-- Tabla de permisos por departamento para el módulo BI
-- Mapea qué departamentos pueden ver qué tablas

CREATE TABLE IF NOT EXISTS bi_department_permission (
    id SERIAL PRIMARY KEY,
    id_department INT NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    visible BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_department, table_name),
    CONSTRAINT fk_bi_dept_perm_dept FOREIGN KEY (id_department)
        REFERENCES department(id_department) ON DELETE CASCADE
);

-- Comentario para documentación
COMMENT ON TABLE bi_department_permission IS
    'Define visibilidad de tablas por departamento en el módulo BI. Si no existe entrada, tabla no es visible.';

-- Datos iniciales: Por defecto todos los departamentos ven todas las tablas
-- (esto se puede refinar por proyecto)
INSERT INTO bi_department_permission (id_department, table_name, visible)
SELECT DISTINCT p.id_department, t.table_name, true
FROM permission p
CROSS JOIN (
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    AND table_name NOT LIKE 'alembic%'
    AND table_name NOT LIKE '%migration%'
) t
WHERE NOT EXISTS (
    SELECT 1 FROM bi_department_permission bdp
    WHERE bdp.id_department = p.id_department
    AND bdp.table_name = t.table_name
)
ON CONFLICT DO NOTHING;
