# SOURCES.md

This file explains what real-world formats I looked at and how that affected the backend importers.

I did not copy a real customer file. The sample shapes are fabricated, but they are based on common fields found in SAP material documents, utility billing exports, and corporate travel/expense exports.

## SAP fuel and procurement

## What I researched

I looked at SAP material document concepts and the SAP Material Document API shape. The useful idea was that SAP inventory/procurement movement data is usually document-based, with header/item information, material identifiers, plant/location fields, dates, quantities, and units.

References used:

- SAP Help Portal - Operations for Material Document API  
  https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/eb2a39dd0c124fed8252f684002d55e1/1aef4e402acd4c8b8ec2ea2bfda7715b.html
- SAP Help Portal - Material Document Item properties  
  https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/eb2a39dd0c124fed8252f684002d55e1/8c451658745b1f60e10000000a44147b.html
- SAP Help Portal - Document concept in inventory management  
  https://help.sap.com/docs/SAP_ERP/96bf9ad642cf4b26a29595e3d573fb8c/1363bd534f22b44ce10000000a174cb4.html

## What I implemented

I chose a flat CSV export instead of a live SAP API.

The importer expects fields like:

- document number
- posting date
- plant/facility code
- material description
- quantity
- unit of measure
- amount
- currency

It also accepts some alternate column names, including German-style names like `Werk`, `Buchungsdatum`, and `Belegnummer`.

## Why the sample data looks this way

The SAP sample should include:

- fuel rows such as diesel or LPG
- procurement rows such as purchased goods/materials
- mixed date formats
- mixed units like L, gallons, kg, tonnes
- plant/facility codes
- invalid quantity rows
- unknown unit rows
- suspiciously high quantity rows

This tests the importer’s main behavior without trying to cover every SAP setup.

## What would break in production

This approach would break or need work if:

- the client uses custom SAP column names not included in the importer
- material descriptions are too vague for keyword classification
- plant codes need a lookup table
- procurement categories must come from GL accounts or material groups
- the customer expects an IDoc, OData, or BAPI integration instead of CSV
- duplicate detection across multiple uploads is required

## Utility electricity

## What I researched

I looked at utility billing and Green Button-style data. The useful idea was that utility data is usually tied to meters, usage periods, consumption units, demand, charges, and billing periods that may not match calendar months.

References used:

- Green Button Alliance - Utility bill data mapping  
  https://www.greenbuttonalliance.org/utility-bill-data
- Hydro Ottawa - Green Button access and electricity usage/billing data  
  https://hydroottawa.com/en/accounts-services/services/green-button

## What I implemented

I chose a utility portal CSV export, not PDF OCR and not a live Green Button XML/API integration.

The importer expects fields like:

- meter ID
- facility code
- billing period start
- billing period end
- usage quantity
- usage unit
- demand kW
- tariff name
- amount
- currency

## Why the sample data looks this way

The utility sample should include:

- valid kWh rows
- MWh rows that normalize to kWh
- missing meter IDs
- invalid billing date ranges
- unsupported units
- unusually high usage rows

This tests the common problems a facilities analyst would care about.

## What would break in production

This approach would need more work if:

- bills arrive as PDFs only
- the utility provides XML/Green Button data instead of CSV
- one account has many meters and complex meter hierarchies
- demand charges and usage charges need separate rows
- billing periods must be allocated into calendar months
- tariff handling needs to affect emissions or cost reporting

## Corporate travel

## What I researched

I looked at SAP Concur-style travel and expense reporting. The useful idea was that travel records may come from itineraries and expense reports, with different segments like flights, hotels, cars, trains, and other ground transport.

References used:

- SAP Help Portal - Concur Expense Report data dictionary  
  https://help.sap.com/docs/SAP_CONCUR/27041ab78c844e679db485fff6f4033f/19c4b9fff2df443dbe42ba518f8cdb72.html
- SAP Help Portal - Concur Itinerary Details report  
  https://help.sap.com/docs/SAP_CONCUR/92814b27ae9c4b298c6e80d2a3241445/1c431f2e700b1014a46a108435d32877.html

## What I implemented

I chose a travel platform CSV export.

The importer supports these categories:

- flight
- hotel
- ground_transport

The expected fields include:

- trip ID
- employee ID
- category
- booking date
- start and end dates
- origin airport
- destination airport
- distance km
- hotel nights
- ground transport mode
- amount
- currency

## Why the sample data looks this way

The travel sample should include:

- valid flights with airport codes and distance
- valid hotels with nights
- valid ground transport rows
- flights missing distance
- hotels missing nights
- unknown ground transport modes

This matches the assignment requirement that distances are not always given and different travel categories need different handling.

## What would break in production

This approach would need more work if:

- distance must be calculated from airport codes
- airport codes need validation against a real airport database
- hotel emissions depend on country or hotel type
- ground transport modes need country-specific emission factors
- travel data comes from real Concur/Navan APIs instead of CSV
- employee IDs must be anonymized or linked to HR data

## General assumption

The backend currently normalizes activity data, not final emissions. It prepares cleaner Scope 1/2/3 activity rows for review. A real CO2e calculation engine would be a separate layer.
