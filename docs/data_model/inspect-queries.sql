-- Ready-made questions for the local database (krisnnai_canonical). Connect with the MSSQL extension, select a block, run it (Ctrl+Shift+E).
-- The database holds the schema only. Every table and column has its description stored as an extended property.

-- 1. Every table, its stage and what one row is
SELECT t.name AS [table], CAST(ep.value AS NVARCHAR(4000)) AS [priority, stage, one row is, why]
FROM sys.tables t
LEFT JOIN sys.extended_properties ep ON ep.major_id = t.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
ORDER BY t.name;

-- 2. All columns of one table with their priority, type, null rule and description (change the table name)
DECLARE @table sysname = N'claim';
SELECT c.column_id AS pos, c.name AS [column], TYPE_NAME(c.user_type_id) + CASE WHEN c.max_length > 0 AND TYPE_NAME(c.user_type_id) LIKE '%char' THEN '(' + CAST(c.max_length AS varchar(10)) + ')' ELSE '' END AS [type],
       CASE c.is_nullable WHEN 0 THEN 'NOT NULL' ELSE 'null' END AS nullable, CAST(ep.value AS NVARCHAR(4000)) AS description
FROM sys.columns c
LEFT JOIN sys.extended_properties ep ON ep.major_id = c.object_id AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
WHERE c.object_id = OBJECT_ID(@table)
ORDER BY c.column_id;

-- 3. How tables link: every foreign key (child column to parent table)
SELECT OBJECT_NAME(fk.parent_object_id) AS child, COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS child_column,
       OBJECT_NAME(fk.referenced_object_id) AS parent
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
ORDER BY parent, child;

-- 4. What depends on a table (change the table name): who points at it?
DECLARE @parent sysname = N'payer';
SELECT OBJECT_NAME(fk.parent_object_id) AS child, COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS child_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
WHERE fk.referenced_object_id = OBJECT_ID(@parent)
ORDER BY child;

-- 5. Search every column description for a word (change the word)
SELECT OBJECT_NAME(ep.major_id) AS [table], COL_NAME(ep.major_id, ep.minor_id) AS [column], CAST(ep.value AS NVARCHAR(4000)) AS description
FROM sys.extended_properties ep
WHERE ep.name = 'MS_Description' AND ep.minor_id > 0 AND CAST(ep.value AS NVARCHAR(4000)) LIKE '%denial%'
ORDER BY [table], [column];

-- 6. The restricted columns (never shown in reports or logs)
SELECT OBJECT_NAME(ep.major_id) AS [table], COL_NAME(ep.major_id, ep.minor_id) AS [column]
FROM sys.extended_properties ep
WHERE ep.name = 'MS_Description' AND ep.minor_id > 0 AND CAST(ep.value AS NVARCHAR(4000)) LIKE '%[[]RESTRICTED]%'
ORDER BY [table], [column];

-- 7. Columns added in the latest review (each says why in the data dictionary)
SELECT OBJECT_NAME(ep.major_id) AS [table], COL_NAME(ep.major_id, ep.minor_id) AS [column]
FROM sys.extended_properties ep
WHERE ep.name = 'MS_Description' AND ep.minor_id > 0 AND CAST(ep.value AS NVARCHAR(4000)) LIKE '%[[]NEW IN REVIEW]%'
ORDER BY [table], [column];

-- 8. Table sizes by number of columns (the widest tables)
SELECT t.name AS [table], COUNT(*) AS columns_count
FROM sys.tables t JOIN sys.columns c ON c.object_id = t.object_id
GROUP BY t.name ORDER BY columns_count DESC;
