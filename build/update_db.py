import sqlite3

conn = sqlite3.connect("mcpdict.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE info_rowid (
  簡稱 TEXT PRIMARY KEY,
  語言ID INTEGER
);
""")

cursor.execute("""
INSERT INTO info_rowid(簡稱, 語言ID)
SELECT 簡稱, info.ROWID
FROM info;
""")

# Add a build_version table to track database build versions

cursor.execute("""
CREATE TABLE IF NOT EXISTS build_version (
    version INTEGER DEFAULT (strftime('%s','now'))
);
""")

cursor.execute("""
INSERT INTO build_version DEFAULT VALUES;
""")

conn.commit()
conn.close()
