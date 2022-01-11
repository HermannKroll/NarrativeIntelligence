select chembl_id, who_name, ac.level1, ac.level2, ac.level3, ac.level4, ac.level5,
ac.level1_description, ac.level2_description, ac.level3_description, ac.level4_description
from molecule_dictionary md
join molecule_atc_classification mac on md.molregno = mac.molregno
join atc_classification ac on mac.level5 = ac.level5
ORDER BY chembl_id ASC