-- Mark m3u migration 0020 as applied to fix startup issue
INSERT INTO django_migrations (app, name, applied)
VALUES ('m3u', '0020_add_proxy_field', NOW())
ON CONFLICT DO NOTHING;

SELECT 'Migration marked as applied' AS status;
