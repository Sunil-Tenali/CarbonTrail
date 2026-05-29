# SOURCES.md

This file explains what I looked at for the three source types and how that shaped the sample data and importers.

I did not use real customer data. The sample files are fabricated, but the columns are based on common fields from SAP material/procurement exports, utility electricity data, and corporate travel reports.

## SAP fuel and procurement

### Format researched

I treated the SAP source as a flat export from inventory/procurement-style material document data.

SAP data can come from many places: IDocs, OData APIs, BAPIs, and custom reports. I looked at the material document style because it commonly has document numbers, posting dates, plant codes, material descriptions, quantities, and units.

References:

- SAP Help Portal - Material Document API / operations  
  https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/eb2a39dd0c124fed8252f684002d55e1/1aef4e402acd4c8b8ec2ea2bfda7715b.html
- SAP Help Portal - Material document item properties  
  https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/eb2a39dd0c124fed8252f684002d55e1/8c451658745b1f60e10000000a44147b.html
- SAP Help Portal - Inventory management document concept  
  https://help.sap.com/docs/SAP_ERP/96bf9ad642cf4b26a29595e3d573fb8c/1363bd534f22b44ce10000000a174cb4.html

### What I learned

SAP exports are not guaranteed to be clean. A real client may have custom column names, plant codes, German labels, odd date formats, and units that need mapping.

The useful fields for this prototype are:

- document number
- posting date
- plant/facility code
- cost center if available
- material description
- quantity
- unit of measure
- amount
- currency

### What my sample data looks like

The SAP sample is meant to include:

- fuel rows such as diesel or LPG
- procurement rows such as purchased goods/materials
- plant codes
- mixed units like liters, gallons, kg, and tonnes
- bad quantity rows
- unknown unit rows
- suspiciously high quantity rows

The importer classifies fuel-like material descriptions as Scope 1 and other procurement as Scope 3.

### What would break in a real deployment

This would need more work if:

- the client exports different SAP columns
- material descriptions are too vague
- plant codes need lookup tables
- fuel/procurement classification must come from GL accounts or material groups
- the client expects OData, BAPI, IDoc, or SFTP instead of CSV
- duplicate detection across repeated exports is required

## Utility electricity

### Format researched

I treated utility data as a portal CSV export. I looked at Green Button-style utility data and electricity billing export concepts.

References:

- Green Button Alliance - utility bill data  
  https://www.greenbuttonalliance.org/utility-bill-data
- Hydro Ottawa - Green Button electricity usage and billing access  
  https://hydroottawa.com/en/accounts-services/services/green-button

### What I learned

Utility data is usually tied to meters and billing periods. The period may not match a calendar month. Usage can come in kWh or MWh. Some exports also include demand kW, tariff names, charges, and account information.

Important fields for the prototype:

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

### What my sample data looks like

The utility sample includes:

- valid kWh rows
- MWh rows that normalize to kWh
- missing meter ID
- invalid billing date range
- unsupported unit
- unusually high usage row

The importer assigns all utility electricity rows to Scope 2.

### What would break in a real deployment

This would need more work if:

- bills are only available as PDFs
- the utility provides Green Button XML instead of CSV
- usage and demand charges need separate accounting
- one account has many meters and sub-meters
- billing periods must be allocated into reporting months
- tariffs affect reporting or validation rules

## Corporate travel

### Format researched

I treated travel data as a Concur/Navan-style travel and expense export.

References:

- SAP Concur - Expense report data dictionary  
  https://help.sap.com/docs/SAP_CONCUR/27041ab78c844e679db485fff6f4033f/19c4b9fff2df443dbe42ba518f8cdb72.html
- SAP Concur - Itinerary details report  
  https://help.sap.com/docs/SAP_CONCUR/92814b27ae9c4b298c6e80d2a3241445/1c431f2e700b1014a46a108435d32877.html

### What I learned

Travel data is category-specific. A flight row is not the same as a hotel row. Flights may have airport codes but not distance. Hotels need nights. Ground transport needs mode and distance if available.

Useful fields for the prototype:

- trip ID
- employee ID
- category
- booking date
- start date
- end date
- origin airport
- destination airport
- distance km
- hotel nights
- ground transport mode
- amount
- currency

### What my sample data looks like

The travel sample includes:

- valid flight
- valid hotel
- valid ground transport
- flight missing distance
- hotel missing nights
- unknown ground transport mode

All corporate travel rows are treated as Scope 3.

### What would break in a real deployment

This would need more work if:

- distances must be calculated from airport codes
- airport codes need validation from a real airport database
- hotel emissions depend on country or hotel type
- ground transport modes need country-specific mapping
- travel comes from live Concur/Navan APIs instead of CSV
- employee IDs need anonymization or HR system mapping

## General note on sample files

The sample files are not meant to be perfect customer exports. They are meant to exercise the main behaviors:

- valid rows
- invalid rows
- suspicious rows
- unit normalization
- source-specific validation
- Scope 1/2/3 classification
- analyst review and audit logs
