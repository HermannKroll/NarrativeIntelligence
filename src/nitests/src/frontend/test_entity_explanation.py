from unittest import TestCase

import tqdm
from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityExplainerData, EntityTaggerData
from narraint.frontend.entity.entityexplainer import EntityExplainer
from narraint.frontend.entity.entitytagger import EntityTagger

tagger_entries = [
    ('CHEMBL4204794', 'Drug', None, ' avapritinib'),
    ('CHEMBL1064', 'Drug', None, ' simvastatin hydroxy acid'),
    ('CHEMBL465617', 'Drug', None, ' amantadine sulfate'),
    ('CHEMBL1569', 'Drug', None, ' amantadine hcl'),
    ('CVCL:B6WA', 'CellLine', None, ' 1e5 mouse hybridoma against amantadine'),
    ('CHEMBL1431', 'Drug', None, ' metformin extended release'),
    ('CHEMBL1431', 'Drug', None, ' la 6023'),
    ('CHEMBL660', 'Drug', None, ' amantadine'),
    ('CHEMBL2348413', 'Drug', None, ' metformin pregabalin salt'),
    ('CHEMBL1569', 'Drug', None, ' amantadine hydrochloride'),
    ('CHEMBL503', 'Drug', None, ' simvastatin impurity lovastatin'),
    ('CHEMBL2165491', 'Drug', None, ' spiroamantadine'),
    ('CHEMBL2108299', 'Drug', None, ' metformin glycinate'),
    ('CHEMBL494397', 'Drug', None, ' metformin xr'),
    ('CHEMBL1201391', 'Drug', None, ' simvastatin acid'),
    ('CHEMBL1703', 'Drug', None, ' la 6023'),
    ('CHEMBL2348410', 'Drug', None, ' metformin gabapentin salt'),
    ('CHEMBL1703', 'Drug', None, ' metformin hydrochloride'),
    ('CHEMBL1703', 'Drug', None, ' metformin hcl'),
    ('CHEMBL1201391', 'Drug', None, ' simvastatin hydroxy acid'),
    ('CHEMBL1064', 'Drug', None, ' simvastatin'),
    ('CHEMBL1431', 'Drug', None, ' metformin'),
    ('CHEMBL1201391', 'Drug', None, ' simvastatin carboxylic acid'),
    ('MESH:D000094024', 'Disease', None, ' long haul covid'),
    ('MESH:C535564', 'Disease', None, ' tibia absence of with polydactyly'),
    ('MESH:D000094024', 'Disease', None, ' longcovid'),
    ('CHEMBL486174', 'Drug', None, ' variotin'),
    ('MESH:D000094024', 'Disease', None, ' long haul covid19s'),
    ('MESH:D000094024', 'Disease', None, ' covid19 long haul'),
    ('MESH:C535563', 'Disease', None, ' absence of tibia'),
    ('MESH:C564764', 'Disease', None, ' tibia absence of with congenital deafness'),
    ('MESH:C535563', 'Disease', None, ' tibia absence of'),
    ('MESH:C535563', 'Disease', None, ' bilateral absence of the tibia'),
    ('MESH:D000094024', 'Disease', None, ' long covid'),
    ('CHEMBL486174', 'Drug', None, ' pecilocin'),
    ('MESH:D000094024', 'Disease', None, ' longhaul covid'),
    ('MESH:D000094024', 'Disease', None, ' covid longhaul'),
    ('Q97154236', 'Vaccine', None, ' anhui zhifei longcom biopharmaceutical covid19 vaccine candidate'),
    ('MESH:C535564', 'Disease', None, ' absence of tibia with polydactyly'),
    ('MESH:C535689', 'Disease', None, ' fibula and ulna duplication of with absence of tibia and radius'),
    ('MESH:D000094024', 'Disease', None, ' long haul covid 19'),
    ('MESH:D000094024', 'Disease', None, ' long hauler covid'),
    ('MESH:D000094024', 'Disease', None, ' longhaul covids'),
    ('MESH:D000094024', 'Disease', None, ' long haul covid19'),
    ('MESH:C563403', 'Disease', None,
     ' tibia absence or hypoplasia of with polydactyly retrocerebellar arachnoid cyst and other anomalies')
]

