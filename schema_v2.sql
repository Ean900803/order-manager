-- 訂單管理系統 schema（對齊 Django models / migrations 與 ER 圖命名）
-- 建表順序已依外鍵相依性排好；字元集 utf8mb4。
-- 主鍵 / 外鍵欄名對齊 ER 圖：eId / catId / pId / uId / custId / oId / sId。

SET NAMES utf8mb4;

-- 員工
CREATE TABLE employees (
  eId           INT PRIMARY KEY AUTO_INCREMENT,
  password      VARCHAR(128) NOT NULL,
  username      VARCHAR(20) UNIQUE NOT NULL,
  name          VARCHAR(20) NOT NULL,
  cellphone     VARCHAR(10) NOT NULL,
  address       VARCHAR(100) NOT NULL DEFAULT '',
  resigned_date DATETIME NULL,
  INDEX idx_resigned (resigned_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 商品分類
CREATE TABLE categories (
  catId INT PRIMARY KEY AUTO_INCREMENT,
  name  VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 單位
CREATE TABLE units (
  uId  INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(10) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 商品（catId = 分類，eId = 建立者）
CREATE TABLE products (
  pId         INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(50) NOT NULL,
  catId       INT NOT NULL,
  eId         INT NOT NULL,
  description TEXT NOT NULL,
  INDEX idx_product_category (catId),
  FOREIGN KEY (catId) REFERENCES categories(catId),
  FOREIGN KEY (eId)   REFERENCES employees(eId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 商品單位定價（同一 product+unit 可有多筆，靠 status 區分啟用/失效）
CREATE TABLE product_unit (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  pId             INT NOT NULL,
  uId             INT NOT NULL,
  conversion_rate INT UNSIGNED NOT NULL,
  price           DECIMAL(10,2) NOT NULL,
  cost            DECIMAL(10,2) NOT NULL,
  status          VARCHAR(10) NOT NULL DEFAULT 'active',  -- 'active' / 'inactive'
  INDEX idx_active_lookup (pId, uId, status),
  FOREIGN KEY (pId) REFERENCES products(pId) ON DELETE CASCADE,
  FOREIGN KEY (uId) REFERENCES units(uId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 客戶
CREATE TABLE customers (
  custId    INT PRIMARY KEY AUTO_INCREMENT,
  name      VARCHAR(20) NOT NULL,
  cellphone VARCHAR(10) NOT NULL DEFAULT '',
  address   VARCHAR(100) NOT NULL DEFAULT '',
  note      TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 訂單（custId = 客戶，eId = 建立者）
CREATE TABLE orders (
  oId        INT PRIMARY KEY AUTO_INCREMENT,
  custId     INT NOT NULL,
  eId        INT NOT NULL,
  order_date DATETIME NOT NULL,
  status     VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending / confirmed / completed / cancelled
  INDEX idx_order_customer (custId),
  INDEX idx_order_date (order_date),
  FOREIGN KEY (custId) REFERENCES customers(custId),
  FOREIGN KEY (eId)    REFERENCES employees(eId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 訂單明細（成交當下鎖定 price / cost / conversion_rate）
CREATE TABLE order_record (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  oId             INT NOT NULL,
  pId             INT NOT NULL,
  price           DECIMAL(10,2) NOT NULL,
  cost            DECIMAL(10,2) NOT NULL,
  quantity        INT UNSIGNED NOT NULL,
  discount        DECIMAL(5,2) NOT NULL DEFAULT 0,
  conversion_rate INT UNSIGNED NOT NULL,
  INDEX idx_record_order (oId),
  INDEX idx_record_product (pId),
  FOREIGN KEY (oId) REFERENCES orders(oId) ON DELETE CASCADE,
  FOREIGN KEY (pId) REFERENCES products(pId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 進貨批次（FIFO 依 id 順序扣庫存，quantity_remaining 可為負表示超賣）
CREATE TABLE stocks (
  sId                INT PRIMARY KEY AUTO_INCREMENT,
  pId                INT NOT NULL,
  uId                INT NOT NULL,
  quantity           INT UNSIGNED NOT NULL,
  quantity_remaining INT NOT NULL,
  unit_cost          DECIMAL(10,2) NOT NULL,
  INDEX idx_fifo_lookup (pId, sId),
  FOREIGN KEY (pId) REFERENCES products(pId),
  FOREIGN KEY (uId) REFERENCES units(uId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
