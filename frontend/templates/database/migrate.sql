-- Migration: Add Member 3 new columns to posts table
USE nexus_db;

ALTER TABLE posts ADD COLUMN IF NOT EXISTS image_url VARCHAR(300) NULL;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_repost TINYINT(1) DEFAULT 0;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS original_post_id INT NULL;