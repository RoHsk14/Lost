-- Pour migration vers MySQL :
-- 1. Schéma des tables et relations généré par Django
-- 2. À compléter avec les données exportées (voir all_data.json)

-- Schéma des tables (extrait de inspectdb)
-- Vous pouvez adapter les types si besoin pour MySQL

-- Exemple :
CREATE TABLE `core_utilisateur` (
  `id` int NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `nom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  -- ... autres champs ...
);

-- Ajoutez ici toutes les tables du projet, en suivant le modèle ci-dessus
-- Pour les relations, utilisez FOREIGN KEY
-- Pour les données, utilisez INSERT INTO ... VALUES (...)

-- Pour automatiser la conversion, installez sqlite3 et utilisez :
-- sqlite3 db.sqlite3 .dump > all_data.sql
-- Puis adaptez la syntaxe pour MySQL (remplacez AUTOINCREMENT par AUTO_INCREMENT, etc.)

-- Pour les données, convertissez all_data.json en INSERT SQL si besoin

-- Ce fichier est un point de départ pour la migration complète vers MySQL.