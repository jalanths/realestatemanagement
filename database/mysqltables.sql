-- -----------------------------------------------------
-- 1. DATABASE CREATION
-- -----------------------------------------------------
CREATE DATABASE IF NOT EXISTS `real_estate_db` DEFAULT CHARACTER SET utf8mb4;
USE `real_estate_db`;

-- -----------------------------------------------------
-- 2. TABLE CREATION (All 13 Tables)
-- -----------------------------------------------------

-- Table `client`
CREATE TABLE IF NOT EXISTS `client` (
  `CLIENT_ID` INT NOT NULL AUTO_INCREMENT,
  `Name` VARCHAR(100) NOT NULL,
  `Fname` VARCHAR(50) NULL,
  `Lname` VARCHAR(50) NULL,
  `Hire_Date` DATE NULL,
  AddressStreet VARCHAR(100),
    City VARCHAR(50),
    State VARCHAR(50),
    ZIPCode VARCHAR(10),
  PRIMARY KEY (`CLIENT_ID`)
);

-- Table `clientphone`
CREATE TABLE IF NOT EXISTS `clientphone` (
  `CLIENT_ID` INT NOT NULL,
  `PhoneNumber` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`CLIENT_ID`, `PhoneNumber`),
  FOREIGN KEY (`CLIENT_ID`) REFERENCES `client` (`CLIENT_ID`) ON DELETE CASCADE
);

-- Table `office`
CREATE TABLE IF NOT EXISTS `office` (
  `OFFICE_ID` INT NOT NULL AUTO_INCREMENT,
  `Name` VARCHAR(100) NOT NULL,
  `Street` VARCHAR(100) NULL,
  `City` VARCHAR(50) NULL,
  `State` VARCHAR(50) NULL,
  `ZIP` VARCHAR(20) NULL,
  PRIMARY KEY (`OFFICE_ID`)
);

-- Table `officephone`
CREATE TABLE IF NOT EXISTS `officephone` (
  `OFFICE_ID` INT NOT NULL,
  `PhoneNumber` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`OFFICE_ID`, `PhoneNumber`),
  FOREIGN KEY (`OFFICE_ID`) REFERENCES `office` (`OFFICE_ID`) ON DELETE CASCADE
);

-- Table `agent`
CREATE TABLE IF NOT EXISTS `agent` (
  `AGENT_ID` INT NOT NULL AUTO_INCREMENT,
  `Name` VARCHAR(100) NOT NULL,
  `Fname` VARCHAR(50) NULL,
  `Lname` VARCHAR(50) NULL,
  `LicenseNumber` VARCHAR(100) NULL,
  `CommissionPerc` DECIMAL(5, 2) NULL,
  `Hire_Date` DATE NULL,
  `OFFICE_ID` INT NULL,
  `Supervisor_ID` INT NULL,
  PRIMARY KEY (`AGENT_ID`),
  FOREIGN KEY (`OFFICE_ID`) REFERENCES `office` (`OFFICE_ID`) ON DELETE SET NULL,
  FOREIGN KEY (`Supervisor_ID`) REFERENCES `agent` (`AGENT_ID`) ON DELETE SET NULL
);

-- Table `agentphone`
CREATE TABLE IF NOT EXISTS `agentphone` (
  `AGENT_ID` INT NOT NULL,
  `PhoneNumber` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`AGENT_ID`, `PhoneNumber`),
  FOREIGN KEY (`AGENT_ID`) REFERENCES `agent` (`AGENT_ID`) ON DELETE CASCADE
);

-- Table `user` (For App Logins)
CREATE TABLE IF NOT EXISTS `user` (
  `USER_ID` INT NOT NULL AUTO_INCREMENT,
  `Email` VARCHAR(100) NOT NULL UNIQUE,
  `PasswordHash` VARCHAR(255) NOT NULL,
  `Role` ENUM('Admin', 'Agent', 'Client') NOT NULL,
  `AGENT_ID` INT NULL UNIQUE,
  `CLIENT_ID` INT NULL UNIQUE,
  PRIMARY KEY (`USER_ID`),
  FOREIGN KEY (`AGENT_ID`) REFERENCES `agent` (`AGENT_ID`) ON DELETE SET NULL,
  FOREIGN KEY (`CLIENT_ID`) REFERENCES `client` (`CLIENT_ID`) ON DELETE SET NULL
);

-- Table `property`
CREATE TABLE IF NOT EXISTS `property` (
  `PROPERTY_ID` INT NOT NULL AUTO_INCREMENT,
  `Street` VARCHAR(100) NULL,
  `City` VARCHAR(50) NULL,
  `State` VARCHAR(50) NULL,
  `ZIP` VARCHAR(20) NULL,
  `SIZE` DECIMAL(10, 2) NULL,
  `TYPE` VARCHAR(50) NULL,
  `PRICE` DECIMAL(12, 2) NULL,
  `CLIENT_ID` INT NOT NULL,
  `AGENT_ID` INT NOT NULL,
  PRIMARY KEY (`PROPERTY_ID`),
  FOREIGN KEY (`CLIENT_ID`) REFERENCES `client` (`CLIENT_ID`),
  FOREIGN KEY (`AGENT_ID`) REFERENCES `agent` (`AGENT_ID`)
);

