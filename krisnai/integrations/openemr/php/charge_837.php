<?php
// Demo-only (ADR-0002): enter one charge for an existing OpenEMR encounter and have OpenEMR's own generator write the 837P.
// Reads one JSON object on stdin, prints one JSON object. Runs inside OUR OpenEMR container against synthetic data.
// OpenEMR 7.0.3 has no REST endpoint for charges, so the charge goes in through OpenEMR's own BillingUtilities.
$ignoreAuth = true;
$_GET['site'] = 'default';
$_SERVER['HTTP_HOST'] = 'localhost';
$_SERVER['REQUEST_METHOD'] = 'CLI';
error_reporting(E_ERROR);
require_once('/var/www/localhost/htdocs/openemr/interface/globals.php');

use OpenEMR\Billing\BillingUtilities;
use OpenEMR\Billing\X125010837P;

$in = json_decode(stream_get_contents(STDIN), true);
$pid = (int) $in['pid'];
$enc = (int) $in['encounter'];
$uid = (int) sqlQuery("select id from users where username='admin'")['id'];

// one-time setup (idempotent): provider, facility, X12 partner, payer
sqlStatement("update users set npi='1234567893', fname='Demo', lname='Provider', taxonomy='207Q00000X', federaltaxid='123456789' where id=?", [$uid]);
sqlStatement("update facility set name='Synthetic Demo Clinic', federal_ein='123456789', facility_npi='1999999984', street='1 Demo Way', city='Testville', state='TX', postal_code='750011234', attn='Billing Office', phone='5125550100', pos_code='11', billing_location=1, service_location=1, tax_id_type='EIN' where id=3");
$partner = sqlQuery("select id from x12_partners where id_number='MOCKCH'");
if (!$partner) {
    sqlStatement("insert into x12_partners (name,id_number,x12_sender_id,x12_receiver_id,processing_format,x12_isa01,x12_isa02,x12_isa03,x12_isa04,x12_isa05,x12_isa07,x12_isa14,x12_isa15,x12_gs02,x12_per06,x12_dtp03,x12_gs03,x12_submitter_id,x12_submitter_name) values ('KrisnAI Mock Clearinghouse','MOCKCH','KRISNAISND','MOCKCH','standard','00','          ','00','          ','ZZ','ZZ','0','T','KRISNAISND','','D','MOCKCH',?,'SYNTHETIC DEMO CLINIC')", [$uid]);
    $partner = sqlQuery("select id from x12_partners where id_number='MOCKCH'");
}
$partnerId = (int) $partner['id'];
$co = sqlQuery("select id from insurance_companies where cms_id=?", [$in['payer_id']]);
if (!$co) {
    $coId = (int) sqlQuery("select coalesce(max(id),0)+1 as n from insurance_companies")['n'];
    sqlStatement("insert into insurance_companies (id,name,cms_id,ins_type_code,x12_receiver_id,x12_default_partner_id,inactive) values (?,?,?,2,?,?,0)", [$coId, $in['payer_name'], $in['payer_id'], $in['payer_id'], $partnerId]);
    sqlStatement("insert into addresses (id,line1,city,state,zip,country,foreign_id) values ((select coalesce(max(a.id),0)+1 from addresses a),'PO Box 1','Hartford','CT','06101','USA',?)", [$coId]);
} else {
    $coId = (int) $co['id'];
}
sqlStatement("update patient_data set providerID=? where pid=?", [$uid, $pid]);
sqlStatement("update form_encounter set facility_id=3, billing_facility=3, provider_id=?, pos_code=11 where pid=? and encounter=?", [$uid, $pid, $enc]);
$p = sqlQuery("select fname,lname,DOB,sex,street,city,state,postal_code from patient_data where pid=?", [$pid]);
sqlStatement("delete from insurance_data where pid=? and type='primary'", [$pid]);
sqlStatement("insert into insurance_data (type,provider,plan_name,policy_number,group_number,subscriber_lname,subscriber_fname,subscriber_relationship,subscriber_DOB,subscriber_street,subscriber_postal_code,subscriber_city,subscriber_state,subscriber_country,date,pid,subscriber_sex,accept_assignment) values ('primary',?,?,?,'GRP1',?,?,'self',?,?,?,?,?,'USA','2025-01-01',?,?,'TRUE')",
    [$coId, $in['plan_name'], $in['member'], $p['lname'], $p['fname'], $p['DOB'], $p['street'], $p['postal_code'], $p['city'], $p['state'], $pid, $p['sex']]);

// the charge: diagnoses first, then the procedure pointing at them
sqlStatement("delete from billing where pid=? and encounter=?", [$pid, $enc]);
$just = '';
foreach ($in['dx'] as $d) {
    BillingUtilities::addBilling($enc, 'ICD10', $d['code'], $d['text'], $pid, '1', $uid, '', '', '0.00', '', '', 0);
    $just .= 'ICD10|' . $d['code'] . ':';
}
foreach ($in['lines'] as $ln) {
    BillingUtilities::addBilling($enc, 'CPT4', $ln['cpt'], $ln['text'], $pid, '1', $uid, '', (string) $ln['units'], $ln['fee'], '', $just, 0);
}
BillingUtilities::updateClaim(true, $pid, $enc, $coId, 1, 1, 0, '', 'X12', $partnerId);
$log = '';
$x12 = X125010837P::genX12837P($pid, $enc, $partnerId, $log, false);
echo json_encode(['x12' => $x12, 'log' => $log, 'pid' => $pid, 'encounter' => $enc]);
