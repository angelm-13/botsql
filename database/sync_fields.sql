-- TYAKXA field metadata sync
-- Requires table "field" if your ERP stores dynamic field metadata.
BEGIN;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'date_born', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'date_start', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'email', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test email', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'first_name', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test first_name', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'id_permission', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'permission', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'full_name', 'varchar',
  TRUE, NULL, '150',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test first_name', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'id_proyect', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'proyect', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'last_name_father', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test last_name_father', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'last_name_mother', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test last_name_mother', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'national_id', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test national_id', TRUE, TRUE,
  'curp', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'password', 'varchar',
  FALSE, NULL, '256',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test password', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'principal_phone', 'varchar',
  FALSE, NULL, '15',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test principal_phone', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'secundary_phone', 'varchar',
  FALSE, NULL, '15',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test secundary_phone', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'ssn', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test ssn', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'supervisor', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'base_salary', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'hire_date', 'date',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'id_status', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'status', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'tax_id', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test tax_id', FALSE, TRUE,
  'rfc', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'title', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test title', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'user_type', 'enum',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'admin', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'username', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'supervisor', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'puesto', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user', 'accepts_marketing', 'boolean',
  FALSE, NULL, NULL,
  FALSE, '0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0', FALSE, FALSE,
  'Indica si el comprador web acepta comunicaciones de marketing.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'id_user_mfa', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'secret', 'VARBINARY',
  FALSE, NULL, '255',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'secret_iv', 'VARBINARY',
  FALSE, NULL, '32',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'enabled', 'boolean',
  FALSE, NULL, '1',
  TRUE, 'FALSE', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'failed_attempts', 'int',
  FALSE, NULL, '11',
  TRUE, '0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'locked_until', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'last_used_at', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'backup_codes', 'json',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '{}', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'created_at', 'datetime',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '2026-01-01 00:00:00', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'user_mfa', 'updated_at', 'datetime',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '2026-01-01 00:00:00', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'id_payroll_period', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'period_start', 'date',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'period_end', 'date',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'payment_date', 'date',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'id_status', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'status', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_period', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'id_payroll_detail', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'id_payroll_period', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'payroll_period', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'gross_salary', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'total_earnings', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'total_deductions', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'net_pay', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_detail', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'id_payroll_concept', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'payroll_code', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test title', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'payroll_concept_description', 'varchar',
  TRUE, NULL, '150',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test title', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'type', 'enum',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'earning', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'is_taxable', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'is_imss', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_concept', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'id_payroll_movement', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'id_payroll_detail', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'payroll_detail', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'id_payroll_concept', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'payroll_concept', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'amount', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'payroll_movement', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'id_customer_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'postal_code', 'varchar',
  FALSE, NULL, '10',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '00000', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'name', 'varchar',
  TRUE, NULL, '150',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test razon_social', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'title', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test title', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'contact_name', 'varchar',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test contact_name', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'phone', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test phone', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'email', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'contacto@example.com', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'web_site', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test web_site', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'street', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test street', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'number_ext', 'varchar',
  FALSE, NULL, '5',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'number_int', 'varchar',
  FALSE, NULL, '5',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'neighborhood', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test neighborhood', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'city', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test city', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'geographic_state', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'fiscal_type', 'varchar',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test fiscal_type', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'last_fiscal_certification_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'tax_id', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test tax_id', FALSE, TRUE,
  'RFC', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'type', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'client', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'customer_supplier', 'path_logo', 'varchar',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'uploads/customer_suppliers/logos/logo.png', FALSE, FALSE,
  'Issue 9 cotizaciones', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'id_proyect', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'id_customer_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'customer_supplier', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'leader', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'proyect_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'title', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test title', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'proyect_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'proyect', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'id_bank', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'bank_name', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test bank_name', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'id_bank_account', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'id_bank', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'bank', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'bank_account_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'branch', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test branch', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'type', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test type', FALSE, TRUE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'ordinary_interest', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'moratorium_interest', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'anuality', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'reimbursement', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'bank_account', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_invoice', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'date_emision', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'date_expiration', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'subtotal', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'tax', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'total', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'invoice_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'payment_method', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test payment_method', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'note', 'varchar',
  FALSE, NULL, '300',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test notes', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_customer_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'customer_supplier', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'fiscal_reference', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test fiscal_reference', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'serie_csd', 'varchar',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test serie_csd', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'internationalization', 'enum',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'exported', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'currency', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test currency', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'type_exchange_rate', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'tax_certification_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  'customer_supplier', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'fiscal_certify_serie', 'varchar',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test fiscal_certify_serie', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'certification_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'cfdi_code', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test cfdi_code', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'sat_code', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test sat_code', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'sat_certification_code', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test sat_certification_code', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_status', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'status', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'nombre_emisor', 'varchar(150)',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'lugar_expedicion', 'varchar',
  FALSE, NULL, '120',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'tipo_de_comprobante', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'factura', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'rfc_receptor', 'varchar(20)',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'nombre_receptor', 'varchar(150)',
  FALSE, NULL, '150',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'regimen_fiscal_receptor', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Empresa Moral', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'domicilio_fiscal_receptor', 'varchar',
  FALSE, NULL, '250',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Paseos de Jerez 541, Las arboledas', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_proveedor_de_sello', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'folio_fiscal', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'exportacion', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'folio', 'varchar(30)',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'no_certificado_sat', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'sello_sat', 'varchar(500)',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'sello_certificacion_sat', 'varchar(500)',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'no_certificado', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'descuento', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0.00', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'metodo_pago', 'varchar(50)',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'condiciones_pago', 'varchar(100)',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_issuer_customer_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'customer_supplier', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Empresa emisora de la cotizacion. Reutiliza customer_supplier para evitar crear entidad duplicada de empresa.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'id_proyect', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, TRUE,
  'proyect', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Proyecto relacionado opcional para la cotizacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'apply_tax', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Control para indicar si la cotizacion aplica IVA.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'tax_rate', 'decimal',
  FALSE, NULL, '5,2',
  FALSE, '16.00', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '16.00', FALSE, FALSE,
  'Porcentaje de IVA aplicable a la cotizacion. Valor esperado por defecto: 16.00.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice', 'commercial_terms', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Vigencia sujeta a disponibilidad.', FALSE, FALSE,
  'Condiciones comerciales de la cotizacion para mostrarse en PDF.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_invoice_material_service', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_invoice', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'invoice', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_material', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, TRUE,
  'material', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_service', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, TRUE,
  'service', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'invoice_material_service_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'max_requirement_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'is_directly_related_to_product_service_creation', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_authorized', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_status', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'status', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_buyer', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_customer_supplier', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'customer_supplier', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'gross_price', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'quantity', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_product', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, TRUE,
  'product', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Producto seleccionado para la partida cuando line_type = product.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'line_type', 'enum',
  FALSE, NULL, '50',
  TRUE, 'custom', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'custom', FALSE, FALSE,
  'Tipo de partida: producto, servicio o concepto personalizado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'tax_applicable', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Indica si la partida considera IVA.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'line_tax', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, '0.00', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0.00', FALSE, FALSE,
  'IVA calculado para la partida, si aplica.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'line_total', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, '0.00', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0.00', FALSE, FALSE,
  'Subtotal de partida calculado como gross_price * quantity.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'id_unit', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, TRUE,
  'unit', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Issue 9 cotizaciones', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'authorization_status', 'enum',
  FALSE, NULL, '50',
  TRUE, 'pending', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'pending', TRUE, FALSE,
  'Estado de autorizacion funcional de la partida: pending, authorized o rejected.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'authorization_note', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Pendiente de revision.', FALSE, FALSE,
  'Nota de autorizacion o rechazo de la partida.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'invoice_material_service', 'authorization_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha en que se autorizo o rechazo la partida.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'id_product_family', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'product_family_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'type', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'tool', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_family', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'id_incident_type', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'incident_type_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_type', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'id_incident', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'incident_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'id_incident_type', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'incident_type', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'note', 'varchar',
  FALSE, NULL, '300',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test note', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'incident_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'close_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident', 'id_lider', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'id_incident_detail', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'id_incident_type', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'incident_type', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'incident_detail_name', 'varchar',
  TRUE, NULL, '50',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'incident_detail_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'incident_detail', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'id_brand', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'brand_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'brand', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'id_unit', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'unit_code', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'unit_name', 'varchar',
  TRUE, NULL, '100',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'unit_category', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'is_active', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'symbol', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'measurement_system', 'enum',
  FALSE, NULL, NULL,
  TRUE, 'metric', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'metric', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'unit', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'id_material', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'material_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'id_unit', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'unit', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'id_brand', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'brand', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'id_product_family', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'product_family', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'id_material_component', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'id_material', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'material', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'id_component', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'material', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'relation', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'id_unit', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'unit', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'material_component', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'id_movement', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'id_fiscal_account', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'fiscal_account', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'type', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'income', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'amount', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'currency', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'mxn', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'type_exchange_rate', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'movement', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'id_location_type', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'location_type_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location_type', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'id_location', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'id_location_type', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'location_type', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'location_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'id_location_reference', 'int',
  FALSE, NULL, '11',
  FALSE, '1', FALSE,
  'location', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'location', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_product', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_invoice', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'invoice', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_location', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'location', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_material', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'material', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'gross_price', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'color', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test color', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'is_directly_related_to_product_service', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'product_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'path_imagen', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test path_imagen', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'product_code', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test code', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'note', 'varchar',
  FALSE, NULL, '300',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test note', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'descripcion', 'varchar(250)',
  FALSE, NULL, '250',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'cantidad', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_material', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_marca', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product', 'id_familia', 'int(11)',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'id_nm_incident_product', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'id_incident', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'incident', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'id_product', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'product', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'note', 'varchar',
  FALSE, NULL, '300',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test note', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'quantity', 'int',
  FALSE, NULL, '10',
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'close_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_incident_product', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'id_task', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'task_code', 'varchar',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'C1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'start_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'duration', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'type', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'business', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'owner', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'analyst', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'dependency', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  'task', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'leader', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'validation', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'task_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'estimated_effort', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test estimated_effort', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'task_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'fase', 'varchar',
  FALSE, NULL, '100',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test fase', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'priority', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test priority', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'title', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test titulo', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'id_proyect', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'proyect', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'id_task_note', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'id_task', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'task', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'task_note_description', 'varchar',
  TRUE, NULL, '600',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_note', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'id_ticket', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'ticket_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'ticket_status', 'varchar',
  FALSE, NULL, '20',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test state', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'note', 'varchar',
  FALSE, NULL, '300',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test respuesta', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'ticket', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'id_fiscal_account', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'fiscal_account_description', 'varchar',
  TRUE, NULL, '200',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'balance', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'id_fiscal_account_reference', 'int',
  FALSE, NULL, '11',
  FALSE, '1', FALSE,
  'fiscal_account', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_account', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'id_fiscal_stamp', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'concept', 'varchar',
  FALSE, NULL, '50',
  TRUE, 'concept', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test concept', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'reviewed_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'authorized_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'auxiliar', 'varchar',
  FALSE, NULL, '50',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test auxiliar', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'num_policy', 'varchar',
  FALSE, NULL, '20',
  TRUE, 'num_policy', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test num_policy', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_stamp', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'id_fiscal_record', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'fiscal_record_name', 'varchar',
  TRUE, NULL, '150',
  TRUE, 'name', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test name', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'id_fiscal_account', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'fiscal_account', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'amount', 'decimal',
  FALSE, NULL, '10,2',
  TRUE, '0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'type', 'varchar',
  FALSE, NULL, '30',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test type', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'id_fiscal_stamp', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'fiscal_stamp', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'fiscal_record', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'id_service', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'service_description', 'varchar',
  TRUE, NULL, '500',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'average_time_cost', 'decimal',
  FALSE, NULL, '10,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '123.45', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'id_brand', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'brand', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'service', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'id_status', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'status_description', 'varchar',
  TRUE, NULL, '150',
  TRUE, 'name', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test name', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'category', 'varchar',
  FALSE, NULL, '150',
  TRUE, 'name', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test name', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'is_terminal', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'sort_order', 'enum',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'mxn', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'status', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'id_theme', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'tenant_id', 'int',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'primary_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#0D47A1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'secondary_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#1565C0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'background_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#F5F6FA', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'text_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#212121', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'highlight_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#1E88E5', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'success_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#2E7D32', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'theme', 'error_color', 'varchar',
  FALSE, NULL, '10',
  TRUE, '#C62828', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#0D47A1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'id_department', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'department_description', 'varchar',
  TRUE, NULL, '100',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'department', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'id_subdepartment', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'subdepartment_description', 'varchar',
  TRUE, NULL, '100',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'id_department', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'department', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'subdepartment', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'id_level', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'level_description', 'varchar',
  TRUE, NULL, '100',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'level', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'id_field', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'table_name', 'varchar',
  TRUE, NULL, '50',
  TRUE, 'user', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'field', 'field_name', 'varchar',
  TRUE, NULL, '50',
  TRUE, 'id_user', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'id_user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'id_permission', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'authorized_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'permission_description', 'varchar',
  TRUE, NULL, '250',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test permission description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'id_department', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'department', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'id_subdepartment', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'subdepartment', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'permission', 'id_level', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'level', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'id_nm_field_permission', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'id_field', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'field', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'id_permission', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'permission', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'control_type', 'enum',
  FALSE, NULL, '11',
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_field_permission', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'id_event_log', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'table_name', 'varchar',
  TRUE, NULL, '50',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'user', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'field_name', 'varchar',
  TRUE, NULL, '50',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'user_id', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'action', 'enum',
  FALSE, NULL, NULL,
  TRUE, 'create', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'create', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'before_value', 'json',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'after_value', 'json',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'event_log', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'id_task_type', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'task_type_description', 'varchar',
  TRUE, NULL, '250',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test permission description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'task_type_scope', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test permission description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'task_type_limit', 'varchar',
  FALSE, NULL, '500',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test permission description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'task_type', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'id_template', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'template_description', 'varchar',
  TRUE, NULL, '250',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'test permission description', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'template', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'id_nm_template_task', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'id_task', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'task', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'id_template', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'template', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_template_task', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'id_survey_question', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'question', 'varchar',
  TRUE, NULL, '300',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'question_type', 'enum',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'single_option', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'owner', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_question', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'id_survey_multiple_answer', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'id_survey_question', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'survey_question', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'survey_answer_description', 'varchar',
  TRUE, NULL, '300',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'score', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'survey_multiple_answer', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'id_nm_survey_user', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'id_survey_question', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'survey_question', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'id_survey_multiple_answer', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'survey_multiple_answer', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'nm_survey_user_description', 'varchar',
  TRUE, NULL, '300',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'score', 'int',
  FALSE, NULL, '11',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'status', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'status', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'nm_survey_user', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'id_entity_permission', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'id_permission', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'permission', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'entity_name', 'varchar',
  TRUE, NULL, '120',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'bank', TRUE, FALSE,
  'Entidad o modulo definido en entities.csv', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'control_type', 'enum',
  FALSE, NULL, '11',
  TRUE, '15', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '15', FALSE, FALSE,
  'Bitmask CRUD: create=1, read=2, update=4, delete=8, full=15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'entity_permission', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'id_inventory_status', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  'Identificador del estado de inventario.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'inventory_status_code', 'varchar',
  TRUE, NULL, '50',
  TRUE, 'ENTRADA', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'ENTRADA', TRUE, FALSE,
  'Codigo estable del estado para guardar en product.product_status sin migrar todavia a FK.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'inventory_status_description', 'varchar',
  TRUE, NULL, '120',
  TRUE, 'Entrada', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Entrada', TRUE, FALSE,
  'Nombre visible del estado de inventario.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'color', 'varchar',
  FALSE, NULL, '20',
  TRUE, '#22c55e', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '#22c55e', FALSE, FALSE,
  'Color visual administrable para tarjetas Kanban y listados.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'entity_scope', 'varchar',
  FALSE, NULL, '80',
  TRUE, 'product', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'product', TRUE, FALSE,
  'Entidad donde aplica el estado, por ejemplo product o incident.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'flow_scope', 'varchar',
  FALSE, NULL, '80',
  TRUE, 'inventory', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'inventory', TRUE, FALSE,
  'Flujo o proceso donde aplica el estado, por ejemplo inventory, quality, production o process.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'id_department', 'int',
  FALSE, NULL, '11',
  TRUE, '4', TRUE,
  'department', NULL,
  FALSE, FALSE,
  '4', TRUE, FALSE,
  'Departamento propietario del flujo del estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'id_subdepartment', 'int',
  FALSE, NULL, '11',
  FALSE, '4', TRUE,
  'subdepartment', NULL,
  FALSE, FALSE,
  '4', TRUE, FALSE,
  'Subdepartamento propietario opcional del flujo del estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'id_minimum_level', 'int',
  FALSE, NULL, '11',
  TRUE, '2', TRUE,
  'level', NULL,
  FALSE, FALSE,
  '2', TRUE, FALSE,
  'Nivel minimo requerido para administrar este estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'is_active', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Indica si el estado aparece en listas operativas.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'is_terminal', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0', FALSE, FALSE,
  'Indica si el estado cierra el flujo.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'visible_to_other_departments', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '0', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '0', TRUE, FALSE,
  'Permite listar el estado fuera de su departamento propietario cuando el flujo lo autorice.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'sort_order', 'int',
  FALSE, NULL, '11',
  TRUE, '100', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '100', FALSE, FALSE,
  'Orden visual del estado en selectores y tablas.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Usuario que creo el estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de creacion del estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de ultima actualizacion del estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'inventory_status', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de baja logica del estado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'id_product_sale_config', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  'Identificador de configuracion publica de venta por producto.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'id_product', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'product', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Producto interno asociado a la configuracion publica. Relacion 1:1 administrada por backend.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'margin_percent', 'decimal',
  FALSE, NULL, '5,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '30.00', FALSE, FALSE,
  'Margen porcentual sobre gross_price cuando no hay precio manual.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'manual_price', 'decimal',
  FALSE, NULL, '12,2',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '100.00', FALSE, FALSE,
  'Precio manual antes de IVA; si existe anula el calculo por margen.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'id_inventory_status', 'int',
  FALSE, NULL, '11',
  TRUE, '1001', TRUE,
  'inventory_status', NULL,
  FALSE, FALSE,
  '1001', TRUE, FALSE,
  'Estado de publicacion web tomado de inventory_status con flow_scope web_catalog.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'is_active', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Permite desactivar rapidamente la configuracion publica sin borrar datos.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Usuario que creo la configuracion publica.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de creacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de ultima actualizacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'product_sale_config', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de baja logica.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'id_public_api_key', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  'Identificador de API Key publica para consumir catalogo web.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'label', 'varchar',
  TRUE, NULL, '120',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'Web produccion', FALSE, FALSE,
  'Nombre legible de la API Key.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'key_hash', 'varchar',
  FALSE, NULL, '255',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'disabled_seed_key_hash', FALSE, FALSE,
  'Hash bcrypt del valor de la API Key. El valor en claro solo se muestra al crearla.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'key_prefix', 'varchar',
  FALSE, NULL, '12',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'disabled', FALSE, FALSE,
  'Primeros caracteres visibles para identificar la API Key sin exponerla completa.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'allowed_domains', 'text',
  FALSE, NULL, '500',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '[]', FALSE, FALSE,
  'Dominios autorizados separados por coma o JSON para consumir la API publica.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'rate_limit_per_min', 'int',
  FALSE, NULL, '11',
  TRUE, '60', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '60', FALSE, FALSE,
  'Limite de requests por minuto para esta API Key.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'is_active', 'boolean',
  FALSE, NULL, NULL,
  TRUE, '1', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Indica si la API Key esta activa.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'last_used_at', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de ultimo uso de la API Key.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'created_by', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', FALSE, FALSE,
  'Usuario interno que creo la API Key.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'creation_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de creacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'last_update_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de ultima actualizacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'public_api_key', 'deletion_date', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', FALSE, FALSE,
  'Fecha de baja logica.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'id_password_reset_token', 'int',
  FALSE, NULL, '11',
  TRUE, NULL, FALSE,
  NULL, NULL,
  TRUE, TRUE,
  '1', FALSE, FALSE,
  'Identificador del token de recuperacion de contrasena.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'id_user', 'int',
  FALSE, NULL, '11',
  TRUE, '1', TRUE,
  'user', NULL,
  FALSE, FALSE,
  '1', TRUE, FALSE,
  'Comprador web asociado al token de recuperacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'token_hash', 'varchar',
  FALSE, NULL, '255',
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'disabled_token_hash', TRUE, FALSE,
  'Hash SHA-256 del token de recuperacion; el valor claro solo viaja por email.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'expires_at', 'datetime',
  FALSE, NULL, NULL,
  TRUE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', TRUE, FALSE,
  'Fecha y hora de expiracion del token.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'used_at', 'datetime',
  FALSE, NULL, NULL,
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  NULL, FALSE, FALSE,
  'Fecha y hora en que el token fue usado.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'requested_ip', 'varchar',
  FALSE, NULL, '45',
  FALSE, NULL, FALSE,
  NULL, NULL,
  FALSE, FALSE,
  '127.0.0.1', FALSE, FALSE,
  'IP desde la que se solicito la recuperacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