-- Table `contract`
CREATE TABLE IF NOT EXISTS `contract` (
  `CONTRACT_ID` INT NOT NULL AUTO_INCREMENT,
  `Start_Date` DATE NULL,
  `End_Date` DATE NULL,
  `Amount` DECIMAL(12, 2) NULL,
  `CLIENT_ID` INT NOT NULL,
  `AGENT_ID` INT NOT NULL,
  PRIMARY KEY (`CONTRACT_ID`),
  FOREIGN KEY (`CLIENT_ID`) REFERENCES `client` (`CLIENT_ID`),
  FOREIGN KEY (`AGENT_ID`) REFERENCES `agent` (`AGENT_ID`)
);

-- Table `payment`
CREATE TABLE IF NOT EXISTS `payment` (
  `Payment_No` INT NOT NULL AUTO_INCREMENT,
  `Payment_Date` DATE NULL,
  `Amount` DECIMAL(12, 2) NULL,
  `CONTRACT_ID` INT NOT NULL,
  PRIMARY KEY (`Payment_No`),
  FOREIGN KEY (`CONTRACT_ID`) REFERENCES `contract` (`CONTRACT_ID`)
);

-- Table `commission`
CREATE TABLE IF NOT EXISTS `commission` (
  `COMMISSION_ID` INT NOT NULL AUTO_INCREMENT,
  `Percentage` DECIMAL(5, 2) NULL,
  `Amount` DECIMAL(12, 2) NULL,
  `CommissionPerc` DECIMAL(5, 2) NULL,
  PRIMARY KEY (`COMMISSION_ID`)
);

-- Table `propertycontract` (M:N Link)
CREATE TABLE IF NOT EXISTS `propertycontract` (
  `PROPERTY_ID` INT NOT NULL,
  `CONTRACT_ID` INT NOT NULL,
  PRIMARY KEY (`PROPERTY_ID`, `CONTRACT_ID`),
  FOREIGN KEY (`PROPERTY_ID`) REFERENCES `property` (`PROPERTY_ID`) ON DELETE CASCADE,
  FOREIGN KEY (`CONTRACT_ID`) REFERENCES `contract` (`CONTRACT_ID`) ON DELETE CASCADE
);

-- Table `earns`
CREATE TABLE IF NOT EXISTS `earns` (
  `EARNS_ID` INT NOT NULL AUTO_INCREMENT,
  `Earned_Date` DATE NULL,
  `AGENT_ID` INT NOT NULL,
  `COMMISSION_ID` INT NOT NULL,
  PRIMARY KEY (`EARNS_ID`),
  UNIQUE KEY `idx_commission_unique` (`COMMISSION_ID`),
  FOREIGN KEY (`AGENT_ID`) REFERENCES `agent` (`AGENT_ID`),
  FOREIGN KEY (`COMMISSION_ID`) REFERENCES `commission` (`COMMISSION_ID`)
);

-- -----------------------------------------------------
-- 3. PROJECT REQUIREMENT: Trigger
-- -----------------------------------------------------

