-- Script SQL de inicialização — executado manualmente se necessário
-- O sistema cria o banco/tabelas automaticamente via SQLAlchemy

CREATE DATABASE IF NOT EXISTS `coreaxis_deploy`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `coreaxis_deploy`;

CREATE USER IF NOT EXISTS 'coreaxis'@'localhost' IDENTIFIED BY 'SenhaForte';
GRANT ALL PRIVILEGES ON `coreaxis_deploy`.* TO 'coreaxis'@'localhost';
FLUSH PRIVILEGES;

CREATE TABLE IF NOT EXISTS `deployments` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `service`    VARCHAR(100) NOT NULL,
  `name`       VARCHAR(255) NOT NULL,
  `url`        VARCHAR(500)     NULL,
  `status`     ENUM('running','stopped','error','removed') NOT NULL DEFAULT 'running',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
