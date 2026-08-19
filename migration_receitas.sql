USE estoque_inteligente;
CREATE TABLE IF NOT EXISTS recipes (
 id INT AUTO_INCREMENT PRIMARY KEY,
 code VARCHAR(30) NOT NULL UNIQUE,
 name VARCHAR(150) NOT NULL,
 yield_text VARCHAR(80) NULL,
 preparation_time VARCHAR(80) NULL,
 instructions TEXT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recipe_ingredients (
 id INT AUTO_INCREMENT PRIMARY KEY,
 recipe_id INT NOT NULL,
 product_code VARCHAR(30) NOT NULL,
 quantity DECIMAL(10,2) NOT NULL,
 unit ENUM('Kg','g','L','ml','un') NOT NULL,
 FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
 INDEX idx_recipe_id (recipe_id), INDEX idx_product_code (product_code)
);
