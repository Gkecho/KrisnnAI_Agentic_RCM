<?php
// Spike: can OpenEMR's own code produce a real 837P for one seeded encounter, headless? Synthetic data, local container only.
$ignoreAuth = true;
$_GET['site'] = 'default';
$_SERVER['HTTP_HOST'] = 'localhost';
require_once('/var/www/localhost/htdocs/openemr/interface/globals.php');

use OpenEMR\Billing\BillingUtilities;
use OpenEMR\Billing\X125010837P;

$pid = 1;
$enc = 2;
$uid = (int) sqlQuery("select id from users where username='admin'")['id'];

sqlStatement("update users set npi='1234567893', fname='Demo', lname='Provider', taxonomy='207Q00000X', federaltaxid='123456789' where id=?", [$uid]);
sqlStatement("update facility set name='Synthetic Demo Clinic', federal_ein='123456789', facility_npi='1999999984', street='1 Demo Way', city='Testville', state='TX', postal_code='750011234', attn='Billing Office', phone='5125550100', pos_code='11', billing_location=1, service_location=1, tax_id_type='EIN' where id=3");
sqlStatement("update patient_data set providerID=? where pid=?", [$uid, $pid]);
sqlStatement("update form_encounter set facility_id=3, billing_facility=3, provider_id=?, pos_code=11 where pid=? and encounter=?", [$uid, $pid, $enc]);

sqlStatement("delete from x12_partners where id=1");
sqlStatement("insert into x12_partners (id,name,id_number,x12_sender_id,x12_receiver_id,processing_format,x12_isa01,x12_isa02,x12_isa03,x12_isa04,x12_isa05,x12_isa07,x12_isa14,x12_isa15,x12_gs02,x12_per06,x12_dtp03,x12_gs03,x12_submitter_id,x12_submitter_name) values (1,'KrisnAI Mock Clearinghouse','MOCKCH','KRISNAISND','MOCKCH','standard','00','          ','00','          ','ZZ','ZZ','0','T','KRISNAISND','','D','MOCKCH','','SYNTHETIC DEMO CLINIC')");
sqlStatement("delete from insurance_companies where id=1");
sqlStatement("insert into insurance_companies (id,name,cms_id,ins_type_code,x12_receiver_id,x12_default_partner_id,inactive) values (1,'SYNAETNA Demo Payer','60054',2,'60054',1,0)");
sqlStatement("delete from addresses where foreign_id=1 and line1='PO Box 1'");
sqlStatement("insert into addresses (id,line1,city,state,zip,country,foreign_id) values ((select coalesce(max(a.id),0)+1 from addresses a),'PO Box 1','Hartford','CT','06101','USA',1)");
sqlStatement("delete from insurance_data where pid=?", [$pid]);
sqlStatement("insert into insurance_data (type,provider,plan_name,policy_number,group_number,subscriber_lname,subscriber_fname,subscriber_relationship,subscriber_DOB,subscriber_street,subscriber_postal_code,subscriber_city,subscriber_state,subscriber_country,date,pid,subscriber_sex,accept_assignment) values ('primary',1,'Demo PPO','SYN000008','GRP1','SYNM000008','Synthetic','self','1997-12-08','100 Synthetic Way','75001','Testville','TX','USA','2025-01-01',?,'Male','TRUE')", [$pid]);

sqlStatement("delete from billing where pid=? and encounter=?", [$pid, $enc]);
BillingUtilities::addBilling($enc, 'ICD10', 'J02.9', 'Acute pharyngitis, unspecified', $pid, '1', $uid, '', '', '0.00', '', '', 0);
BillingUtilities::addBilling($enc, 'CPT4', '99213', 'Office visit est patient', $pid, '1', $uid, '', '1', '110.00', '', 'ICD10|J02.9:', 0);

BillingUtilities::updateClaim(true, $pid, $enc, 1, 1, 1, 0, '', 'X12', 1);
$log = '';
$x12 = X125010837P::genX12837P($pid, $enc, 1, $log, false);
file_put_contents('/tmp/spike_837.x12', $x12);
echo $x12, "\n--- LOG\n", $log, "\n";