explanation_entries = [
    ('CHEMBL1201391', '[simvastatin acid,tenivastatin,simvastatin hydroxy acid,simvastatin carboxylic acid]'),
    ('CHEMBL2165491', '[spiroamantadine]'),
    ('CHEMBL2348413', '[metformin pregabalin salt]'),
    ('CVCL:B6WA', '[1e5 [mouse hybridoma against amantadine]]'),
    ('CHEMBL4204794', '[avapritinib,x-720776,c-366,70c366,blu-285,x720776]'),
    ('CHEMBL1703',
     '[ex404,walaphage,benofomin,diabefagos,neodipa,siamformet,diabex,ex-404,apophage,metformin hcl,la-6023,nsc-91485,metformin hydrochloride,glucaminol]'),
    ('CHEMBL503',
     '[simvastatin impurity, lovastatin-,sivlor,mevlor,c10aa02,lovastatin,mevinolin,mk-803,nsc-758662,6.alpha.-methylcompactin,l-154803,monacolin k]'),
    ('CHEMBL494397', '[metformin xr]'), ('CHEMBL2108299', '[metformin glycinate,dmmet-01]'),
    ('CHEMBL1569',
     '[adamantanamine hydrochloride,amantadine hcl,mantadix,amantadine hydrochloride,exp-105-1,osmolex,nsc-83653]'),
    ('CHEMBL660', '[symmetrel,symadine,nsc-341865,amantadine,tcmdc-125869,amantidine]'),
    ('CHEMBL465617', '[amantadine sulfate]'),
    ('CHEMBL1064', '[nsc-758706,synvinolin,mk-733,simvastatin,simvastatin hydroxy acid,c10aa01,mk-0733]'),
    ('CHEMBL1431', '[la-6023,metformin,metformin extended release]'),
    ('CHEMBL2348410', '[metformin gabapentin salt]'),
    ('MESH:D000094024',
     '[long covid,Long-Haul COVIDs,Long Haul COVID 19,Post-Acute COVID-19 Syndromes,Long Haul COVID,Post-COVID Conditions,persistent covid-19,post-covid syndrome,post-acute covid syndrome,post-coronavirus disease-2019 syndrome,Long Haul COVID-19,long-covid,long-haul covid,long-haul coronavirus disease,post-acute covid19 syndrome,chronic coronavirus disease syndrome,Post Acute Sequelae of SARS CoV 2 Infection,Post-COVID Condition,COVID-19 Post-Acute Sequelae,PASC Post Acute Sequelae of COVID 19,long haul covid,Post-Acute Sequelae of COVID-19,Post-Acute Sequelae of SARS-CoV-2 Infection,Post Acute COVID-19 Syndrome,Post Acute COVID 19 Syndrome,chronic covid syndrome,post-acute sequelae of sars-cov-2 infection,long hauler covid,COVID, Long-Haul,post-coronavirus disease syndrome,Post-Acute COVID-19 Syndrome,Post COVID Conditions,post-covid-19 syndrome,COVID-19 Syndrome, Post-Acute,Long COVID,Post Acute Sequelae of COVID 19,PASC Post Acute Sequelae of COVID-19,pasc,Long Haul COVID-19s,Long-Haul COVID,COVID-19, Long Haul,post-acute covid-19 syndrome,post-acute sequelae of severe acute respiratory syndrome coronavirus 2]'),
    ('MESH:C535563', '[Tibial hemimelia,Absence of Tibia,Bilateral absence of the tibia,Tibia, absence of]'),
    ('MESH:C564764', '[Tibia, Absence of, with Congenital Deafness]'),
    ('MESH:C535689',
     '[Tetramelic mirror-image polydactyly,Mirror hands and feet with nasal defects,Fibula And Ulna, Duplication Of, With Absence Of Tibia And Radius,Laurin-Sandrow Syndrome, Segmental,Laurin Sandrow syndrome,Fibula ulna duplication tibia radius absence,Mirror-Image Polydactyly,Laurin-Sandrow syndrome,Sandrow syndrome]'),
    ('MESH:C563403',
     '[Tibia, Absence or Hypoplasia of, with Polydactyly, Retrocerebellar Arachnoid Cyst, and Other Anomalies]'),
    ('CHEMBL486174', '[variotin,nsc-291839,pecilocin]'),
    ('Q97154236',
     '[rbd-dimer,zf-uz-vac-2001,zifivax,anhui zhifei longcom biopharmaceutical covid-19 vaccine candidate,zf2001,zhongyianke biotech–liaoning maokangyuan biotech covid-19 vaccine]'),
    ('MESH:C535564',
     '[Tibia, Absence of, with Polydactyly,Absence of tibia with polydactyly,Polydactyly with absent tibia]')
]


