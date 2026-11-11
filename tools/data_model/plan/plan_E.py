# Plan E: resources (rooms, equipment and clinical staff) and what is allocated to each appointment.
# Executed by gen_final.py; helpers (add, addr, L, common, audit, M_, I_, O_, GA, ...) come from there. Existing tables are not changed.

TBD_DONE = []
REMAP = {}

addr("resource", I_, "One row per bookable resource: a room, a piece of equipment, or a clinical staff member. A registered nurse is a resource like a machine: shared, allocated to the appointments that need one.",
     "The inventory. Appointments need rooms, equipment and nurses, and only a table of what exists can show what is free, what is overused and what is missing. appointment_slot.room_or_resource is free text and cannot do that.",
     "Utilization by resource and class, idle and overbooked hours, equipment or nurse shortage by site, cost of resource time per visit and per specialty, resources needed for the services booked next week",
     "1 scheduler resource list, 2 facility asset or equipment list plus staff roster, 3 distinct room_or_resource values on appointment_slot (class guessed from the text)", [
    L("resource_number", "VARCHAR(30)", M_, "", "The practice's code for the resource, for example LOC3-XRAY-1 or RN-GARCIA.", "Code created by us"),
    L("resource_name", "VARCHAR(80)", M_, "", "Display name: Exam room 3, C-arm suite 2, Garcia, RN.", "Built from the class and a number"),
    L("resource_type", "VARCHAR(15)", M_, "", "room, equipment or staff. A registered nurse is a staff resource and is booked the same way as a machine.", "Inferred from the class"),
    L("resource_class", "VARCHAR(30)", I_, "", "Kind of room, equipment or role: Exam room, Treatment table, X-ray room, E-stim unit, Registered nurse.", "Blank"),
    L("practice_id", "INT", I_, "practice", "Owning practice.", "Client default"),
    L("facility_id", "INT", I_, "facility", "Home site. A floating resource can still be booked at other sites.", "Practice default"),
    L("is_floating", "BIT", I_, "", "1 if the resource can be allocated at any facility, such as a nurse who covers several sites.", "0"),
    L("capacity", "SMALLINT", I_, "", "How many appointments can use it at the same time: 1 for a machine, a room or a nurse.", "1"),
    L("provider_id", "INT", O_, "provider", "For a staff resource, the clinician row, so the nurse joins to their supervising physician and notes.", "Blank"),
    L("specialty_id", "INT", O_, "specialty", "Specialty the resource is dedicated to. Blank when shared.", "Blank"),
    L("serves_cpt_codes", "VARCHAR(200)", O_, "", "CPT codes whose services need this resource, comma separated. Drives the requirement checks.", "Blank"),
    L("in_service_date", "DATE", O_, "", "First day it can be booked.", "Blank"),
    L("out_of_service_date", "DATE", O_, "", "Last day it can be booked (retired, sold, left). Blank while in service.", "Blank"),
    L("resource_status", "VARCHAR(15)", O_, "", "in_service, maintenance or retired.", "in_service"),
    L("cost_per_hour", "DECIMAL(8,2)", O_, "", "What one hour of the resource costs, for utilization economics.", "Blank")])

add("resource_allocation", I_, "1 Appointment", "capacity", "One row per resource held by an appointment: the room, the machine, the nurse. A change of state is a new version.",
    "Allocation. Links an appointment to everything it needs so conflicts, overbooking, idle time and shortages can be measured, for machines and nurses alike.",
    "Utilization by resource, overbooked allocations, nurse hours per procedure, wait for a free resource, appointments blocked by a missing resource, cost of resources per visit",
    "1 scheduler resource booking, 2 room or equipment text on the slot matched to the resource list, 3 none (utilization is then estimated from appointment length)",
    common("resource_allocation") + [
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Client default"),
        L("resource_id", "BIGINT", M_, "resource", "The resource held.", "Matched on the room or equipment text of the slot"),
        L("appointment_id", "BIGINT", M_, "appointment", "The appointment that uses it.", "Match on provider, date, time"),
        L("allocation_date", "DATE", M_, "", "Day of use.", "Appointment date"), L("start_time", "TIME(0)", M_, "", "When the resource is needed. Equipment can start later than the visit.", "Appointment start"),
        L("duration_minutes", "SMALLINT", M_, "", "How long it is held.", "Appointment length"),
        L("appointment_slot_id", "BIGINT", I_, "appointment_slot", "The slot it was allocated for.", "Match on appointment"),
        L("facility_id", "INT", I_, "facility", "Site where it was used.", "Appointment facility"),
        L("allocation_status", "VARCHAR(10)", I_, "", "booked, used, released or no_show.", "booked"),
        L("allocation_role", "VARCHAR(15)", I_, "", "How the appointment uses it: room, equipment or clinical_staff.", "From the resource type"),
        L("cpt_code_id", "INT", O_, "cpt_code", "The service line that needed the resource. Blank for the base room.", "Blank"),
        L("provider_id", "INT", O_, "provider", "The clinician the resource was allocated to (the appointment's provider).", "Blank"),
        L("is_overbook", "BIT", O_, "", "1 if every instance was busy when it was allocated.", "Blank")] + audit("resource_allocation"))
