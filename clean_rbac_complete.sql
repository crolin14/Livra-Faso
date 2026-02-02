-- Script SQL complet pour nettoyage RBAC PostgreSQL
-- À exécuter dans psql ou pgAdmin

-- 1. Supprimer toutes les tables RBAC avec CASCADE
DROP TABLE IF EXISTS rbac_permissioncache CASCADE;
DROP TABLE IF EXISTS rbac_userrole CASCADE;
DROP TABLE IF EXISTS rbac_rolepermission CASCADE;
DROP TABLE IF EXISTS rbac_permission CASCADE;
DROP TABLE IF EXISTS rbac_role CASCADE;

-- 2. Supprimer les séquences associées (si elles existent)
DROP SEQUENCE IF EXISTS rbac_role_id_seq CASCADE;
DROP SEQUENCE IF EXISTS rbac_permission_id_seq CASCADE;
DROP SEQUENCE IF EXISTS rbac_rolepermission_id_seq CASCADE;
DROP SEQUENCE IF EXISTS rbac_userrole_id_seq CASCADE;

-- 3. Nettoyer les migrations Django pour RBAC
DELETE FROM django_migrations WHERE app = 'rbac';

-- 4. Vérifier que tout est supprimé
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'rbac_%';

-- 5. Vérifier les séquences restantes
SELECT sequence_name FROM information_schema.sequences 
WHERE sequence_schema = 'public' AND sequence_name LIKE 'rbac_%';

-- 6. Vérifier les migrations supprimées
SELECT * FROM django_migrations WHERE app = 'rbac';
