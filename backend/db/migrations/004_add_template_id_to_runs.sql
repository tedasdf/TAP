-- Migration: add template_id column to runs table

ALTER TABLE runs ADD COLUMN template_id TEXT REFERENCES templates(template_id);
