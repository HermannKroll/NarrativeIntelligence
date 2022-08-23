-- MySQL dump 10.14  Distrib 5.5.60-MariaDB, for Linux (x86_64)
--
-- Host: indsrv2    Database: semmedVER40
-- ------------------------------------------------------
-- Server version	5.7.18

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table CITATIONS
--

DROP TABLE IF EXISTS CITATIONS;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE CITATIONS
(
    PMID  varchar(20) NOT NULL,
    ISSN  varchar(10) DEFAULT NULL,
    DP    varchar(50) DEFAULT NULL,
    EDAT  varchar(50) DEFAULT NULL,
    PYEAR int         DEFAULT NULL,
    PRIMARY KEY (PMID)
);
--
-- Dumping data for table CITATIONS
--


--
-- Table structure for table COREFERENCE
--

DROP TABLE IF EXISTS COREFERENCE;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE COREFERENCE
(
    COREFERENCE_ID  int         NOT NULL,
    PMID            varchar(20) NOT NULL DEFAULT '',
    ANA_CUI         varchar(255)         DEFAULT NULL,
    ANA_NAME        varchar(999)         DEFAULT NULL,
    ANA_SEMTYPE     varchar(50)          DEFAULT NULL,
    ANA_TEXT        varchar(200)         DEFAULT '',
    ANA_SENTENCE_ID int         NOT NULL,
    ANA_START_INDEX int                  DEFAULT '0',
    ANA_END_INDEX   int                  DEFAULT '0',
    ANA_SCORE       int                  DEFAULT '0',
    ANT_CUI         varchar(255)         DEFAULT NULL,
    ANT_NAME        varchar(999)         DEFAULT NULL,
    ANT_SEMTYPE     varchar(50)          DEFAULT NULL,
    ANT_TEXT        varchar(200)         DEFAULT '',
    ANT_SENTENCE_ID int         NOT NULL,
    ANT_START_INDEX int                  DEFAULT '0',
    ANT_END_INDEX   int                  DEFAULT '0',
    ANT_SCORE       int                  DEFAULT '0',
    CURR_TIMESTAMP  timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (COREFERENCE_ID)
);
--
-- Table structure for table GENERIC_CONCEPT
--

DROP TABLE IF EXISTS GENERIC_CONCEPT;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE GENERIC_CONCEPT
(
    CONCEPT_ID     int          NOT NULL,
    CUI            varchar(20)  NOT NULL DEFAULT '',
    PREFERRED_NAME varchar(200) NOT NULL DEFAULT '',
    PRIMARY KEY (CONCEPT_ID)
);

DROP TABLE IF EXISTS METAINFO;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE METAINFO
(
    DBVERSION     varchar(10) NOT NULL,
    SEMREPVERSION varchar(10)  DEFAULT NULL,
    PUBMED_TODATE varchar(10)  DEFAULT NULL,
    COMMENT       varchar(500) DEFAULT NULL
);

DROP TABLE IF EXISTS PREDICATION;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE PREDICATION
(
    PREDICATION_ID  int NOT NULL,
    SENTENCE_ID     int NOT NULL,
    PMID            varchar(20)  DEFAULT NULL,
    PREDICATE       varchar(50)  DEFAULT NULL,
    SUBJECT_CUI     varchar(255) DEFAULT NULL,
    SUBJECT_NAME    varchar(999) DEFAULT NULL,
    SUBJECT_SEMTYPE varchar(50)  DEFAULT NULL,
    SUBJECT_NOVELTY int          DEFAULT NULL,
    OBJECT_CUI      varchar(255) DEFAULT NULL,
    OBJECT_NAME     varchar(999) DEFAULT NULL,
    OBJECT_SEMTYPE  varchar(50)  DEFAULT NULL,
    OBJECT_NOVELTY  int          DEFAULT NULL,
    FACT_VALUE      char(20)     DEFAULT NULL,
    MOD_SCALE       char(20)     DEFAULT NULL,
    MOD_VALUE       float        DEFAULT NULL,
    PRIMARY KEY (PREDICATION_ID)
);
--
-- Table structure for table PREDICATION_AUX
--

DROP TABLE IF EXISTS PREDICATION_AUX;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE PREDICATION_AUX
(
    PREDICATION_AUX_ID    int       NOT NULL,
    PREDICATION_ID        int       NOT NULL,
    SUBJECT_TEXT          varchar(200)       DEFAULT '',
    SUBJECT_DIST          int                DEFAULT '0',
    SUBJECT_MAXDIST       int                DEFAULT '0',
    SUBJECT_START_INDEX   int                DEFAULT '0',
    SUBJECT_END_INDEX     int                DEFAULT '0',
    SUBJECT_SCORE         int                DEFAULT '0',
    INDICATOR_TYPE        varchar(10)        DEFAULT '',
    PREDICATE_START_INDEX int                DEFAULT '0',
    PREDICATE_END_INDEX   int                DEFAULT '0',
    OBJECT_TEXT           varchar(200)       DEFAULT '',
    OBJECT_DIST           int                DEFAULT '0',
    OBJECT_MAXDIST        int                DEFAULT '0',
    OBJECT_START_INDEX    int                DEFAULT '0',
    OBJECT_END_INDEX      int                DEFAULT '0',
    OBJECT_SCORE          int                DEFAULT '0',
    CURR_TIMESTAMP        timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (PREDICATION_AUX_ID)
);

-- Table structure for table SENTENCE
--

DROP TABLE IF EXISTS SENTENCE;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE SENTENCE
(
    SENTENCE_ID               int                             NOT NULL AUTO_INCREMENT,
    PMID                      varchar(20)                     NOT NULL DEFAULT '',
    TYPE                      varchar(2)                      NOT NULL DEFAULT '',
    NUMBER                    int                             NOT NULL DEFAULT '0',
    SENT_START_INDEX          int                             NOT NULL DEFAULT '0',
    SENT_END_INDEX            int                             NOT NULL DEFAULT '0',
    SECTION_HEADER            varchar(100)                             DEFAULT NULL,
    NORMALIZED_SECTION_HEADER varchar(50)                              DEFAULT NULL,
    SENTENCE                  varchar(999) CHARACTER SET utf8 NOT NULL DEFAULT '',
    PRIMARY KEY (SENTENCE_ID)
);

-- Dump completed on 2019-07-05 14:38:22
