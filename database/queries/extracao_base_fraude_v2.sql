select count(*) FROM processes;
-- SQLite
SELECT ag.external_id as id, fa.process_number as numero_processo, pr.parte_adversa, ag.advogados_adversos, LENGTH(ag.advogados_adversos) - LENGTH(replace(ag.advogados_adversos,',','')) + 1 as qtde_advogados_adversos, ag.nome_titular, ag.cpf_cnpj_titular, ag.valor, ag.data_pagamento, fa.created_at
FROM agreements ag inner join fraud_assessments fa on ag.external_id = fa.external_id inner join processes pr on fa.external_id = pr.external_id 
--WHERE fa.created_at >= '2025-03-10'
order by 5 desc;
SELECT 
    ag.external_id as id, 
    fa.process_number as numero_processo, 
    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(pr.parte_adversa, 'á', 'a'), 'à', 'a'), 'â', 'a'), 'ã', 'a'), 'é', 'e'), 'ê', 'e'), 'í', 'i'), 'ó', 'o'), 'ô', 'o'), 'õ', 'o'), 'ú', 'u'), 'ç', 'c'), 'Á', 'A'), 'À', 'A'), 'Â', 'A'), 'Ã', 'A'), 'É', 'E'), 'Ê', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ô', 'O'), 'Õ', 'O'), 'Ú', 'U'), 'Ç', 'C')) as parte_adversa,
    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ag.advogados_adversos, 'á', 'a'), 'à', 'a'), 'â', 'a'), 'ã', 'a'), 'é', 'e'), 'ê', 'e'), 'í', 'i'), 'ó', 'o'), 'ô', 'o'), 'õ', 'o'), 'ú', 'u'), 'ç', 'c'), 'Á', 'A'), 'À', 'A'), 'Â', 'A'), 'Ã', 'A'), 'É', 'E'), 'Ê', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ô', 'O'), 'Õ', 'O'), 'Ú', 'U'), 'Ç', 'C')) as advogados_adversos,
    LENGTH(ag.advogados_adversos) - LENGTH(replace(ag.advogados_adversos,',','')) + 1 as qtde_advogados_adversos,
    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ag.nome_titular, 'á', 'a'), 'à', 'a'), 'â', 'a'), 'ã', 'a'), 'é', 'e'), 'ê', 'e'), 'í', 'i'), 'ó', 'o'), 'ô', 'o'), 'õ', 'o'), 'ú', 'u'), 'ç', 'c'), 'Á', 'A'), 'À', 'A'), 'Â', 'A'), 'Ã', 'A'), 'É', 'E'), 'Ê', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ô', 'O'), 'Õ', 'O'), 'Ú', 'U'), 'Ç', 'C')) as nome_titular,
    ag.cpf_cnpj_titular, 
    ag.valor, 
    ag.data_pagamento, 
    fa.created_at
FROM 
    agreements ag 
    INNER JOIN fraud_assessments fa ON ag.external_id = fa.external_id 
    INNER JOIN processes pr ON fa.external_id = pr.external_id
ORDER BY 5 DESC;
SELECT fa.* FROM agreements ag inner join fraud_assessments fa on ag.external_id = fa.external_id;
SELECT * FROM processes pr WHERE pr.external_id not in (SELECT ag.external_id as id FROM agreements ag inner join fraud_assessments fa on ag.external_id = fa.external_id inner join processes pr on fa.external_id = pr.external_id) AND pr.status = 'Ativo';

SELECT ag.external_id as id, fa.process_number as numero_processo, pr.parte_adversa, ag.advogados_adversos, LENGTH(ag.advogados_adversos) - LENGTH(replace(ag.advogados_adversos,',','')) + 1 as qtde_advogados_adversos, ag.nome_titular, ag.cpf_cnpj_titular, ag.valor, ag.data_pagamento, fa.created_at
FROM agreements ag inner join fraud_assessments fa on ag.external_id = fa.external_id inner join processes pr on fa.external_id = pr.external_id 
WHERE fa.external_id = '448925'
order by 5 desc;

PRAGMA foreign_keys=off;

DELETE FROM fraud_assessments
WHERE fraud_assessments.external_id = '298661';
DELETE FROM processes
WHERE processes.external_id = '298661';
DELETE FROM agreements
WHERE agreements.external_id = '298661';

-- 5020476-31.2023.8.21.0026 (

select count(1) qtde, external_id from fraud_assessments group by external_id having qtde > 1;
select count(1) qtde from agreements;