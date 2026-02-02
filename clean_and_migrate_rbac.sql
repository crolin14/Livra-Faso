-- Script SQL pour nettoyer et préparer RBAC UUID
-- Exécuter dans psql

-- Supprimer toutes les tables RBAC
DROP TABLE IF EXISTS rbac_permissioncache CASCADE;
DROP TABLE IF EXISTS rbac_userrole CASCADE;
DROP TABLE IF EXISTS rbac_rolepermission CASCADE;
DROP TABLE IF EXISTS rbac_permission CASCADE;
DROP TABLE IF EXISTS rbac_role CASCADE;

-- Nettoyer les migrations Django
DELETE FROM django_migrations WHERE app = 'rbac';

-- Vérifier que les tables sont supprimées
\dt rbac_*;
