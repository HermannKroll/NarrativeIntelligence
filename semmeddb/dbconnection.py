from datetime import datetime
import psycopg2
import os
import pickle
import json

WORKING_DIR = "../tmp/"
UMLS_DATA = "../data/umls/MRCONSO.RRF"
UMLS_MESH2CUI_INDEX_TMP_FILE = WORKING_DIR + "umls_mesh2cui_index.pickle"
UMLS_CUI2MESH_INDEX_TMP_FILE = WORKING_DIR + "umls_cui2mesh_index.pickle"
PREDICATES_TMP_FILE = WORKING_DIR + "predicates.pickle"

SEMMED_CONFIG_FILE = "config.json"





QUERY_PREDICATES = 'SELECT predicate, COUNT(*) FROM PREDICATION GROUP BY predicate'
QUERY_CUIS = '(SELECT subject_cui AS CUI FROM PREDICATION) UNION (SELECT object_cui AS CUI FROM PREDICATION)'
QUERY_FACTS = 'SELECT pmid, subject_cui, predicate, object_cui FROM PREDICATION LIMIT 10000'


class SemMedDB:
    def __init__(self, config_file="semmeddb/config.json"):
        self.cui2mesh = dict()
        self.mesh2cui = dict()
        self.connected = False
        self.predicates = set()
        self.predicatesCount = {}
        self.conn = None

        if not os.path.isfile(config_file):
            raise Exception('no config file for semmed found under {}'.format(config_file))

        self.__load_config(config_file)

    def __load_config(self, config_file):
        with open(config_file) as f:
            self.config = json.load(f)

    def load_umls_dictionary(self):
        start = datetime.now()
        print('loading umls dictionary...')
        if os.path.isfile(UMLS_MESH2CUI_INDEX_TMP_FILE) and os.path.isfile(UMLS_CUI2MESH_INDEX_TMP_FILE):
            with open(UMLS_MESH2CUI_INDEX_TMP_FILE, 'rb') as f:
                self.mesh2cui = pickle.load(f)
                print('read mesh2cui index from file')
            with open(UMLS_CUI2MESH_INDEX_TMP_FILE, 'rb') as f:
                self.cui2mesh = pickle.load(f)
                print('read cui2mesh index from file')
        else:
            with open(UMLS_DATA) as f:
                for idx, line in enumerate(f):
                    fields = line.split("|")
                    if fields[11] == "MSH":
                        if fields[0] not in self.cui2mesh:
                            self.cui2mesh[fields[0]] = fields[10]
                        if fields[10] not in self.mesh2cui:
                            self.mesh2cui[fields[10]] = fields[0]

            end = datetime.now()
            print("Read {} lines in {}".format(idx + 1, end - start))
            print('Write UMLS index to tmp index files...')
            with open(UMLS_MESH2CUI_INDEX_TMP_FILE, 'wb') as f:
                pickle.dump(self.mesh2cui, f)
                print('mesh2cui index written')
            with open(UMLS_CUI2MESH_INDEX_TMP_FILE, 'wb') as f:
                pickle.dump(self.cui2mesh, f)
                print('cui2mesh index written')

    def connect_to_db(self):
        connection_str = "dbname='{}' user='{}' host='{}' port='{}' password='{}'".format(self.config["POSTGRES_DB"],
                                                                                          self.config["POSTGRES_USER"],
                                                                                          self.config["POSTGRES_HOST"],
                                                                                          self.config["POSTGRES_PORT"],
                                                                                          self.config["POSTGRES_PW"])
        print('connection string to database: {}'.format(connection_str))
        try:
            self.conn = psycopg2.connect(connection_str)
            self.connected = True
            print('Connected to SemMedDB at {}'.format(self.config["POSTGRES_HOST"]))
        except:
            self.connected = False
            print('Error while connecting to the database..')

    def __execute_select_query(self, sql):
        print('executing select statement: {}'.format(sql))
        start = datetime.now()
        cur = self.conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        end = datetime.now()
        print("Query processed in {}".format(end - start))
        return rows

    def load_predicates(self):
        if os.path.isfile(PREDICATES_TMP_FILE):
            with open(PREDICATES_TMP_FILE, 'rb') as f:
                self.predicatesCount = pickle.load(f)
                self.predicates = self.predicatesCount.keys()
                print('{} predicates load from file'.format(len(self.predicatesCount)))

        else:
            if self.connected == False:
                print('Cannot load predicates - not conntected to database')
                return
            # load predicate list
            self.predicatesCount = {}

            print('Executing query to retrieve the predicates list...')
            rows = self.__execute_select_query(QUERY_PREDICATES)
            for r in rows:
                self.predicatesCount[r[0]] = r[1]
            print("{} predicates load from DB".format(len(self.predicatesCount)))
            with open(PREDICATES_TMP_FILE, 'wb') as f:
                pickle.dump(self.predicatesCount, f)
            self.predicates = self.predicatesCount.keys()
            print('predicates saved to file: {}'.format(PREDICATES_TMP_FILE))

    def __translate_fact_pattern_mesh_ids_to_cuis(self, fact_patterns):
        fact_patterns_new = []
        for f in fact_patterns:
            s, p, o = f

            s_new = s
            if s.startswith('MESH'):
                s_tmp = s[5:]
                if s_tmp in self.mesh2cui:
                    s_new = self.mesh2cui[s_tmp]
                else:
                    print('{} not in mesh2cui'.format(s))
            o_new = o
            if o.startswith('MESH'):
                o_tmp = o[5:]
                if o_tmp in self.mesh2cui:
                    o_new = self.mesh2cui[o_tmp]
                else:
                    print('{} not in mesh2cui'.format(o))

            fact_patterns_new.append((s_new, p, o_new))

        return fact_patterns_new

    def __translate_fact_patterns_to_semmeddb_sql(self, fact_patterns):
        sql = ''
        # add joins
        i = 1
        for f in fact_patterns[1:]:
            sql += '    JOIN PREDICATION P{} ON (P{}.pmid = P{}.pmid) \n'.format(i, i, i - 1)
            i += 1

        # add where
        sql += 'WHERE \n'

        # first pattern
        # s, p, o = fact_patterns[0]

        # dictionary of variables in fact patterns
        vars_dict = {}
        # iterate over all fact patterns
        i = 0
        for f in fact_patterns:
            s, p, o = f
            # first compute the given predication
            pred = 'P{}'.format(i)
            if i == 0:
                sql += "    {}.predicate = '{}' ".format(pred, p)
            else:
                sql += "    AND {}.predicate = '{}' ".format(pred, p)
            # we just need to include specific entities.
            # variables means we need to join later
            vars_in_fact = []
            if not s.startswith('?'):
                sql += "AND {}.subject_cui = '{}' ".format(pred, s)
            else:
                vars_in_fact.append(('subj', s))

            if not o.startswith('?'):
                sql += "AND {}.object_cui = '{}' ".format(pred, o)
            else:
                vars_in_fact.append(('obj', o))

            # store that variable occurred in this fact
            for t, v in vars_in_fact:
                if v not in vars_dict:
                    vars_dict[v] = [(t, pred)]
                else:
                    vars_dict[v].append((t, pred))

            sql += '\n'
            i += 1

        # print(vars_dict)

        # join all predications sharing the same vars
        # pairwise join should be enough
        for variable, occurrences in vars_dict.items():
            # skip all variables which are just mentioned once
            # they do not influence the query
            if len(occurrences) < 2:
                continue
            # go trough the occurrences of the variable and join the tables
            for i in range(0, len(occurrences) - 1):
                t1, pred1 = occurrences[i]
                t2, pred2 = occurrences[i + 1]

                if t1 == 'subj':
                    sql += '    AND {}.subject_cui = '.format(pred1)
                elif t1 == 'obj':
                    sql += '    AND {}.object_cui = '.format(pred1)

                if t2 == 'subj':
                    sql += '{}.subject_cui '.format(pred2)
                elif t2 == 'obj':
                    sql += '{}.object_cui '.format(pred2)

                sql += '\n'

        # add projection
        var_names = []
        if len(vars_dict) == 0:
            sql_header = 'SELECT DISTINCT P0.pmid FROM PREDICATION P0 \n'
        else:
            sql_header = 'SELECT DISTINCT P0.pmid '
            for var, occurrences in vars_dict.items():
                var_names.append(var)
                type, pred = occurrences[0]
                if type == 'subj':
                    sql_header += ', {}.{} , {}.{} '.format(pred, 'subject_name', pred, 'subject_cui')
                elif type == 'obj':
                    sql_header += ', {}.{} , {}.{} '.format(pred, 'object_name', pred, 'object_cui')

            sql_header += 'FROM PREDICATION P0 \n'

        return sql_header + sql, var_names

    def query_for_fact_patterns(self, fact_patterns):
        fact_patterns_cui = self.__translate_fact_pattern_mesh_ids_to_cuis(fact_patterns)
        sql, var_names = self.__translate_fact_patterns_to_semmeddb_sql(fact_patterns_cui)

        rows = self.__execute_select_query(sql)
        pmids = []
        var_subs = []
        for r in rows:
            pmids.append(r[0])
            # extract var substitutions for pmid
            i = 1
            var_sub = {}
            for v in var_names:
                # add name as well as cui to substitution
                var_sub[v] = '{} ({})'.format(r[i], r[i+1])
                i += 2 # skip the next cui and switch to name
            var_subs.append(var_sub)
        print("{} hits: {}".format(len(pmids), pmids))
        return pmids, var_subs, var_names
