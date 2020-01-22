WITH t_dos AS (
    SELECT document_id AS did, ent_id
    FROM tag
    WHERE ent_type = 'DosageForm' AND document_collection = 'PMC'
),
     t_chem AS (
         SELECT document_id AS did, ent_id
         FROM tag
         WHERE ent_type = 'Chemical'AND document_collection = 'PMC'
     )
SELECT t_dos.ent_id AS dosage_form, t_chem.ent_id AS chemical, count(DISTINCT t_dos.did) AS count
FROM t_dos
         JOIN t_chem
              ON t_dos.did = t_chem.did
GROUP BY t_dos.ent_id, t_chem.ent_id;