INSERT INTO "field" (
  table_name, field_name, data_type, is_representative, if_enum, size,
  not_null, default_value, is_foreign, foreign_table, foreign_att,
  auto_increment, is_primary, sample_data, is_index, encrypted, note,
  created_by, creation_date, last_update_date
) VALUES (
  'password_reset_token', 'created_at', 'datetime',
  FALSE, NULL, NULL,
  TRUE, 'datetime.now()', FALSE,
  NULL, NULL,
  FALSE, FALSE,
  'datetime.now()', TRUE, FALSE,
  'Fecha de creacion del token de recuperacion.', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (table_name, field_name) DO UPDATE SET
  data_type = EXCLUDED.data_type,
  is_representative = EXCLUDED.is_representative,
  if_enum = EXCLUDED.if_enum,
  size = EXCLUDED.size,
  not_null = EXCLUDED.not_null,
  default_value = EXCLUDED.default_value,
  is_foreign = EXCLUDED.is_foreign,
  foreign_table = EXCLUDED.foreign_table,
  foreign_att = EXCLUDED.foreign_att,
  auto_increment = EXCLUDED.auto_increment,
  is_primary = EXCLUDED.is_primary,
  sample_data = EXCLUDED.sample_data,
  is_index = EXCLUDED.is_index,
  encrypted = EXCLUDED.encrypted,
  note = EXCLUDED.note,
  last_update_date = CURRENT_TIMESTAMP;

COMMIT;
