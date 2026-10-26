## Sanity check 
Based on received filename
# Directory
- Connect to Dev application (10.0.39.201) verify whether directory structure is ready or not under /u01/ngcplus/DCH/DATA/
    for example /u01/ngcplus/DCH/DATA/GBROR for client operator: GBROR.
- Compare directory tree with FRAF1 or GBRJT.
- If Directory is missing then, raise as missing thing
    button action: Create directory
    solution:
     refer FRAF1 or JAMDC and create directory.

# Configurations
- Following are the list of tables which are critical to do file processing.
- get access to database server and check in following table whether configuration is present and active or not  
select * from product_client where client_tadig = 'GBROR';
-- roaming partner = the other 5 char TADIG in the filename (CDTURISGBROR18672, client GBROR -> partner TURIS)
select * from bilateral_agreement where client_operator = 'GBROR' and roaming_operator = 'TURIS';
select * from industry where pmn = 'GBROR';
select * from industry where pmn = 'TURIS';
select * from rap_pmn_seq where pmn = 'GBROR' and homepmn = 'TURIS';
-- take process id from below select query and pass to next
select * from process_id_map where client_name = 'GBROR' and roaming_partner = 'TURIS' and file_direction = 'TI';
select * from processmaster where processid = 88888;
select * from process_control_system where client_operator = 'GBROR' and file_direction = 'TI';
-- sync: virtual columns (FILE_PATH) are skipped; unique numbers (SEQNO) already used in dev move to the next free value

-- check configuration for currency . Currency against pmn = roaming partner in industry table and its target currency SDR or XDR configuration from test server to dev 

SELECT  *
        FROM EXCHANGE_RATE_LIST T
        WHERE T.BASE_CURRENCY ='GBP' 
        AND T.TARGET_CURRENCY =  'SDR'
                  AND T.EFFECTIVE_DATE =    '22-OCT-2026' AND ROWNUM <2 ;
-- Read all tables check missing configuration 
-- display and wait for user to accept sync permission
-- connect to test database 
-- get data sync and update revise 
