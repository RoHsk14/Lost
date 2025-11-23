-- Script de création de la base de données MySQL pour Lost & Found
-- Exécutez ce script dans votre interface MySQL (phpMyAdmin, MySQL Workbench, ou ligne de commande)

-- 1. Créer la base de données
CREATE DATABASE lostfound_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 2. Créer un utilisateur dédié (optionnel mais recommandé)
-- UNCOMMENT ET MODIFIEZ SI VOUS VOULEZ UN UTILISATEUR DÉDIÉ:
-- CREATE USER IF NOT EXISTS 'lostfound_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe_securise';
-- GRANT ALL PRIVILEGES ON lostfound_db.* TO 'lostfound_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 3. Utiliser la base de données
USE lostfound_db;

-- 4. Vérifier la création
SHOW TABLES;