-- This table will store the audit log
CREATE TABLE IF NOT EXISTS `property_price_audit` (
  `Audit_ID` INT NOT NULL AUTO_INCREMENT,
  `PROPERTY_ID` INT,
  `Old_Price` DECIMAL(12, 2),
  `New_Price` DECIMAL(12, 2),
  `Change_Timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`Audit_ID`)
);

-- This is the trigger that fires on UPDATE
DELIMITER $$
CREATE TRIGGER `trg_PropertyPriceAudit`
BEFORE UPDATE ON `property`
FOR EACH ROW
BEGIN
  IF OLD.PRICE <> NEW.PRICE THEN
    INSERT INTO `property_price_audit` (PROPERTY_ID, Old_Price, New_Price)
    VALUES (OLD.PROPERTY_ID, OLD.PRICE, NEW.PRICE);
  END IF;
END$$
DELIMITER ;

-- -----------------------------------------------------
-- 4. PROJECT REQUIREMENT: Stored Procedure
-- -----------------------------------------------------

-- This procedure is called by the GUI to calculate commission
DELIMITER $$
CREATE PROCEDURE `sp_GenerateCommission` (
  IN in_PAYMENT_ID INT
)
BEGIN
  DECLARE v_PaymentAmount DECIMAL(12, 2);
  DECLARE v_AgentID INT;
  DECLARE v_CommissionPerc DECIMAL(5, 2);
  DECLARE v_CommissionAmount DECIMAL(12, 2);
  DECLARE v_NewCommissionID INT;

  -- Get payment amount and agent details
  SELECT p.Amount, c.AGENT_ID INTO v_PaymentAmount, v_AgentID
  FROM payment p
  JOIN contract c ON p.CONTRACT_ID = c.CONTRACT_ID
  WHERE p.Payment_No = in_PAYMENT_ID;
  
  -- Get agent's commission percentage
  SELECT CommissionPerc INTO v_CommissionPerc FROM agent WHERE AGENT_ID = v_AgentID;

  -- Calculate and insert commission
  SET v_CommissionAmount = v_PaymentAmount * (v_CommissionPerc / 100);
  
  INSERT INTO commission (Amount, CommissionPerc) 
  VALUES (v_CommissionAmount, v_CommissionPerc);
  
  -- Get the new commission ID
  SET v_NewCommissionID = LAST_INSERT_ID();
  
  -- Link it in the 'earns' table
  INSERT INTO earns (Earned_Date, AGENT_ID, COMMISSION_ID) 
  VALUES (CURDATE(), v_AgentID, v_NewCommissionID);

END$$
DELIMITER ;

-- -----------------------------------------------------
-- 5. PROJECT REQUIREMENT: Function
-- -----------------------------------------------------
-- This function calculates the total value of all contracts
-- for a specific agent.
DELIMITER $$
CREATE FUNCTION `fn_GetAgentTotalSales` (
  in_AGENT_ID INT
)
RETURNS DECIMAL(12, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
  DECLARE total_sales DECIMAL(12, 2);

  SELECT SUM(Amount) INTO total_sales
  FROM contract
  WHERE AGENT_ID = in_AGENT_ID;
  
  -- Return the total, or 0 if the agent has no sales
  RETURN IFNULL(total_sales, 0);

END$$
DELIMITER ;

-- -----------------------------------------------------
-- 6. DATA SEEDING (Test Data)
-- -----------------------------------------------------

-- Add a default Admin user (email: 'admin@test.com', password: 'admin')
INSERT INTO `user` (Email, PasswordHash, Role) 
VALUES ('admin@test.com', 'admin', 'Admin')
ON DUPLICATE KEY UPDATE Email=Email; -- Prevents error if run twice

-- Add a test Office
INSERT INTO `office` (OFFICE_ID, Name, City) VALUES (1, 'Downtown Realty', 'New York')
ON DUPLICATE KEY UPDATE Name=Name;

-- Add a test Agent
INSERT INTO `agent` (AGENT_ID, Name, CommissionPerc, OFFICE_ID) 
VALUES (1, 'Jane Doe', 5.0, 1)
ON DUPLICATE KEY UPDATE Name=Name;

-- Link Agent to a User login (email: 'agent@test.com', password: 'agent')
INSERT INTO `user` (Email, PasswordHash, Role, AGENT_ID) 
VALUES ('agent@test.com', 'agent', 'Agent', 1)
ON DUPLICATE KEY UPDATE Email=Email;

-- Add a test Client
INSERT INTO `client` (CLIENT_ID, Name, Hire_Date) 
VALUES (1, 'John Smith', CURDATE())
ON DUPLICATE KEY UPDATE Name=Name;

-- Link Client to a User login (email: 'client@test.com', password: 'client')
INSERT INTO `user` (Email, PasswordHash, Role, CLIENT_ID) 
VALUES ('client@test.com', 'client', 'Client', 1)
ON DUPLICATE KEY UPDATE Email=Email;

-- Add a test Property
INSERT INTO `property` (PROPERTY_ID, Street, City, PRICE, CLIENT_ID, AGENT_ID) 
VALUES (1, '123 Main St', 'New York', 500000.00, 1, 1)
ON DUPLICATE KEY UPDATE Street=Street;

-- Add a test Contract
INSERT INTO `contract` (CONTRACT_ID, Start_Date, Amount, CLIENT_ID, AGENT_ID)
VALUES (1, CURDATE(), 500000.00, 1, 1)
ON DUPLICATE KEY UPDATE Amount=Amount;

-- Add a test Payment
INSERT INTO `payment` (Payment_No, Payment_Date, Amount, CONTRACT_ID)
VALUES (1, CURDATE(), 25000.00, 1)
ON DUPLICATE KEY UPDATE Amount=Amount;

-- Add a second agent for testing the function
INSERT INTO `agent` (AGENT_ID, Name, CommissionPerc, OFFICE_ID) 
VALUES (2, 'Bob Johnson', 4.5, 1)
ON DUPLICATE KEY UPDATE Name=Name;
INSERT INTO `user` (Email, PasswordHash, Role, AGENT_ID) 
VALUES ('bob@test.com', 'bob', 'Agent', 2)
ON DUPLICATE KEY UPDATE Email=Email;
INSERT INTO `contract` (CONTRACT_ID, Start_Date, Amount, CLIENT_ID, AGENT_ID)
VALUES (2, CURDATE(), 750000.00, 1, 2)
ON DUPLICATE KEY UPDATE Amount=Amount;