class EntityExplanationTestCase(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        session = SessionExtended.get()

        # Delete old explainer and tagger data
        session.execute(delete(EntityExplainerData))
        session.execute(delete(EntityTaggerData))
        session.commit()

        entity_tagger_data = list()
        for ent_id, ent_type, ent_class, synonyms in tagger_entries:
            entity_tagger_data.append(dict(entity_id=ent_id,
                                           entity_type=ent_type,
                                           entity_class=ent_class,
                                           synonym=synonyms,
                                           synonym_processed=synonyms))

        entity_explainer_data = list()
        for ent_id, ent_terms in explanation_entries:
            entry = dict(entity_id=ent_id, entity_terms=ent_terms)
            entity_explainer_data.append(entry)

        # update index data
        EntityTaggerData.bulk_insert_values_into_table(session, entity_tagger_data)
        EntityExplainerData.bulk_insert_values_into_table(session, entity_explainer_data)

        cls.entity_explainer = EntityExplainer()

    def test_chembl_entries(self):
        """
        Tests whether drugbank names and headings can be tagged correctly
        """
        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Metformin', truncate_at_k=1000)]
        self.assertIn('la-6023', terms)
        self.assertIn('metformin', terms)
        self.assertNotIn('metformin malt', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('LA-6023', truncate_at_k=1000)]
        self.assertIn('la-6023', terms)
        self.assertIn('metformin', terms)
        # Because Metformin should be included
        self.assertNotIn('metformin salt', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Simvastatin', truncate_at_k=1000)]
        self.assertIn('simvastatin', terms)
        self.assertIn('synvinolin', terms)
        self.assertIn('mk-0733', terms)
        self.assertIn('mk-733', terms)
        # Because Prefix Simvastatin should already be included
        self.assertNotIn('simvastatin hydroxy acid', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Amantadine', truncate_at_k=1000)]
        self.assertIn('amantadine', terms)
        self.assertIn('symadine', terms)
        self.assertIn('symmetrel', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Avapritinib', truncate_at_k=1000)]
        self.assertIn('avapritinib', terms)

    def test_prefix_filter(self):
        prefixes = ['Diabetes',
                    'Diabetes Mellitus',
                    'Diabetes Mellitus Congenital',
                    'Diabetes Mellitus Congenital Autoimmune']
        test_prefixes = list(self.entity_explainer.get_prefixes('Diabetes Mellitus Congenital Autoimmune'))
        for p in prefixes:
            self.assertIn(p.lower(), test_prefixes)

        self.assertIn('diabetes', list(self.entity_explainer.get_prefixes('Diabetes')))

        test = ['Diabetes Mellitus',
                'Diabetes Meitus',
                'Diabetes Mellitus, Congenital Autoimmune']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Diabetes Mellitus', f_test)
        self.assertIn('Diabetes Meitus', f_test)
        self.assertNotIn('Diabetes Mellitus, Congenital Autoimmune', f_test)

        test = ['Diabetes Mellitus',
                'Diabetes Mellitus Congenital Autoimmune']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Diabetes Mellitus', f_test)
        self.assertNotIn('Diabetes Mellitus Congenital Autoimmune', f_test)

        test = ['Ace',
                'Acetabulum']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Ace', f_test)
        self.assertIn('Acetabulum', f_test)

    def test_mesh_supplement_entries(self):
        self.assertIn('Absence of Tibia', [t for t in self.entity_explainer.explain_entity_str('Absence of Tibia')])

    def test_no_mesh_expansion(self):
        direct_names = ['Long COVID', "Long Haul COVID-19", "Long-Haul COVID"]
        not_expanded_names = ["COVID 19", "Chronic Condition"]
        for n1 in direct_names:
            terms = [t for t in self.entity_explainer.explain_entity_str(n1, truncate_at_k=1000)]
            for n2 in direct_names:
                self.assertIn(n2, terms)
            for not_n2 in not_expanded_names:
                self.assertNotIn(not_n2, terms)

    def test_no_atc_trees(self):
        direct_names = ['Pecilocin', "variotin"]
        not_expanded_names = ["antibiotics", "antibiotics for topical use", "antibiotics for dermatological use"]
        for n1 in direct_names:
            terms = [t for t in self.entity_explainer.explain_entity_str(n1, truncate_at_k=1000)]
            for n2 in direct_names:
                self.assertIn(n2, terms)
            for not_n2 in not_expanded_names:
                self.assertNotIn(not_n2, terms)


def generate_test_data():
    tagger_data = set()
    explainer_data = set()

    entity_tagger = EntityTagger()

    terms_to_explain = [
        "Metformin",
        "LA-6023",
        "Simvastatin",
        "Amantadine",
        "Avapritinib",

        "Absence of Tibia",

        'Long COVID',
        "Long Haul COVID-19",
        "Long-Haul COVID",

        'Pecilocin',
        "variotin"
    ]
    session = SessionExtended.get()

    for term in tqdm.tqdm(terms_to_explain):
        for entity in entity_tagger.tag_entity(term):
            tagger_data.add((entity.entity_id, entity.entity_type, entity.entity_class, entity.entity_name))

            query = session.query(EntityExplainerData.entity_terms)
            query = query.filter(entity.entity_id == EntityExplainerData.entity_id)

            if query.count() == 0:
                continue

            terms = query.first()[0]
            explainer_data.add((entity.entity_id, terms))

    print("TAGGER INDEX DATA")
    print(",\n".join(str(t) for t in list(tagger_data)))

    print()
    print()

    print("EXPLAINER INDEX DATA")
    print(",\n".join(str(t) for t in list(explainer_data)))


if __name__ == "__main__":
    generate_test_data()
