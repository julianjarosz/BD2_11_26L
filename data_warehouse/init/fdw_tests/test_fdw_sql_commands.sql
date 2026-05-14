select *
  from pg_extension
 where extname = 'postgres_fdw';
-- you should see fdw extension returned

select foreign_table_schema,
       foreign_table_name
  from information_schema.foreign_tables
 where foreign_table_schema = 'src'
 order by foreign_table_name;

-- you should see all table names from the operation db

select count(*)
  from src.location;

-- shouldn't fail, you should see 0 for now